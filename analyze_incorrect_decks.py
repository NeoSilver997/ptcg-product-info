import sqlite3

conn = sqlite3.connect('ptcg_events.db')
c = conn.cursor()

print("=== Checking Decks with Incorrect Count ===\n")

# Get all decks with count != 60
c.execute("""
    SELECT d.deck_id, d.rank, d.deck_url, SUM(dc.quantity) as total_cards
    FROM decks d
    JOIN deck_cards dc ON d.deck_id = dc.deck_id
    GROUP BY d.deck_id
    HAVING total_cards != 60
    ORDER BY total_cards
    LIMIT 20
""")

wrong_decks = c.fetchall()

print(f"Found {len(wrong_decks)} decks with incorrect count:\n")

for deck in wrong_decks:
    deck_id, rank, deck_url, total = deck
    print(f"Deck: {deck_id}")
    print(f"  Rank: {rank}")
    print(f"  Total: {total} cards")
    if deck_url:
        print(f"  URL: {deck_url}")
    print()

# Count all decks
c.execute("SELECT COUNT(*) FROM decks")
total_decks = c.fetchone()[0]

c.execute("""
    SELECT COUNT(DISTINCT d.deck_id)
    FROM decks d
    JOIN deck_cards dc ON d.deck_id = dc.deck_id
    GROUP BY d.deck_id
    HAVING SUM(dc.quantity) = 60
""")
correct_decks = c.fetchone()[0]

print(f"Summary:")
print(f"  Total decks: {total_decks}")
print(f"  Correct (60 cards): {correct_decks}")
print(f"  Incorrect: {total_decks - correct_decks}")
print(f"  Success rate: {(correct_decks / total_decks * 100):.2f}%")

# Check if these are edge cases (tournament rules might allow different counts)
print("\n=== Distribution of Incorrect Counts ===")
c.execute("""
    SELECT SUM(dc.quantity) as total_cards, COUNT(*) as deck_count
    FROM decks d
    JOIN deck_cards dc ON d.deck_id = dc.deck_id
    GROUP BY d.deck_id
    HAVING total_cards != 60
    ORDER BY total_cards
""")

distribution = c.fetchall()
for count, num_decks in distribution:
    print(f"  {count} cards: {num_decks} deck(s)")

conn.close()
