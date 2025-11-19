"""Quick verification script to check old format decks were removed."""
import sqlite3

conn = sqlite3.connect('ptcg_events.db')
c = conn.cursor()

# Get basic stats
c.execute('SELECT COUNT(*) FROM decks')
decks = c.fetchone()[0]

c.execute('SELECT COUNT(*) FROM deck_cards')
cards = c.fetchone()[0]

c.execute('SELECT AVG(card_count) FROM (SELECT deck_id, COUNT(*) as card_count FROM deck_cards GROUP BY deck_id)')
avg = c.fetchone()[0]

print(f'Current Database Stats:')
print(f'  Decks: {decks:,}')
print(f'  Deck Cards: {cards:,}')
print(f'  Avg cards per deck: {avg:.2f}')

# Check for remaining old format cards
print('\nVerifying no old format cards remain...')

# Check for GX cards
c.execute("SELECT COUNT(DISTINCT deck_id) FROM deck_cards WHERE card_name LIKE '%GX'")
gx_count = c.fetchone()[0]
print(f'  Decks with GX cards: {gx_count}')

# Check for VMAX cards
c.execute("SELECT COUNT(DISTINCT deck_id) FROM deck_cards WHERE card_name LIKE '%VMAX'")
vmax_count = c.fetchone()[0]
print(f'  Decks with VMAX cards: {vmax_count}')

# Check for V cards (but not VMAX or VSTAR)
c.execute("SELECT COUNT(DISTINCT deck_id) FROM deck_cards WHERE card_name LIKE '%V' AND card_name NOT LIKE '%VMAX' AND card_name NOT LIKE '%VSTAR' AND card_name NOT LIKE '%VIPパス'")
v_count = c.fetchone()[0]
print(f'  Decks with V cards: {v_count}')

# Check for ヒスイのヘビーボール
c.execute("SELECT COUNT(DISTINCT deck_id) FROM deck_cards WHERE card_name = 'ヒスイのヘビーボール'")
heavy_ball_count = c.fetchone()[0]
print(f'  Decks with ヒスイのヘビーボール: {heavy_ball_count}')

print('\n✓ Verification complete!')
conn.close()
