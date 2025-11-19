"""
Update Chinese Database with Card Links
========================================
Adds Japanese card information to the main Chinese database.

Creates a new table 'japanese_card_links' in the main database
to store references to Japanese event cards.
"""

import sqlite3

EVENT_DB = "ptcg_events.db"
MAIN_DB = r"c:\AI_Server\Coding\PokemonDBByjules\PTCG_CardDB_Tc\pokemon_cards.db"

def update_chinese_database():
    """Add Japanese card link information to Chinese database"""
    
    event_conn = sqlite3.connect(EVENT_DB)
    main_conn = sqlite3.connect(MAIN_DB)
    
    event_cursor = event_conn.cursor()
    main_cursor = main_conn.cursor()
    
    print("="*80)
    print("UPDATING CHINESE DATABASE WITH JAPANESE CARD LINKS")
    print("="*80)
    
    # Create japanese_card_links table in main database
    print("\n1. Creating japanese_card_links table...")
    main_cursor.execute("""
        CREATE TABLE IF NOT EXISTS japanese_card_links (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            card_id INTEGER NOT NULL,
            japanese_name TEXT NOT NULL,
            japanese_card_code TEXT NOT NULL,
            tournament_usage_decks INTEGER DEFAULT 0,
            tournament_usage_copies INTEGER DEFAULT 0,
            FOREIGN KEY (card_id) REFERENCES cards(id),
            UNIQUE(card_id, japanese_card_code)
        )
    """)
    
    # Create index for faster lookups
    main_cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_japanese_links_card_id 
        ON japanese_card_links(card_id)
    """)
    
    main_cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_japanese_links_name 
        ON japanese_card_links(japanese_name)
    """)
    
    main_conn.commit()
    print("   ✓ Table created with indexes")
    
    # Get all card mappings with usage statistics
    print("\n2. Fetching card mappings from event database...")
    event_cursor.execute("""
        SELECT 
            cm.main_card_id,
            cm.event_card_name,
            cm.event_card_code,
            COUNT(DISTINCT dc.deck_id) as deck_count,
            COUNT(*) as copy_count
        FROM card_mappings cm
        LEFT JOIN deck_cards dc ON dc.card_code = cm.event_card_code 
            AND dc.card_name = cm.event_card_name
        GROUP BY cm.main_card_id, cm.event_card_name, cm.event_card_code
    """)
    
    mappings = event_cursor.fetchall()
    print(f"   ✓ Found {len(mappings)} card mappings")
    
    # Insert mappings into main database
    print("\n3. Inserting Japanese card links...")
    inserted = 0
    updated = 0
    
    for main_card_id, jp_name, jp_code, deck_count, copy_count in mappings:
        # Check if link already exists
        main_cursor.execute("""
            SELECT id, tournament_usage_decks, tournament_usage_copies
            FROM japanese_card_links
            WHERE card_id = ? AND japanese_card_code = ?
        """, (main_card_id, jp_code))
        
        existing = main_cursor.fetchone()
        
        if existing:
            # Update usage statistics
            link_id, old_deck_count, old_copy_count = existing
            if deck_count != old_deck_count or copy_count != old_copy_count:
                main_cursor.execute("""
                    UPDATE japanese_card_links
                    SET tournament_usage_decks = ?,
                        tournament_usage_copies = ?
                    WHERE id = ?
                """, (deck_count, copy_count, link_id))
                updated += 1
        else:
            # Insert new link
            main_cursor.execute("""
                INSERT INTO japanese_card_links (
                    card_id, 
                    japanese_name, 
                    japanese_card_code,
                    tournament_usage_decks,
                    tournament_usage_copies
                ) VALUES (?, ?, ?, ?, ?)
            """, (main_card_id, jp_name, jp_code, deck_count, copy_count))
            inserted += 1
    
    main_conn.commit()
    print(f"   ✓ Inserted {inserted} new links")
    print(f"   ✓ Updated {updated} existing links")
    
    # Show statistics
    print("\n" + "="*80)
    print("DATABASE UPDATE STATISTICS")
    print("="*80)
    
    main_cursor.execute("SELECT COUNT(*) FROM japanese_card_links")
    total_links = main_cursor.fetchone()[0]
    
    main_cursor.execute("SELECT COUNT(DISTINCT card_id) FROM japanese_card_links")
    cards_with_links = main_cursor.fetchone()[0]
    
    print(f"\nTotal Japanese Card Links: {total_links}")
    print(f"Chinese Cards with Links:  {cards_with_links}")
    
    # Show top linked cards
    print("\n" + "="*80)
    print("TOP 10 MOST-USED CHINESE CARDS IN JAPANESE TOURNAMENTS")
    print("="*80)
    
    main_cursor.execute("""
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
        ORDER BY jcl.tournament_usage_decks DESC
        LIMIT 10
    """)
    
    print(f"\n{'Chinese Name':<25} {'Japanese Name':<25} {'Code':<15} {'Decks':<6} {'Copies'}")
    print("-"*80)
    
    for row in main_cursor.fetchall():
        cn_name, jp_name, jp_code, exp, decks, copies = row
        code_display = jp_code if jp_code else "[ENERGY]"
        print(f"{cn_name:<25} {jp_name:<25} {code_display:<15} {decks:<6} {copies}")
    
    # Show example query
    print("\n" + "="*80)
    print("EXAMPLE USAGE QUERIES")
    print("="*80)
    
    print("""
-- Find all Japanese versions of a Chinese card:
SELECT 
    c.name as chinese_name,
    jcl.japanese_name,
    jcl.japanese_card_code,
    jcl.tournament_usage_decks
FROM cards c
JOIN japanese_card_links jcl ON c.id = jcl.card_id
WHERE c.name = '基本火能量'
ORDER BY jcl.tournament_usage_decks DESC;

-- Find Chinese card from Japanese name:
SELECT 
    c.name as chinese_name,
    e.code as expansion,
    c.collector_number,
    jcl.tournament_usage_decks
FROM japanese_card_links jcl
JOIN cards c ON jcl.card_id = c.id
LEFT JOIN expansions e ON c.expansion_id = e.id
WHERE jcl.japanese_name = 'ネストボール'
ORDER BY jcl.tournament_usage_decks DESC;

-- Top tournament cards with both names:
SELECT 
    c.name as chinese_name,
    jcl.japanese_name,
    SUM(jcl.tournament_usage_decks) as total_tournament_decks
FROM japanese_card_links jcl
JOIN cards c ON jcl.card_id = c.id
GROUP BY c.name, jcl.japanese_name
ORDER BY total_tournament_decks DESC
LIMIT 20;
""")
    
    event_conn.close()
    main_conn.close()
    
    print("\n" + "="*80)
    print("✅ DATABASE UPDATE COMPLETE")
    print("="*80)
    print(f"\nJapanese card links have been added to:")
    print(f"  {MAIN_DB}")
    print(f"\nTable: japanese_card_links")
    print(f"  - {total_links} total links")
    print(f"  - {cards_with_links} unique Chinese cards linked")

if __name__ == "__main__":
    update_chinese_database()
