"""
Quick Card Lookup Utility
=========================
Simple command-line tool for looking up card mappings.

Usage:
    python lookup_card.py "カード名"          # Search by Japanese name
    python lookup_card.py "卡片名稱" --chinese  # Search by Chinese name
    python lookup_card.py "SV8a 120/187"      # Search by card code
"""

import sqlite3
import sys

EVENT_DB = "ptcg_events.db"
MAIN_DB = r"c:\AI_Server\Coding\PokemonDBByjules\PTCG_CardDB_Tc\pokemon_cards.db"

def lookup_by_japanese_name(name):
    """Look up card by Japanese name"""
    event_conn = sqlite3.connect(EVENT_DB)
    main_conn = sqlite3.connect(MAIN_DB)
    
    cursor = event_conn.cursor()
    cursor.execute("""
        SELECT DISTINCT 
            dc.card_name,
            dc.card_code,
            cm.main_card_id,
            COUNT(DISTINCT dc.deck_id) as deck_count
        FROM deck_cards dc
        LEFT JOIN card_mappings cm ON dc.card_code = cm.event_card_code
        WHERE dc.card_name LIKE ?
        GROUP BY dc.card_name, dc.card_code, cm.main_card_id
        ORDER BY deck_count DESC
    """, (f'%{name}%',))
    
    results = cursor.fetchall()
    
    if not results:
        print(f"❌ No cards found matching '{name}'")
        event_conn.close()
        main_conn.close()
        return
    
    print(f"\n{'='*80}")
    print(f"SEARCH RESULTS FOR: {name}")
    print("="*80)
    
    for jp_name, code, main_id, deck_count in results:
        code_display = code if code else "[BASIC ENERGY]"
        status = "✅" if main_id else "❌"
        
        print(f"\n{status} {jp_name}")
        print(f"   Card Code: {code_display}")
        print(f"   Usage: {deck_count} decks")
        
        if main_id:
            # Get Chinese name
            main_cursor = main_conn.cursor()
            main_cursor.execute("""
                SELECT c.name, e.code, c.collector_number
                FROM cards c
                LEFT JOIN expansions e ON c.expansion_id = e.id
                WHERE c.id = ?
            """, (main_id,))
            
            result = main_cursor.fetchone()
            if result:
                cn_name, exp_code, coll_num = result
                print(f"   → Chinese: {cn_name}")
                print(f"   → Database: {exp_code} {coll_num}")
        else:
            print(f"   ⚠️  Not mapped to Chinese database")
    
    event_conn.close()
    main_conn.close()

def lookup_by_chinese_name(name):
    """Look up card by Chinese name"""
    main_conn = sqlite3.connect(MAIN_DB)
    event_conn = sqlite3.connect(EVENT_DB)
    
    main_cursor = main_conn.cursor()
    main_cursor.execute("""
        SELECT c.id, c.name, e.code, c.collector_number
        FROM cards c
        LEFT JOIN expansions e ON c.expansion_id = e.id
        WHERE c.name LIKE ?
        LIMIT 10
    """, (f'%{name}%',))
    
    results = main_cursor.fetchall()
    
    if not results:
        print(f"❌ No cards found matching '{name}'")
        main_conn.close()
        event_conn.close()
        return
    
    print(f"\n{'='*80}")
    print(f"SEARCH RESULTS FOR: {name}")
    print("="*80)
    
    for main_id, cn_name, exp_code, coll_num in results:
        print(f"\n✅ {cn_name}")
        print(f"   Database: {exp_code} {coll_num}")
        
        # Check if mapped to event cards
        event_cursor = event_conn.cursor()
        event_cursor.execute("""
            SELECT event_card_code, event_card_name
            FROM card_mappings
            WHERE main_card_id = ?
        """, (main_id,))
        
        mapping = event_cursor.fetchone()
        if mapping:
            event_code, jp_name = mapping
            code_display = event_code if event_code else "[BASIC ENERGY]"
            print(f"   ← Japanese: {jp_name}")
            print(f"   ← Event Code: {code_display}")
            
            # Get usage statistics
            event_cursor.execute("""
                SELECT COUNT(DISTINCT deck_id)
                FROM deck_cards
                WHERE card_code = ? AND card_name = ?
            """, (event_code, jp_name))
            
            deck_count = event_cursor.fetchone()[0]
            print(f"   Usage: {deck_count} tournament decks")
        else:
            print(f"   ⚠️  Not used in tournament events")
    
    main_conn.close()
    event_conn.close()

