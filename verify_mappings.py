import sqlite3
conn = sqlite3.connect('ptcg_events.db')
cursor = conn.cursor()

print('=== VERIFYING USER TRANSLATION MAPPINGS ===')

# Check a few mappings to ensure they're using correct Chinese names
cursor.execute('''
    SELECT cm.event_card_name, cm.main_card_name, ut.chinese_name,
           CASE WHEN cm.main_card_name = ut.chinese_name THEN 'MATCH' ELSE 'DIFFERENT' END as name_check
    FROM card_mappings cm
    JOIN user_translations ut ON cm.event_card_name = ut.japanese_name
    WHERE cm.match_type = 'user_translation'
    LIMIT 10
''')

results = cursor.fetchall()
print(f'Checked {len(results)} user translation mappings:')
for row in results:
    event_name, main_name, user_chinese, check = row
    status = '✅' if check == 'MATCH' else '⚠️'
    print(f'  {status} \"{event_name}\" -> \"{main_name}\" (user had: \"{user_chinese}\")')

# Check if any mappings have Japanese names as main_card_name
cursor.execute('''
    SELECT COUNT(*) FROM card_mappings
    WHERE match_type = 'user_translation'
    AND (main_card_name LIKE '%エネルギー%'
    OR main_card_name LIKE '%Energy%'
    OR main_card_name LIKE '%基本%')
''')

japanese_main_names = cursor.fetchone()[0]
print(f'\nMappings with Japanese names as main_card_name: {japanese_main_names}')

conn.close()
print('\n✅ Verification complete')