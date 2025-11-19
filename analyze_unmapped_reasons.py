import sqlite3

event_db = sqlite3.connect('ptcg_events.db')
main_db = sqlite3.connect(r'c:\AI_Server\Coding\PokemonDBByjules\PTCG_CardDB_Tc\pokemon_cards.db')

ec = event_db.cursor()
mc = main_db.cursor()

print("=== Analyzing Unmapped Cards ===\n")

# Get total unique cards in events
ec.execute("SELECT COUNT(DISTINCT card_id) FROM deck_cards")
total_cards = ec.fetchone()[0]

# Get mapped cards count
ec.execute("SELECT COUNT(DISTINCT event_card_id) FROM card_mappings")
mapped_cards = ec.fetchone()[0]

unmapped_cards = total_cards - mapped_cards

print(f"📊 Card Mapping Statistics:")
print(f"  Total unique cards: {total_cards}")
print(f"  Mapped cards: {mapped_cards} ({mapped_cards/total_cards*100:.1f}%)")
print(f"  Unmapped cards: {unmapped_cards} ({unmapped_cards/total_cards*100:.1f}%)")

# Get sample unmapped cards
print(f"\n❌ Sample Unmapped Cards (showing first 30):\n")

ec.execute("""
    SELECT DISTINCT dc.card_id, dc.card_name, dc.card_code
    FROM deck_cards dc
    LEFT JOIN card_mappings cm ON dc.card_id = cm.event_card_id
    WHERE cm.event_card_id IS NULL
    ORDER BY dc.card_name
    LIMIT 30
""")

unmapped = ec.fetchall()

for card in unmapped:
    card_id, card_name, card_code = card
    print(f"  [{card_id}] {card_name}")
    print(f"      Code: {card_code or '無代碼'}")
    
    # Try to find potential matches in main DB
    if card_code:
        # Extract expansion code
        import re
        code_match = re.match(r'^([A-Za-z0-9]+)', card_code)
        if code_match:
            exp_code = code_match.group(1)
            
            # Search in main DB by expansion
            mc.execute("""
                SELECT c.id, c.name, e.code, c.collector_number
                FROM cards c
                JOIN expansions e ON c.expansion_id = e.id
                WHERE e.code = ?
                LIMIT 3
            """, (exp_code,))
            
            potential = mc.fetchall()
            if potential:
                print(f"      💡 Found {len(potential)} cards in expansion {exp_code}:")
                for p in potential[:2]:
                    print(f"         • {p[1]} ({p[2]} {p[3]})")
    print()

# Check match types distribution
print("\n=== Match Type Distribution ===\n")
ec.execute("""
    SELECT match_type, COUNT(*) as count
    FROM card_mappings
    GROUP BY match_type
    ORDER BY count DESC
""")

match_types = ec.fetchall()
for match_type, count in match_types:
    print(f"  {match_type}: {count}")

# Check if there are cards with codes but not mapped
print("\n=== Cards with Codes but Unmapped ===\n")
ec.execute("""
    SELECT COUNT(DISTINCT dc.card_id)
    FROM deck_cards dc
    LEFT JOIN card_mappings cm ON dc.card_id = cm.event_card_id
    WHERE cm.event_card_id IS NULL
    AND dc.card_code IS NOT NULL
    AND dc.card_code != ''
""")

unmapped_with_code = ec.fetchone()[0]
print(f"Cards with expansion codes but unmapped: {unmapped_with_code}")

# Check expansion coverage
print("\n=== Expansion Code Analysis ===\n")
ec.execute("""
    SELECT SUBSTR(card_code, 1, INSTR(card_code || ' ', ' ') - 1) as exp_code, 
           COUNT(DISTINCT card_id) as card_count
    FROM deck_cards
    WHERE card_code IS NOT NULL AND card_code != ''
    GROUP BY exp_code
    ORDER BY card_count DESC
    LIMIT 15
""")

exp_stats = ec.fetchall()
print("Top 15 expansion codes in event data:")
for exp_code, count in exp_stats:
    # Check if expansion exists in main DB
    mc.execute("SELECT COUNT(*) FROM expansions WHERE code = ?", (exp_code,))
    exists = mc.fetchone()[0]
    status = "✓" if exists > 0 else "✗"
    print(f"  {status} {exp_code}: {count} cards")

event_db.close()
main_db.close()
