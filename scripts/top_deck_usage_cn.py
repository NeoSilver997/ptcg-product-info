import sqlite3, os
from pathlib import Path

cdir = Path(__file__).resolve().parents[1]

cards_db = cdir / 'pokemon_cards.db'
events_db = cdir / 'ptcg_events.db'

if not events_db.exists() or not cards_db.exists():
    print('Missing DB(s)', events_db.exists(), cards_db.exists())
    raise SystemExit

conn = sqlite3.connect(str(events_db))
conn.row_factory = sqlite3.Row
cur = conn.cursor()

cur.execute('''
SELECT card_name, COUNT(DISTINCT deck_id) as deck_count
FROM deck_cards
GROUP BY card_name
ORDER BY deck_count DESC
LIMIT 30
''')
rows = cur.fetchall()

conn2 = sqlite3.connect(str(cards_db))
conn2.row_factory = sqlite3.Row
cur2 = conn2.cursor()

print('Top 30 (JP name) -> find matching CN name and type')
print(f"{'deck_count':>8}  {'jp_name':40}  {'cn_name':40}  type")
for r in rows:
    jp = r['card_name']
    deck_count = r['deck_count']
    # Lookup in cards DB where japanese_name or name matches
    cur2.execute('''
        SELECT c.id, c.name as cn_name, c.card_type
        FROM cards c
        LEFT JOIN japanese_card_links j ON c.id = j.card_id
        WHERE LOWER(j.japanese_name)=? OR LOWER(c.name) = ?
        LIMIT 1
    ''', (jp.lower(), jp))
    res = cur2.fetchone()
    cn = res['cn_name'] if res else ''
    ctype = res['card_type'] if res else ''
    print(f"{deck_count:8}  {jp:40}  {cn:40}  {ctype}")

conn.close()
conn2.close()
