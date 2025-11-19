import sqlite3

conn = sqlite3.connect('ptcg_events.db')
cursor = conn.cursor()

cursor.execute("""
    SELECT event_card_name, main_card_name, COUNT(*) as count 
    FROM card_mappings 
    WHERE event_card_name IN ('マキシマムベルト', 'プレシャスキャリー')
    GROUP BY event_card_name, main_card_name 
    ORDER BY event_card_name
""")

results = cursor.fetchall()
print('\n修復後的對應關係:')
print('='*60)
for jp, cn, count in results:
    print(f'{jp} → {cn}: {count} 個變體')
conn.close()
