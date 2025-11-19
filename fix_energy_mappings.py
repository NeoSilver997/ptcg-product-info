#!/usr/bin/env python3
"""
Fix energy card mappings with correct Chinese names
"""

import sqlite3
import os

def fix_energy_mappings():
    """Fix energy card mappings using correct Chinese names"""

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

    print('=== FIXING ENERGY CARD MAPPINGS ===')

    # Japanese to Chinese energy mapping
    energy_mapping = {
        '基本炎エネルギー': ['基本【火】能量', '基本火能量'],
        '基本水エネルギー': ['基本【水】能量', '基本水能量'],
        '基本雷エネルギー': ['基本【雷】能量', '基本雷能量'],
        '基本草エネルギー': ['基本【草】能量', '基本草能量'],
        '基本闘エネルギー': ['基本【鬥】能量', '基本鬥能量'],
        '基本超エネルギー': ['基本【超】能量', '基本超能量'],
        '基本悪エネルギー': ['基本【惡】能量', '基本惡能量'],
        '基本鋼エネルギー': ['基本【鋼】能量', '基本鋼能量'],
    }

    # Trainer card mappings (some common ones)
    trainer_mapping = {
        'ポケモンいれかえ': '寶可夢交換',
        'エネルギーつけかえ': '能量轉移',
        'スーパーエネルギー回収': '超級能量回収',  # May need to check actual name
        'プリズムエネルギー': '稜鏡能量',
        'ジェットエネルギー': '噴射能量',
        'ルミナスエネルギー': '夜光能量',
        'ミストエネルギー': '薄霧能量',
        'レガシーエネルギー': '傳承能量',
        'イグニッションエネルギー': '點火能量',
    }

    fixed_count = 0
    skipped_count = 0

    # Process energy mappings
    for japanese_name, chinese_options in energy_mapping.items():
        print(f'\nProcessing energy: "{japanese_name}"')

        # Find event card IDs for this Japanese name
        event_cursor.execute('''
            SELECT dc.card_id, dc.card_name, COUNT(DISTINCT dc.deck_id) as deck_count
            FROM deck_cards dc
            WHERE dc.card_name = ?
            GROUP BY dc.card_id
        ''', (japanese_name,))

        event_cards = event_cursor.fetchall()

        if not event_cards:
            print(f'  No event cards found for "{japanese_name}"')
            continue

        print(f'  Found {len(event_cards)} event card entries')

        # Try each Chinese option
        correct_main_card = None
        for chinese_name in chinese_options:
            main_cursor.execute('''
                SELECT c.id, c.name, c.collector_number, e.code as expansion_code
                FROM cards c
                LEFT JOIN expansions e ON c.expansion_id = e.id
                WHERE c.name = ?
                LIMIT 1
            ''', (chinese_name,))

            result = main_cursor.fetchone()
            if result:
                correct_main_card = result
                print(f'  ✅ Found Chinese card: "{chinese_name}" (ID {result[0]})')
                break

        if not correct_main_card:
            print(f'  ❌ No Chinese card found for options: {chinese_options}')
            skipped_count += len(event_cards)
            continue

        new_main_id, new_main_name, collector_number, expansion_code = correct_main_card

        # Update all mappings for this Japanese name
        for event_card_id, event_card_name, deck_count in event_cards:
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

    # Process trainer card mappings
    print('\n=== PROCESSING TRAINER CARDS ===')

    for japanese_name, chinese_name in trainer_mapping.items():
        print(f'\nProcessing trainer: "{japanese_name}" -> "{chinese_name}"')

        # Find event card IDs
        event_cursor.execute('''
            SELECT dc.card_id, dc.card_name, COUNT(DISTINCT dc.deck_id) as deck_count
            FROM deck_cards dc
            WHERE dc.card_name = ?
            GROUP BY dc.card_id
        ''', (japanese_name,))

        event_cards = event_cursor.fetchall()

        if not event_cards:
            print(f'  No event cards found for "{japanese_name}"')
            continue

        print(f'  Found {len(event_cards)} event card entries')

        # Find Chinese card
        main_cursor.execute('''
            SELECT c.id, c.name, c.collector_number, e.code as expansion_code
            FROM cards c
            LEFT JOIN expansions e ON c.expansion_id = e.id
            WHERE c.name = ?
            LIMIT 1
        ''', (chinese_name,))

        correct_main_card = main_cursor.fetchone()

        if not correct_main_card:
            print(f'  ❌ Chinese card "{chinese_name}" not found')
            skipped_count += len(event_cards)
            continue

        new_main_id, new_main_name, collector_number, expansion_code = correct_main_card
        print(f'  ✅ Found Chinese card: "{new_main_name}" (ID {new_main_id})')

        # Update mappings
        for event_card_id, event_card_name, deck_count in event_cards:
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
    fix_energy_mappings()