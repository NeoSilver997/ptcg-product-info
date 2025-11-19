#!/usr/bin/env python3
"""
Complete missing card_id links using existing user_translations
"""

import sqlite3
import os
from pathlib import Path

def analyze_user_translations():
    """Analyze current state of user_translations table"""
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

    print('=== USER TRANSLATIONS ANALYSIS ===')

    # Check user_translations table structure
    event_cursor.execute('PRAGMA table_info(user_translations)')
    columns = event_cursor.fetchall()
    print('User translations table columns:')
    for col in columns:
        print(f'  {col[1]} ({col[2]})')

    # Get total user translations
    event_cursor.execute('SELECT COUNT(*) FROM user_translations')
    total_translations = event_cursor.fetchone()[0]
    print(f'\nTotal user translations: {total_translations}')

    # Check which user translations are already linked
    event_cursor.execute('''
        SELECT COUNT(DISTINCT ut.japanese_name)
        FROM user_translations ut
        JOIN card_mappings cm ON ut.japanese_name = cm.event_card_name
    ''')
    linked_translations = event_cursor.fetchone()[0]
    print(f'User translations already linked in card_mappings: {linked_translations}')

    # Find unlinked user translations
    event_cursor.execute('''
        SELECT ut.japanese_name, ut.chinese_name, ut.created_at
        FROM user_translations ut
        LEFT JOIN card_mappings cm ON ut.japanese_name = cm.event_card_name
        WHERE cm.event_card_id IS NULL
        ORDER BY ut.created_at DESC
    ''')
    unlinked = event_cursor.fetchall()
    print(f'\nUnlinked user translations: {len(unlinked)}')

    if len(unlinked) == 0:
        print('✅ All user translations are already linked!')
        event_conn.close()
        main_conn.close()
        return

    print('\nFirst 10 unlinked translations:')
    for i, trans in enumerate(unlinked[:10]):
        print(f'  {i+1}. "{trans[0]}" -> "{trans[1]}" ({trans[2]})')

    # Now try to link them
    print(f'\n=== ATTEMPTING TO LINK {len(unlinked)} UNLINKED TRANSLATIONS ===')

    linked_count = 0
    skipped_count = 0

    for japanese_name, chinese_name, created_at in unlinked:
        print(f'\nProcessing: "{japanese_name}" -> "{chinese_name}"')

        # Find the event card ID for this Japanese name
        event_cursor.execute('''
            SELECT dc.card_id, dc.card_name, dc.card_code, COUNT(DISTINCT dc.deck_id) as deck_count
            FROM deck_cards dc
            WHERE dc.card_name = ?
            GROUP BY dc.card_id
            ORDER BY deck_count DESC
            LIMIT 1
        ''', (japanese_name,))

        event_card = event_cursor.fetchone()

        if not event_card:
            print(f'  ❌ No event card found for "{japanese_name}"')
            skipped_count += 1
            continue

        event_card_id, event_card_name, event_card_code, deck_count = event_card
        print(f'  ✅ Found event card ID {event_card_id} (used in {deck_count} decks)')

        # Check if this card is already mapped
        event_cursor.execute('SELECT * FROM card_mappings WHERE event_card_id = ?', (event_card_id,))
        existing_mapping = event_cursor.fetchone()

        if existing_mapping:
            print(f'  ⚠️  Event card {event_card_id} already has a mapping, skipping')
            skipped_count += 1
            continue

        # Find the main card ID by Chinese name
        main_cursor.execute('''
            SELECT c.id, c.name, c.collector_number, e.code as expansion_code
            FROM cards c
            LEFT JOIN expansions e ON c.expansion_id = e.id
            WHERE c.name = ?
            ORDER BY c.id
        ''', (chinese_name,))

        main_cards = main_cursor.fetchall()

        if not main_cards:
            print(f'  ❌ No main card found for Chinese name "{chinese_name}"')
            skipped_count += 1
            continue

        if len(main_cards) > 1:
            print(f'  ⚠️  Multiple main cards found for "{chinese_name}":')
            for card in main_cards[:3]:
                print(f'     - ID {card[0]}: {card[1]} ({card[3]} {card[2]})')
            # Use the first one
            main_card_id, main_card_name, collector_number, expansion_code = main_cards[0]
            print(f'  Using first match: ID {main_card_id}')
        else:
            main_card_id, main_card_name, collector_number, expansion_code = main_cards[0]
            print(f'  ✅ Found main card ID {main_card_id}: {main_card_name}')

        # Create the mapping
        try:
            event_cursor.execute('''
                INSERT INTO card_mappings
                (event_card_id, event_card_name, event_card_code,
                 main_card_id, main_card_name, main_expansion_code,
                 main_collector_number, match_type, match_confidence)
                VALUES (?, ?, ?, ?, ?, ?, ?, 'user_translation', 1.0)
            ''', (event_card_id, japanese_name, event_card_code or '',
                  main_card_id, main_card_name, expansion_code or '',
                  collector_number or '',))

            event_conn.commit()
            linked_count += 1
            print(f'  ✅ Successfully linked event card {event_card_id} to main card {main_card_id}')

        except Exception as e:
            print(f'  ❌ Error creating mapping: {e}')
            skipped_count += 1

    print(f'\n=== SUMMARY ===')
    print(f'Successfully linked: {linked_count}')
    print(f'Skipped: {skipped_count}')
    print(f'Total processed: {linked_count + skipped_count}')

    # Save the event database
    event_conn.commit()
    print('✅ Database changes saved')

    event_conn.close()
    main_conn.close()

if __name__ == '__main__':
    analyze_user_translations()