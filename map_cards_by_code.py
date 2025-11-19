import sqlite3
import json
import re

def load_card_code_cache():
    """Load the card code cache"""
    try:
        with open('card_code_cache.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print("Warning: card_code_cache.json not found")
        return {}

def parse_card_code(card_code):
    """Parse expansion code and collector number from card code string"""
    # Try multiple patterns to handle different formats
    patterns = [
        r'^([A-Z]{2,3}\d+[a-z]?)\s+(\d+)/(\d+)$',  # SV8a 120/187
        r'^([A-Z]{2,4}-[A-Z]{1,3})\s+(\d+)/(\d+)$',  # DPs-Sd 011/014
        r'^([A-Z]{2,3}\d+)-([A-Z]{1,3})\s+(\d+)/(\d+)$',  # BW1-Bb 049/053
        r'^([A-Z]{2,3}\d+)\s+(\d+)/(\d+)$',  # BW1 049/053
        r'^([A-Z]{1,3})\s+(\d+)/(\d+)$',  # BW 049/053
    ]

    for pattern in patterns:
        match = re.search(pattern, card_code)
        if match:
            groups = match.groups()
            if len(groups) == 3:
                expansion_code, collector_number, total = groups
            elif len(groups) == 4:
                # Handle complex format like BW1-Bb 049/053
                expansion_code = f"{groups[0]}-{groups[1]}"
                collector_number = groups[2]
            else:
                continue
            return expansion_code, collector_number

    return None, None

def map_cards_by_code():
    """Map unmapped event cards to main database cards using card codes"""

    # Load card code cache
    code_cache = load_card_code_cache()
    print(f"Loaded {len(code_cache)} card codes from cache")

    # Connect to both databases
    event_conn = sqlite3.connect('ptcg_events.db')
    main_conn = sqlite3.connect('../PokemonDBByjules/PTCG_CardDB_Tc/pokemon_cards.db')

    event_cursor = event_conn.cursor()
    main_cursor = main_conn.cursor()

    print('=== MAPPING CARDS BY CODE ===')

    # Get all unmapped cards
    event_cursor.execute('''
        SELECT DISTINCT dc.card_id, dc.card_name
        FROM deck_cards dc
        LEFT JOIN card_mappings cm ON dc.card_id = cm.event_card_id
        WHERE cm.event_card_id IS NULL
        ORDER BY dc.card_id
    ''')

    unmapped_cards = event_cursor.fetchall()
    print(f'Found {len(unmapped_cards)} unmapped cards to process')

    mapped_count = 0
    skipped_count = 0

    for event_card_id, event_card_name in unmapped_cards:
        card_id_str = str(event_card_id)

        # Check if we have a code for this card
        if card_id_str in code_cache:
            card_code = code_cache[card_id_str]

            # Skip if code is None
            if card_code is None:
                print(f'  No code available: "{event_card_name}" (ID {event_card_id})')
                skipped_count += 1
                continue

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

                    # Insert mapping
                    try:
                        event_cursor.execute('''
                            INSERT INTO card_mappings (event_card_id, main_card_id, main_card_name)
                            VALUES (?, ?, ?)
                        ''', (event_card_id, main_card_id, main_card_name))

                        event_conn.commit()
                        mapped_count += 1
                        print(f'  Mapped: "{event_card_name}" ({card_code}) -> ID {main_card_id}: "{main_card_name}"')

                    except sqlite3.IntegrityError:
                        print(f'  Skipped (already exists): "{event_card_name}"')
                        skipped_count += 1
                else:
                    print(f'  No match in main DB: "{event_card_name}" ({card_code})')
                    skipped_count += 1
            else:
                print(f'  Could not parse code: "{event_card_name}" ({card_code})')
                skipped_count += 1
        else:
            print(f'  No code in cache: "{event_card_name}" (ID {event_card_id})')
            skipped_count += 1

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
    map_cards_by_code()