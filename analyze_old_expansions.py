import sqlite3

event_db = sqlite3.connect('ptcg_events.db')
ec = event_db.cursor()

print("=== Old Expansion Analysis ===\n")

# Get cards from old expansions (XY, BW, SA, etc.)
old_exp_prefixes = ['XY', 'BW', 'BKR', 'SA', 'BWR', 'MBD', 'MBG', 'SVF']

for prefix in old_exp_prefixes:
    ec.execute("""
        SELECT COUNT(DISTINCT card_id)
        FROM deck_cards
        WHERE card_code LIKE ?
    """, (f'{prefix}%',))
    
    count = ec.fetchone()[0]
    if count > 0:
        print(f"{prefix:10} : {count:4} unique cards")
        
        # Sample cards
        ec.execute("""
            SELECT DISTINCT card_name, card_code
            FROM deck_cards
            WHERE card_code LIKE ?
            LIMIT 3
        """, (f'{prefix}%',))
        
        samples = ec.fetchall()
        for name, code in samples:
            print(f"           - {name} ({code})")
        print()

# Total from old expansions
total_old = 0
for prefix in old_exp_prefixes:
    ec.execute("""
        SELECT COUNT(DISTINCT card_id)
        FROM deck_cards
        WHERE card_code LIKE ?
    """, (f'{prefix}%',))
    total_old += ec.fetchone()[0]

ec.execute("SELECT COUNT(DISTINCT card_id) FROM deck_cards")
total_cards = ec.fetchone()[0]

print(f"{'='*60}")
print(f"Total cards from old expansions: {total_old}")
print(f"Percentage: {total_old/total_cards*100:.1f}%")

# Check current mapping status
ec.execute("""
    SELECT COUNT(DISTINCT dc.card_id)
    FROM deck_cards dc
    LEFT JOIN card_mappings cm ON dc.card_id = cm.event_card_id
    WHERE cm.event_card_id IS NULL
""")
unmapped = ec.fetchone()[0]

print(f"\nTotal unmapped cards: {unmapped}")
print(f"Likely from old expansions: ~{total_old} ({total_old/unmapped*100:.1f}% of unmapped)")

event_db.close()
