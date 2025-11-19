import sqlite3
import os
from datetime import datetime

# Backup database first
db_path = 'ptcg_events.db'
backup_path = f'ptcg_events_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.db'

print(f"📦 Creating backup: {backup_path}")
os.system(f'copy "{db_path}" "{backup_path}"')

# Connect to database
conn = sqlite3.connect(db_path)
c = conn.cursor()

print("\n=== Starting Duplicate Removal ===\n")

# Get count before cleanup
c.execute("SELECT COUNT(*) FROM deck_cards")
before_count = c.fetchone()[0]
print(f"📊 Total deck_cards entries before: {before_count}")

# Find duplicates
c.execute("""
    SELECT deck_id, card_id, card_name, card_code, quantity, COUNT(*) as cnt
    FROM deck_cards
    GROUP BY deck_id, card_id, card_name, card_code, quantity
    HAVING cnt > 1
""")

duplicates = c.fetchall()
print(f"❌ Found {len(duplicates)} groups of duplicates\n")

if len(duplicates) > 0:
    print("Removing duplicates (keeping one copy of each)...")
    
    # Create a temporary table with unique records
    c.execute("""
        CREATE TEMPORARY TABLE deck_cards_unique AS
        SELECT DISTINCT deck_id, card_id, card_name, card_code, quantity
        FROM deck_cards
    """)
    
    # Get count of unique records
    c.execute("SELECT COUNT(*) FROM deck_cards_unique")
    unique_count = c.fetchone()[0]
    print(f"✅ Unique records: {unique_count}")
    
    # Delete all records from deck_cards
    c.execute("DELETE FROM deck_cards")
    
    # Insert unique records back
    c.execute("""
        INSERT INTO deck_cards (deck_id, card_id, card_name, card_code, quantity)
        SELECT deck_id, card_id, card_name, card_code, quantity
        FROM deck_cards_unique
    """)
    
    # Drop temporary table
    c.execute("DROP TABLE deck_cards_unique")
    
    conn.commit()
    
    # Verify after cleanup
    c.execute("SELECT COUNT(*) FROM deck_cards")
    after_count = c.fetchone()[0]
    print(f"\n📊 Total deck_cards entries after: {after_count}")
    print(f"🗑️  Removed {before_count - after_count} duplicate entries")
    
    # Verify deck counts
    print("\n=== Verifying Deck Counts ===\n")
    
    c.execute("""
        SELECT d.deck_id, d.rank, SUM(dc.quantity) as total_cards
        FROM decks d
        JOIN deck_cards dc ON d.deck_id = dc.deck_id
        GROUP BY d.deck_id
        HAVING total_cards != 60
        LIMIT 10
    """)
    
    wrong_decks = c.fetchall()
    
    if wrong_decks:
        print(f"⚠️  Still found {len(wrong_decks)} decks with incorrect count:")
        for deck in wrong_decks:
            print(f"  Deck {deck[0]} (Rank: {deck[1]}): {deck[2]} cards")
    else:
        print("✅ All checked decks now have 60 cards!")
    
    # Sample verification
    print("\n=== Sample Deck Verification ===\n")
    c.execute("SELECT deck_id FROM decks LIMIT 1")
    sample_deck = c.fetchone()[0]
    
    c.execute("SELECT SUM(quantity) FROM deck_cards WHERE deck_id = ?", (sample_deck,))
    total = c.fetchone()[0]
    print(f"Sample deck {sample_deck}: {total} cards")
    
    if total == 60:
        print("✅ Sample deck is correct!")
    else:
        print(f"❌ Sample deck is incorrect (should be 60, got {total})")

else:
    print("✅ No duplicates found!")

conn.close()

print("\n✅ Cleanup complete!")
print(f"💾 Backup saved as: {backup_path}")
