import sqlite3

event_db = sqlite3.connect('ptcg_events.db')
main_db = sqlite3.connect(r'c:\AI_Server\Coding\PokemonDBByjules\PTCG_CardDB_Tc\pokemon_cards.db')

ec = event_db.cursor()
mc = main_db.cursor()

card_name = 'ボウルタウン'

print(f"=== Analyzing: {card_name} ===\n")

# Step 1: Check if card exists in event database
print("1️⃣ Checking event database:")
ec.execute("""
    SELECT DISTINCT card_id, card_name, card_code
    FROM deck_cards
    WHERE card_name = ?
""", (card_name,))

event_cards = ec.fetchall()

if event_cards:
    print(f"   ✓ Found {len(event_cards)} entries in deck_cards:")
    for card in event_cards:
        print(f"     • ID: {card[0]}, Code: {card[2]}")
else:
    print(f"   ✗ NOT found in deck_cards")

# Step 2: Check if card is mapped
print("\n2️⃣ Checking card mappings:")
for card_id, _, card_code in event_cards:
    ec.execute("""
        SELECT event_card_id, event_card_name, main_card_id, main_card_name, match_type
        FROM card_mappings
        WHERE event_card_id = ?
    """, (card_id,))
    
    mapping = ec.fetchone()
    
    if mapping:
        print(f"   ✓ Card ID {card_id} IS mapped:")
        print(f"     • Japanese: {mapping[1]}")
        print(f"     • Chinese ID: {mapping[2]}")
        print(f"     • Chinese: {mapping[3]}")
        print(f"     • Match type: {mapping[4]}")
    else:
        print(f"   ✗ Card ID {card_id} NOT mapped")
        
        # Try to find potential matches
        print(f"\n   🔍 Searching for potential matches...")
        
        # Try code-based search
        if card_code and card_code != '無代碼':
            import re
            code_match = re.match(r'^([A-Za-z0-9\-]+)\s+(\d+[A-Za-z]?)/(\d+)', card_code)
            if code_match:
                exp_code = code_match.group(1)
                collector = code_match.group(2)
                
                print(f"   📋 Parsed code: {exp_code} {collector}")
                
                mc.execute("""
                    SELECT c.id, c.name, e.code, c.collector_number
                    FROM cards c
                    JOIN expansions e ON c.expansion_id = e.id
                    WHERE e.code = ? AND c.collector_number = ?
                """, (exp_code, collector))
                
                exact_match = mc.fetchone()
                if exact_match:
                    print(f"   ✓ FOUND exact match by code:")
                    print(f"     • ID: {exact_match[0]}")
                    print(f"     • Name: {exact_match[1]}")
                    print(f"     • Code: {exact_match[2]} {exact_match[3]}")
                else:
                    print(f"   ✗ No exact match for {exp_code} {collector}")
                    
                    # Try finding any card in that expansion
                    mc.execute("""
                        SELECT c.id, c.name, c.collector_number, c.card_type
                        FROM cards c
                        JOIN expansions e ON c.expansion_id = e.id
                        WHERE e.code = ?
                        ORDER BY c.collector_number
                        LIMIT 5
                    """, (exp_code,))
                    
                    sample_cards = mc.fetchall()
                    if sample_cards:
                        print(f"   💡 Sample cards in {exp_code}:")
                        for sc in sample_cards:
                            print(f"     • {sc[1]} ({sc[2]}) - {sc[3]}")

# Step 3: Try name search in Chinese DB
print("\n3️⃣ Searching Chinese database by name:")

possible_chinese = ['寶可鎮', '碗鎮', '寶可夢鎮', '鎮']

for cn_name in possible_chinese:
    mc.execute("""
        SELECT id, name, card_type
        FROM cards
        WHERE name LIKE ?
        LIMIT 3
    """, (f'%{cn_name}%',))
    
    results = mc.fetchall()
    if results:
        print(f"\n   🔍 Search '{cn_name}':")
        for r in results:
            print(f"     • ID {r[0]}: {r[1]} ({r[2]})")

# Step 4: Check if it's a Stadium card
print("\n4️⃣ Checking for Stadium cards (競技場):")
mc.execute("""
    SELECT id, name, card_type
    FROM cards
    WHERE card_type = '競技場'
    AND name LIKE '%鎮%'
""")

stadiums = mc.fetchall()
if stadiums:
    print(f"   Found {len(stadiums)} stadium cards with '鎮':")
    for s in stadiums:
        print(f"     • ID {s[0]}: {s[1]}")

event_db.close()
main_db.close()