def lookup_by_code(code):
    """Look up card by card code"""
    event_conn = sqlite3.connect(EVENT_DB)
    main_conn = sqlite3.connect(MAIN_DB)
    
    cursor = event_conn.cursor()
    cursor.execute("""
        SELECT 
            dc.card_name,
            dc.card_code,
            cm.main_card_id,
            COUNT(DISTINCT dc.deck_id) as deck_count
        FROM deck_cards dc
        LEFT JOIN card_mappings cm ON dc.card_code = cm.event_card_code
        WHERE dc.card_code = ?
        GROUP BY dc.card_name, dc.card_code, cm.main_card_id
    """, (code,))
    
    result = cursor.fetchone()
    
    if not result:
        print(f"❌ No card found with code '{code}'")
        event_conn.close()
        main_conn.close()
        return
    
    jp_name, card_code, main_id, deck_count = result
    
    print(f"\n{'='*80}")
    print(f"CARD DETAILS: {code}")
    print("="*80)
    
    print(f"\n✅ Japanese: {jp_name}")
    print(f"   Card Code: {card_code}")
    print(f"   Usage: {deck_count} tournament decks")
    
    if main_id:
        main_cursor = main_conn.cursor()
        main_cursor.execute("""
            SELECT c.name, e.code, c.collector_number, c.card_type
            FROM cards c
            LEFT JOIN expansions e ON c.expansion_id = e.id
            WHERE c.id = ?
        """, (main_id,))
        
        result = main_cursor.fetchone()
        if result:
            cn_name, exp_code, coll_num, card_type = result
            print(f"\n   → Chinese: {cn_name}")
            print(f"   → Type: {card_type}")
            print(f"   → Database: {exp_code} {coll_num}")
    else:
        print(f"\n   ⚠️  Not mapped to Chinese database")
    
    event_conn.close()
    main_conn.close()

def show_statistics():
    """Show overall mapping statistics"""
    event_conn = sqlite3.connect(EVENT_DB)
    cursor = event_conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM card_mappings")
    total_mappings = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(DISTINCT card_code) FROM deck_cards")
    total_cards = cursor.fetchone()[0]
    
    coverage = (total_mappings / total_cards * 100) if total_cards > 0 else 0
    
    print(f"\n{'='*80}")
    print("CARD MAPPING STATISTICS")
    print("="*80)
    print(f"\nTotal Mapped Cards: {total_mappings}")
    print(f"Total Unique Cards: {total_cards}")
    print(f"Coverage: {coverage:.2f}%")
    
    # Top mapped cards
    cursor.execute("""
        SELECT dc.card_name, dc.card_code, COUNT(DISTINCT dc.deck_id) as deck_count
        FROM deck_cards dc
        JOIN card_mappings cm ON dc.card_code = cm.event_card_code
        GROUP BY dc.card_name, dc.card_code
        ORDER BY deck_count DESC
        LIMIT 10
    """)
    
    print(f"\n{'='*80}")
    print("TOP 10 MAPPED CARDS")
    print("="*80)
    
    for i, (name, code, count) in enumerate(cursor.fetchall(), 1):
        code_display = code if code else "[ENERGY]"
        print(f"{i:2d}. {name:30s} {code_display:20s} ({count:4d} decks)")
    
    event_conn.close()

def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python lookup_card.py <card_name>           # Search Japanese")
        print("  python lookup_card.py <card_name> --chinese # Search Chinese")
        print("  python lookup_card.py <card_code>           # Search by code")
        print("  python lookup_card.py --stats               # Show statistics")
        return
    
    if sys.argv[1] == '--stats':
        show_statistics()
        return
    
    search_term = sys.argv[1]
    
    # Check if searching by Chinese
    if len(sys.argv) > 2 and sys.argv[2] == '--chinese':
        lookup_by_chinese_name(search_term)
    # Check if it's a card code (contains space and slash)
    elif ' ' in search_term and '/' in search_term:
        lookup_by_code(search_term)
    else:
        lookup_by_japanese_name(search_term)

if __name__ == "__main__":
    main()
