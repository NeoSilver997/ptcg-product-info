import sqlite3

# Import user translations from backup database
backup_db = 'ptcg_events_backup_20251116_010212.db'
current_db = 'ptcg_events.db'

print('Importing user translations from backup...')

# Get mappings from backup that are not in current
backup_conn = sqlite3.connect(backup_db)
backup_cursor = backup_conn.cursor()
backup_cursor.execute('SELECT event_card_id, event_card_name, main_card_id, main_card_name FROM card_mappings')
backup_mappings = backup_cursor.fetchall()
backup_conn.close()

# Get current mappings
current_conn = sqlite3.connect(current_db)
current_cursor = current_conn.cursor()
current_cursor.execute('SELECT event_card_id, main_card_id FROM card_mappings')
current_mappings = {row[0]: row[1] for row in current_cursor.fetchall()}

print(f'Backup has {len(backup_mappings)} total mappings')
print(f'Current has {len(current_mappings)} mappings')

imported = 0
updated = 0

# Import new mappings and update differing ones
for event_id, event_name, main_id, main_name in backup_mappings:
    if event_id not in current_mappings:
        # New mapping
        try:
            current_cursor.execute('''
                INSERT INTO card_mappings
                (event_card_id, event_card_name, main_card_id, main_card_name)
                VALUES (?, ?, ?, ?)
            ''', (event_id, event_name, main_id, main_name))
            imported += 1
        except Exception as e:
            print(f'Error importing event_card_id {event_id}: {e}')
    elif current_mappings[event_id] != main_id:
        # Update differing mapping
        try:
            current_cursor.execute('''
                UPDATE card_mappings
                SET main_card_id = ?, main_card_name = ?
                WHERE event_card_id = ?
            ''', (main_id, main_name, event_id))
            updated += 1
        except Exception as e:
            print(f'Error updating event_card_id {event_id}: {e}')

current_conn.commit()
current_conn.close()

print(f'Imported {imported} new mappings')
print(f'Updated {updated} existing mappings')
print('Import completed!')