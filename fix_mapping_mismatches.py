import sqlite3

# Connect to both databases
event_conn = sqlite3.connect('ptcg_events.db')
main_conn = sqlite3.connect('../PokemonDBByjules/PTCG_CardDB_Tc/pokemon_cards.db')

event_cursor = event_conn.cursor()
main_cursor = main_conn.cursor()

print('=== FIXING NAME/ID MISMATCHES IN CARD_MAPPINGS ===')

# Get all mismatches
mismatches = []
event_cursor.execute('SELECT DISTINCT main_card_name, main_card_id FROM card_mappings')

for name, mapped_id in event_cursor.fetchall():
    # Find the correct ID for this name
    main_cursor.execute('SELECT id FROM cards WHERE name = ?', (name,))
    correct_result = main_cursor.fetchone()

    if correct_result:
        correct_id = correct_result[0]
        if correct_id != mapped_id:
            mismatches.append((name, mapped_id, correct_id))

print(f'Found {len(mismatches)} mismatches to fix')

# Fix the mismatches
fixed_count = 0
for name, wrong_id, correct_id in mismatches:
    # Update the mapping
    event_cursor.execute('''
        UPDATE card_mappings
        SET main_card_id = ?
        WHERE main_card_name = ? AND main_card_id = ?
    ''', (correct_id, name, wrong_id))

    event_conn.commit()
    fixed_count += 1

    if fixed_count % 100 == 0:
        print(f'Fixed {fixed_count} mappings...')

print(f'\\n=== FIX COMPLETE ===')
print(f'Fixed {fixed_count} mismatched mappings')

# Verify the fix
print('\\n=== VERIFICATION ===')

# Check remaining mismatches
remaining_mismatches = []
event_cursor.execute('SELECT DISTINCT main_card_name, main_card_id FROM card_mappings')

for name, mapped_id in event_cursor.fetchall():
    main_cursor.execute('SELECT id FROM cards WHERE name = ?', (name,))
    correct_result = main_cursor.fetchone()

    if correct_result:
        correct_id = correct_result[0]
        if correct_id != mapped_id:
            remaining_mismatches.append((name, mapped_id, correct_id))

if remaining_mismatches:
    print(f'Still have {len(remaining_mismatches)} mismatches')
else:
    print('All mismatches fixed!')

# Check total mappings
event_cursor.execute('SELECT COUNT(*) FROM card_mappings')
total_mappings = event_cursor.fetchone()[0]
print(f'Total mappings: {total_mappings}')

event_conn.close()
main_conn.close()