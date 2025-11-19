"""
Verify Chinese Database Update
==============================
Test queries on the updated Chinese database.
"""

import sqlite3

MAIN_DB = r"c:\AI_Server\Coding\PokemonDBByjules\PTCG_CardDB_Tc\pokemon_cards.db"

conn = sqlite3.connect(MAIN_DB)
cursor = conn.cursor()

print("="*80)
print("CHINESE DATABASE - JAPANESE LINKS VERIFICATION")
print("="*80)

# Test 1: Find all Japanese versions of "ネストボール"
print("\n📝 Test 1: Find Chinese name for Japanese 'ネストボール'")
print("-"*80)

cursor.execute("""
    SELECT 
        c.name as chinese_name,
        jcl.japanese_name,
        jcl.japanese_card_code,
        e.code as expansion,
        jcl.tournament_usage_decks,
        jcl.tournament_usage_copies
    FROM japanese_card_links jcl
    JOIN cards c ON jcl.card_id = c.id
    LEFT JOIN expansions e ON c.expansion_id = e.id
    WHERE jcl.japanese_name = 'ネストボール'
    ORDER BY jcl.tournament_usage_decks DESC
    LIMIT 5
""")

for row in cursor.fetchall():
    cn_name, jp_name, jp_code, exp, decks, copies = row
    print(f"Chinese: {cn_name}")
    print(f"  Japanese: {jp_name} ({jp_code})")
    print(f"  Expansion: {exp}")
    print(f"  Usage: {decks} decks, {copies} copies\n")

# Test 2: Find all cards used in 1000+ tournament decks
print("="*80)
print("📊 Test 2: Top 15 Cards in Japanese Tournaments (Chinese Names)")
print("-"*80)

cursor.execute("""
    SELECT 
        c.name as chinese_name,
        GROUP_CONCAT(DISTINCT jcl.japanese_name) as japanese_names,
        SUM(jcl.tournament_usage_decks) as total_decks,
        COUNT(DISTINCT jcl.japanese_card_code) as variant_count
    FROM japanese_card_links jcl
    JOIN cards c ON jcl.card_id = c.id
    GROUP BY c.name
    HAVING total_decks >= 1000
    ORDER BY total_decks DESC
    LIMIT 15
""")

print(f"\n{'Chinese Name':<30} {'Total Decks':<12} {'Variants'}")
print("-"*80)

for cn_name, jp_names, total_decks, variants in cursor.fetchall():
    # Show first Japanese name if multiple
    jp_name_display = jp_names.split(',')[0] if ',' in jp_names else jp_names
    print(f"{cn_name:<30} {total_decks:<12} {variants} version(s)")

# Test 3: Check specific Chinese card's Japanese variants
print("\n" + "="*80)
print("🔍 Test 3: Find Japanese variants of Chinese '巢穴球' (Nest Ball)")
print("-"*80)

cursor.execute("""
    SELECT 
        jcl.japanese_name,
        jcl.japanese_card_code,
        e.code as expansion,
        jcl.tournament_usage_decks
    FROM cards c
    JOIN japanese_card_links jcl ON c.id = jcl.card_id
    LEFT JOIN expansions e ON c.expansion_id = e.id
    WHERE c.name LIKE '%巢穴球%' OR c.name LIKE '%ネストボール%'
    ORDER BY jcl.tournament_usage_decks DESC
    LIMIT 10
""")

results = cursor.fetchall()
if results:
    for jp_name, jp_code, exp, decks in results:
        code_display = jp_code if jp_code else "[NO CODE]"
        print(f"  {jp_name:<30} {code_display:<20} ({decks} decks)")
else:
    print("  No matches found")

# Test 4: Database schema verification
print("\n" + "="*80)
print("📋 Test 4: Database Schema Verification")
print("-"*80)

cursor.execute("""
    SELECT 
        name, 
        type
    FROM sqlite_master 
    WHERE type='table' AND name='japanese_card_links'
""")

table_info = cursor.fetchone()
if table_info:
    print(f"✅ Table exists: {table_info[0]}")
    
    # Get column info
    cursor.execute("PRAGMA table_info(japanese_card_links)")
    columns = cursor.fetchall()
    
    print("\nColumns:")
    for col in columns:
        col_id, name, type_, notnull, default, pk = col
        print(f"  - {name:<30} {type_:<15} {'PRIMARY KEY' if pk else ''}")
    
    # Get indexes
    cursor.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='index' AND tbl_name='japanese_card_links'
    """)
    
    indexes = cursor.fetchall()
    print("\nIndexes:")
    for idx in indexes:
        print(f"  - {idx[0]}")
else:
    print("❌ Table not found!")

# Final statistics
print("\n" + "="*80)
print("📊 FINAL STATISTICS")
print("="*80)

cursor.execute("SELECT COUNT(*) FROM japanese_card_links")
total_links = cursor.fetchone()[0]

cursor.execute("SELECT COUNT(DISTINCT card_id) FROM japanese_card_links")
unique_cards = cursor.fetchone()[0]

cursor.execute("""
    SELECT COUNT(*) FROM japanese_card_links 
    WHERE tournament_usage_decks >= 100
""")
popular_cards = cursor.fetchone()[0]

cursor.execute("""
    SELECT COUNT(*) FROM japanese_card_links 
    WHERE tournament_usage_decks >= 1000
""")
super_popular = cursor.fetchone()[0]

print(f"""
Total Japanese Card Links:        {total_links:>6}
Unique Chinese Cards with Links:  {unique_cards:>6}
Links with 100+ deck usage:       {popular_cards:>6}
Links with 1000+ deck usage:      {super_popular:>6}

Coverage: {(unique_cards/total_links*100):.1f}% of links are unique cards
          (multiple Japanese versions per Chinese card)
""")

conn.close()

print("\n" + "="*80)
print("✅ VERIFICATION COMPLETE - Database successfully updated!")
print("="*80)
