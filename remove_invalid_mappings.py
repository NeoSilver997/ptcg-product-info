#!/usr/bin/env python3
"""
Remove invalid mappings that point to non-existent card IDs (>= 4859)
"""

import sqlite3
import os

def remove_invalid_mappings():
    """Remove mappings that point to card IDs that don't exist in the main database"""

    event_db_path = 'ptcg_events.db'
    main_db_path = '../PokemonDBByjules/PTCG_CardDB_Tc/pokemon_cards.db'

    if not os.path.exists(event_db_path):
        print(f"❌ Event database not found: {event_db_path}")
        return

    if not os.path.exists(main_db_path):
        print(f"❌ Main database not found: {main_db_path}")
        return

    # Connect to databases
    event_conn = sqlite3.connect(event_db_path)
    main_conn = sqlite3.connect(main_db_path)

    event_cursor = event_conn.cursor()
    main_cursor = main_conn.cursor()

    print('=== REMOVING INVALID MAPPINGS ===')

    # Get the maximum valid card ID from main database
    main_cursor.execute('SELECT MAX(id) FROM cards')
    max_valid_id = main_cursor.fetchone()[0]
    print(f'Maximum valid card ID in main database: {max_valid_id}')

    # Find mappings with invalid card IDs
    event_cursor.execute('SELECT COUNT(*) FROM card_mappings WHERE main_card_id > ?', (max_valid_id,))
    invalid_mappings = event_cursor.fetchone()[0]
    print(f'Found {invalid_mappings} mappings with invalid main_card_id (> {max_valid_id})')

    if invalid_mappings == 0:
        print('✅ No invalid mappings found!')
        event_conn.close()
        main_conn.close()
        return

    # Get sample of invalid mappings
    event_cursor.execute('''
        SELECT cm.event_card_id, cm.event_card_name, cm.main_card_id, cm.main_card_name
        FROM card_mappings cm
        WHERE cm.main_card_id > ?
        LIMIT 10
    ''', (max_valid_id,))
    sample_invalid = event_cursor.fetchall()

    print('\nSample invalid mappings:')
    for event_id, event_name, main_id, main_name in sample_invalid:
        print(f'  Event: "{event_name}" -> Invalid Main ID {main_id}: "{main_name}"')

    # Remove all invalid mappings
    print(f'\nRemoving {invalid_mappings} invalid mappings...')
    event_cursor.execute('DELETE FROM card_mappings WHERE main_card_id > ?', (max_valid_id,))
    event_conn.commit()

    print('✅ Invalid mappings removed')

    # Verify the removal
    event_cursor.execute('SELECT COUNT(*) FROM card_mappings WHERE main_card_id > ?', (max_valid_id,))
    remaining_invalid = event_cursor.fetchone()[0]
    print(f'Remaining invalid mappings: {remaining_invalid}')

    # Show final stats
    event_cursor.execute('SELECT COUNT(*) FROM card_mappings')
    total_mappings = event_cursor.fetchone()[0]
    print(f'Total mappings remaining: {total_mappings}')

    event_conn.close()
    main_conn.close()

if __name__ == '__main__':
    remove_invalid_mappings()