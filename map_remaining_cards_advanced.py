import sqlite3
import re
from difflib import SequenceMatcher

def load_card_code_cache():
    """Load the card code cache"""
    try:
        with open('card_code_cache.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print("Warning: card_code_cache.json not found")
        return {}

def parse_card_code(card_code):
    """Parse expansion code and collector number from card code string - improved version"""
    # More comprehensive patterns
    patterns = [
        # Standard formats
        r'^([A-Z]{2,3}\d+[a-z]?)\s+(\d+)/(\d+)$',  # SV8a 120/187
        r'^([A-Z]{2,4}-[A-Z]{1,3})\s+(\d+)/(\d+)$',  # DPs-Sd 011/014
        r'^([A-Z]{2,3}\d+)-([A-Z]{1,3})\s+(\d+)/(\d+)$',  # BW1-Bb 049/053
        r'^([A-Z]{2,3}\d+)\s+(\d+)/(\d+)$',  # BW1 049/053
        r'^([A-Z]{1,3})\s+(\d+)/(\d+)$',  # BW 049/053
        # Special formats
        r'^([A-Z]{1,4}\d*)-([A-Z]{1,3})\s+(\d+)/(\d+)$',  # More flexible dash format
        r'^(\w+)\s+(\d+)/(\d+)$',  # Very flexible alphanumeric
    ]

    for pattern in patterns:
        match = re.search(pattern, card_code)
        if match:
            groups = match.groups()
            if len(groups) >= 3:
                if len(groups) == 3:
                    expansion_code, collector_number, total = groups
                elif len(groups) == 4:
                    expansion_code = f"{groups[0]}-{groups[1]}"
                    collector_number = groups[2]
                else:
                    continue
                return expansion_code, collector_number

    return None, None

def find_similar_name(japanese_name, main_cards, threshold=0.6):
    """Find similar card names using fuzzy matching"""
    best_match = None
    best_score = 0

    for card_id, card_name in main_cards:
        # Simple similarity score
        score = SequenceMatcher(None, japanese_name, card_name).ratio()
        if score > best_score and score >= threshold:
            best_match = (card_id, card_name)
            best_score = score

    return best_match, best_score

def map_remaining_cards_advanced():
    """Map remaining unmapped cards using multiple strategies"""

    # Load card code cache
    code_cache = load_card_code_cache()
    print(f"Loaded {len(code_cache)} card codes from cache")

    # Connect to both databases
    event_conn = sqlite3.connect('ptcg_events.db')
    main_conn = sqlite3.connect('../PokemonDBByjules/PTCG_CardDB_Tc/pokemon_cards.db')

    event_cursor = event_conn.cursor()
    main_cursor = main_conn.cursor()

    print('=== ADVANCED MAPPING OF REMAINING CARDS ===')

    # Get all main database cards for reference
    main_cursor.execute('SELECT id, name FROM cards')
    main_cards = main_cursor.fetchall()
    main_name_to_id = {name: card_id for card_id, name in main_cards}

    # Get unmapped cards
    event_cursor.execute('''
        SELECT DISTINCT dc.card_id, dc.card_name
        FROM deck_cards dc
        LEFT JOIN card_mappings cm ON dc.card_id = cm.event_card_id
        WHERE cm.event_card_id IS NULL
        ORDER BY dc.card_id
    ''')

    unmapped_cards = event_cursor.fetchall()
    print(f'Found {len(unmapped_cards)} unmapped cards to process')

    # Get existing mappings for pattern reference
    event_cursor.execute('SELECT event_card_name, main_card_name FROM card_mappings')
    existing_mappings = dict(event_cursor.fetchall())
    print(f'Found {len(existing_mappings)} existing mappings for reference')

    mapped_count = 0
    skipped_count = 0

    for event_card_id, event_card_name in unmapped_cards:
        card_id_str = str(event_card_id)
        mapped = False

        # Strategy 1: Try exact code matching (improved parsing)
        if card_id_str in code_cache and not mapped:
            card_code = code_cache[card_id_str]

            if card_code is not None:
                expansion_code, collector_number = parse_card_code(card_code)

                if expansion_code and collector_number:
                    # Find matching card in main database
                    main_cursor.execute('''
                        SELECT c.id, c.name
                        FROM cards c
                        JOIN expansions e ON c.expansion_id = e.id
                        WHERE e.code = ? AND c.collector_number = ?
                    ''', (expansion_code, collector_number))

                    match = main_cursor.fetchone()

                    if match:
                        main_card_id, main_card_name = match
                        event_cursor.execute('''
                            INSERT INTO card_mappings (event_card_id, main_card_id, main_card_name)
                            VALUES (?, ?, ?)
                        ''', (event_card_id, main_card_id, main_card_name))
                        event_conn.commit()
                        mapped_count += 1
                        mapped = True
                        print(f'  ✓ Code match: "{event_card_name}" ({card_code}) -> "{main_card_name}"')

        # Strategy 2: Try exact name matching from existing patterns
        if not mapped and event_card_name in existing_mappings:
            main_card_name = existing_mappings[event_card_name]
            if main_card_name in main_name_to_id:
                main_card_id = main_name_to_id[main_card_name]
                event_cursor.execute('''
                    INSERT INTO card_mappings (event_card_id, main_card_id, main_card_name)
                    VALUES (?, ?, ?)
                ''', (event_card_id, main_card_id, main_card_name))
                event_conn.commit()
                mapped_count += 1
                mapped = True
                print(f'  ✓ Pattern match: "{event_card_name}" -> "{main_card_name}"')

        # Strategy 3: Try fuzzy name matching (last resort)
        if not mapped:
            similar_match, score = find_similar_name(event_card_name, main_cards, threshold=0.8)
            if similar_match:
                main_card_id, main_card_name = similar_match
                event_cursor.execute('''
                    INSERT INTO card_mappings (event_card_id, main_card_id, main_card_name)
                    VALUES (?, ?, ?)
                ''', (event_card_id, main_card_id, main_card_name))
                event_conn.commit()
                mapped_count += 1
                mapped = True
                print(f'  ✓ Fuzzy match ({score:.2f}): "{event_card_name}" -> "{main_card_name}"')

        if not mapped:
            skipped_count += 1
            print(f'  ✗ No match found: "{event_card_name}"')

    print(f'\n=== MAPPING COMPLETE ===')
    print(f'Mapped: {mapped_count} cards')
    print(f'Skipped/No match: {skipped_count} cards')

    # Verify the mappings
    event_cursor.execute('SELECT COUNT(*) FROM card_mappings')
    total_mappings = event_cursor.fetchone()[0]
    print(f'Total mappings now: {total_mappings}')

    # Check remaining unmapped
    event_cursor.execute('''
        SELECT COUNT(DISTINCT dc.card_id)
        FROM deck_cards dc
        LEFT JOIN card_mappings cm ON dc.card_id = cm.event_card_id
        WHERE cm.event_card_id IS NULL
    ''')
    remaining_unmapped = event_cursor.fetchone()[0]
    print(f'Remaining unmapped cards: {remaining_unmapped}')

    event_conn.close()
    main_conn.close()

if __name__ == '__main__':
    import json
    map_remaining_cards_advanced()