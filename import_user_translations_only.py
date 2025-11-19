import sqlite3

# Import user translations from backup database (NOT card_mappings)
backup_db = 'ptcg_events_backup_20251116_010212.db'
current_db = 'ptcg_events.db'

print('Importing user translations from backup database...')

# Get translations from backup
backup_conn = sqlite3.connect(backup_db)
backup_cursor = backup_conn.cursor()
backup_cursor.execute('SELECT japanese_name, chinese_name, created_at, updated_at FROM user_translations')
backup_translations = backup_cursor.fetchall()
backup_conn.close()

# Get current translations
current_conn = sqlite3.connect(current_db)
current_cursor = current_conn.cursor()
current_cursor.execute('SELECT japanese_name, chinese_name FROM user_translations')
current_translations = {(row[0], row[1]) for row in current_cursor.fetchall()}

print(f'Backup has {len(backup_translations)} user translations')
print(f'Current has {len(current_translations)} user translations')

imported = 0
skipped = 0

# Import new translations
for japanese_name, chinese_name, created_at, updated_at in backup_translations:
    translation_key = (japanese_name, chinese_name)

    if translation_key not in current_translations:
        # New translation
        try:
            current_cursor.execute('''
                INSERT INTO user_translations
                (japanese_name, chinese_name, created_at, updated_at)
                VALUES (?, ?, ?, ?)
            ''', (japanese_name, chinese_name, created_at, updated_at))
            imported += 1
            print(f'Imported: {japanese_name} -> {chinese_name}')
        except Exception as e:
            print(f'Error importing {japanese_name}: {e}')
    else:
        skipped += 1

current_conn.commit()
current_conn.close()

print(f'\\nImport completed!')
print(f'Imported {imported} new translations')
print(f'Skipped {skipped} existing translations')
print(f'Total translations now: {len(current_translations) + imported}')