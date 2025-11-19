#!/usr/bin/env python3
"""
Fix all incorrect card mappings that have Japanese names as main_card_name
"""

import sqlite3
import os

def fix_all_incorrect_mappings():
    """Fix all mappings where main_card_name contains Japanese text"""

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

    print('=== FIXING ALL INCORRECT CARD MAPPINGS ===')

    # Find all mappings with Japanese-like names
    event_cursor.execute('''
        SELECT cm.event_card_id, cm.event_card_name, cm.main_card_name, cm.main_card_id
        FROM card_mappings cm
        WHERE cm.main_card_name LIKE '%エネルギー%'
        OR cm.main_card_name LIKE '%Energy%'
        OR cm.main_card_name LIKE '%基本%'
        OR cm.main_card_name LIKE '%特殊%'
        OR cm.main_card_name LIKE '%サポート%'
        OR cm.main_card_name LIKE '%スタジアム%'
        OR cm.main_card_name LIKE '%ポケモン%'
        OR cm.main_card_name LIKE '%トレーナー%'
    ''')

    incorrect_mappings = event_cursor.fetchall()
    print(f'Found {len(incorrect_mappings)} mappings with Japanese names as main_card_name')

    if len(incorrect_mappings) == 0:
        print('✅ No incorrect mappings found!')
        event_conn.close()
        main_conn.close()
        return

    # Group by event_card_name to avoid duplicate processing
    card_groups = {}
    for event_card_id, event_card_name, incorrect_main_name, current_main_id in incorrect_mappings:
        if event_card_name not in card_groups:
            card_groups[event_card_name] = []
        card_groups[event_card_name].append((event_card_id, incorrect_main_name, current_main_id))

    print(f'Processing {len(card_groups)} unique card names')

    fixed_count = 0
    skipped_count = 0

    for event_card_name, mappings in card_groups.items():
        print(f'\nProcessing: "{event_card_name}" ({len(mappings)} mappings)')

        # First, try to find user translation
        event_cursor.execute('SELECT chinese_name FROM user_translations WHERE japanese_name = ?', (event_card_name,))
        user_translation = event_cursor.fetchone()

        correct_chinese_name = None

        if user_translation:
            correct_chinese_name = user_translation[0]
            print(f'  Found user translation: "{correct_chinese_name}"')
        else:
            # No user translation, try to find by expansion code and collector number
            # Extract expansion code and collector number from event_card_name if possible
            # Format is usually like "SV8a 120/187" or just the name

            # Try to find this card in the main database by name
            main_cursor.execute('''
                SELECT c.id, c.name, c.collector_number, e.code as expansion_code
                FROM cards c
                LEFT JOIN expansions e ON c.expansion_id = e.id
                WHERE c.name LIKE ?
                ORDER BY c.id
                LIMIT 5
            ''', (f'%{event_card_name}%',))

            possible_matches = main_cursor.fetchall()

            if possible_matches:
                print(f'  Found {len(possible_matches)} possible matches in main DB:')
                for match in possible_matches[:3]:
                    print(f'    - ID {match[0]}: "{match[1]}" ({match[3]} {match[2]})')

                # Use the first match as the most likely correct one
                correct_main_id, correct_main_name, collector_number, expansion_code = possible_matches[0]
                correct_chinese_name = correct_main_name
                print(f'  Using first match: "{correct_chinese_name}"')
            else:
                print(f'  ❌ No matches found in main database for "{event_card_name}"')
                skipped_count += len(mappings)
                continue

        # Now find the correct main card by Chinese name
        main_cursor.execute('''
            SELECT c.id, c.name, c.collector_number, e.code as expansion_code
            FROM cards c
            LEFT JOIN expansions e ON c.expansion_id = e.id
            WHERE c.name = ?
            ORDER BY c.id
            LIMIT 1
        ''', (correct_chinese_name,))

        correct_main_card = main_cursor.fetchone()

        if not correct_main_card:
            print(f'  ❌ Correct Chinese name "{correct_chinese_name}" not found in main database')
            skipped_count += len(mappings)
            continue

        new_main_id, new_main_name, collector_number, expansion_code = correct_main_card
        print(f'  ✅ Found correct main card: ID {new_main_id} - "{new_main_name}"')

        # Update all mappings for this card
        for event_card_id, incorrect_main_name, current_main_id in mappings:
            try:
                event_cursor.execute('''
                    UPDATE card_mappings
                    SET main_card_id = ?, main_card_name = ?, main_expansion_code = ?, main_collector_number = ?
                    WHERE event_card_id = ?
                ''', (new_main_id, new_main_name, expansion_code or '', collector_number or '', event_card_id))

                event_conn.commit()
                fixed_count += 1
                print(f'  ✅ Fixed mapping for event card {event_card_id}')

            except Exception as e:
                print(f'  ❌ Error updating mapping for event card {event_card_id}: {e}')
                skipped_count += 1

    print(f'\n=== SUMMARY ===')
    print(f'Successfully fixed: {fixed_count}')
    print(f'Skipped: {skipped_count}')
    print(f'Total processed: {fixed_count + skipped_count}')

    if fixed_count > 0:
        print('✅ Database changes saved')

    event_conn.close()
    main_conn.close()

if __name__ == '__main__':
    fix_all_incorrect_mappings()