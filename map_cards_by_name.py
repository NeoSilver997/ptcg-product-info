import sqlite3
import re

def normalize_name(name):
    """Normalize card names for better matching"""
    # Remove extra whitespace
    name = name.strip()
    # Remove special characters that might differ
    name = re.sub(r'[^\w\s\u4e00-\u9fff]', '', name)  # Keep Chinese characters and alphanumeric
    return name

def map_cards_by_name():
    """Map unmapped event cards to main database cards by name matching"""

    # Connect to both databases
    event_conn = sqlite3.connect('ptcg_events.db')
    main_conn = sqlite3.connect('../PokemonDBByjules/PTCG_CardDB_Tc/pokemon_cards.db')

    event_cursor = event_conn.cursor()
    main_cursor = main_conn.cursor()

    print('=== MAPPING CARDS BY NAME ===')

    # Get all unmapped cards
    event_cursor.execute('''
        SELECT DISTINCT dc.card_id, dc.card_name
        FROM deck_cards dc
        LEFT JOIN card_mappings cm ON dc.card_id = cm.event_card_id
        WHERE cm.event_card_id IS NULL
        ORDER BY dc.card_name
    ''')

    unmapped_cards = event_cursor.fetchall()
    print(f'Found {len(unmapped_cards)} unmapped cards to process')

    # Get all cards from main database for name matching
    main_cursor.execute('SELECT id, name FROM cards')
    main_cards = main_cursor.fetchall()

    # Create lookup dict for faster matching
    main_name_to_id = {}
    for card_id, name in main_cards:
        normalized = normalize_name(name)
        if normalized not in main_name_to_id:
            main_name_to_id[normalized] = []
        main_name_to_id[normalized].append(card_id)

    mapped_count = 0
    skipped_count = 0

    for event_card_id, event_card_name in unmapped_cards:
        normalized_event_name = normalize_name(event_card_name)

        # Try exact normalized name match
        if normalized_event_name in main_name_to_id:
            main_card_ids = main_name_to_id[normalized_event_name]

            # If multiple matches, take the first one (could be improved)
            main_card_id = main_card_ids[0]

            # Insert mapping
            try:
                event_cursor.execute('''
                    INSERT INTO card_mappings (event_card_id, main_card_id, main_card_name)
                    SELECT ?, c.id, c.name
                    FROM cards c
                    WHERE c.id = ?
                ''', (event_card_id, main_card_id))

                event_conn.commit()
                mapped_count += 1
                print(f'  Mapped: "{event_card_name}" -> ID {main_card_id}')

            except sqlite3.IntegrityError:
                print(f'  Skipped (already exists): "{event_card_name}"')
                skipped_count += 1
        else:
            print(f'  No match found: "{event_card_name}"')
            skipped_count += 1

    print(f'\n=== MAPPING COMPLETE ===')
    print(f'Mapped: {mapped_count} cards')
    print(f'Skipped/No match: {skipped_count} cards')

    # Verify the mappings
    event_cursor.execute('SELECT COUNT(*) FROM card_mappings')
    total_mappings = event_cursor.fetchone()[0]
    print(f'Total mappings now: {total_mappings}')

    event_conn.close()
    main_conn.close()

if __name__ == '__main__':
    map_cards_by_name()