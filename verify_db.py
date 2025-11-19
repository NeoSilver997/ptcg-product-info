import sqlite3

conn = sqlite3.connect('ptcg_events.db')
cursor = conn.cursor()

# Check tables
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [row[0] for row in cursor.fetchall()]
print(f"Tables: {tables}")

# Check counts
cursor.execute("SELECT COUNT(*) FROM events")
print(f"Events: {cursor.fetchone()[0]}")

cursor.execute("SELECT COUNT(*) FROM players")
print(f"Players: {cursor.fetchone()[0]}")

cursor.execute("SELECT COUNT(*) FROM decks")
print(f"Decks: {cursor.fetchone()[0]}")

cursor.execute("SELECT COUNT(*) FROM deck_cards")
print(f"Deck Cards: {cursor.fetchone()[0]}")

conn.close()
print("\n✅ Database verification successful!")
