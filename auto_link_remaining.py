import sqlite3
import re

event_db = sqlite3.connect('ptcg_events.db')
main_db = sqlite3.connect(r'c:\AI_Server\Coding\PokemonDBByjules\PTCG_CardDB_Tc\pokemon_cards.db')

ec = event_db.cursor()
mc = main_db.cursor()

print("=== Improved Auto-Linking for Unmapped Cards ===\n")

# Get unmapped cards with codes
ec.execute("""
    SELECT DISTINCT dc.card_id, dc.card_name, dc.card_code
    FROM deck_cards dc
    LEFT JOIN card_mappings cm ON dc.card_id = cm.event_card_id
    WHERE cm.event_card_id IS NULL
    AND dc.card_code IS NOT NULL
    AND dc.card_code != ''
    AND dc.card_code != '無代碼'
    ORDER BY dc.card_name
""")

unmapped_cards = ec.fetchall()

print(f"Found {len(unmapped_cards)} unmapped cards with codes\n")

linked_count = 0
failed_count = 0
failed_cards = []

for card_id, card_name, card_code in unmapped_cards:
    # Parse expansion code and collector number
    code_match = re.match(r'^([A-Za-z0-9\-]+)\s+(\d+[A-Za-z]?)/(\d+)', card_code)
    
    if not code_match:
        failed_count += 1
        failed_cards.append((card_name, card_code, "Cannot parse code"))
        continue
    
    exp_code = code_match.group(1)
    collector_num = code_match.group(2)
    
    # Try exact match first (expansion code + collector number)
    mc.execute("""
        SELECT c.id, c.name, e.code, c.collector_number
        FROM cards c
        JOIN expansions e ON c.expansion_id = e.id
        WHERE e.code = ? AND c.collector_number = ?
    """, (exp_code, collector_num))
    
    match = mc.fetchone()
    
    if match:
        main_card_id, main_card_name, main_exp_code, main_collector = match
        
        # Insert mapping
        try:
            ec.execute("""
                INSERT OR REPLACE INTO card_mappings
                (event_card_id, event_card_name, event_card_code,
                 main_card_id, main_card_name, main_expansion_code,
                 main_collector_number, match_type, match_confidence)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (card_id, card_name, card_code,
                  main_card_id, main_card_name, main_exp_code,
                  main_collector, 'auto_code_match', 0.95))
            
            linked_count += 1
            print(f"✓ Linked: {card_name} ({card_code}) → {main_card_name}")
        except Exception as e:
            failed_count += 1
            failed_cards.append((card_name, card_code, str(e)))
    else:
        # Try name-based match in same expansion
        mc.execute("""
            SELECT c.id, c.name, e.code, c.collector_number
            FROM cards c
            JOIN expansions e ON c.expansion_id = e.id
            WHERE e.code = ? AND c.name LIKE ?
            LIMIT 1
        """, (exp_code, f'%{card_name}%'))
        
        name_match = mc.fetchone()
        
        if name_match:
            main_card_id, main_card_name, main_exp_code, main_collector = name_match
            
            try:
                ec.execute("""
                    INSERT OR REPLACE INTO card_mappings
                    (event_card_id, event_card_name, event_card_code,
                     main_card_id, main_card_name, main_expansion_code,
                     main_collector_number, match_type, match_confidence)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (card_id, card_name, card_code,
                      main_card_id, main_card_name, main_exp_code,
                      main_collector, 'auto_name_expansion', 0.85))
                
                linked_count += 1
                print(f"✓ Linked (name): {card_name} ({card_code}) → {main_card_name}")
            except Exception as e:
                failed_count += 1
                failed_cards.append((card_name, card_code, str(e)))
        else:
            failed_count += 1
            failed_cards.append((card_name, card_code, f"No match in {exp_code}"))

# Commit changes
event_db.commit()

print(f"\n{'='*60}")
print(f"✅ Successfully linked: {linked_count} cards")
print(f"❌ Failed to link: {failed_count} cards")

if failed_cards[:10]:
    print(f"\n❌ Sample Failed Cards (first 10):")
    for name, code, reason in failed_cards[:10]:
        print(f"  • {name} ({code})")
        print(f"    Reason: {reason}")

# Update statistics
ec.execute("SELECT COUNT(DISTINCT event_card_id) FROM card_mappings")
total_mapped = ec.fetchone()[0]

ec.execute("SELECT COUNT(DISTINCT card_id) FROM deck_cards")
total_cards = ec.fetchone()[0]

print(f"\n📊 Updated Statistics:")
print(f"  Total unique cards: {total_cards}")
print(f"  Mapped cards: {total_mapped} ({total_mapped/total_cards*100:.1f}%)")
print(f"  Unmapped cards: {total_cards - total_mapped} ({(total_cards - total_mapped)/total_cards*100:.1f}%)")

event_db.close()
main_db.close()
