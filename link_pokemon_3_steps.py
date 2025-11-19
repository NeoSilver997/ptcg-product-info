"""
3-Step Card Linking Strategy:
1. Pokemon: Find by code (expansion + collector number) in Chinese database
2. If code not found: Find by same name in same expansion
3. Trainers: Already linked via link_trainers_by_name.py (504 mappings)

This script implements steps 1-2 for Pokemon cards.
"""

import sqlite3
import re
from datetime import datetime

def parse_card_code(card_code):
    """Parse card code into expansion and collector number"""
    if not card_code or card_code == '無代碼' or card_code == 'ACE SPEC':
        return None, None
    
    # Pattern: "SV8a 120/187" or "M1 001/165"
    match = re.match(r'([A-Z0-9\-]+)\s+(\d+)/(\d+)', card_code)
    if match:
        expansion_code = match.group(1)
        collector_number = match.group(2)
        return expansion_code, collector_number
    
    return None, None

def get_expansion_map(main_conn):
    """Build mapping of expansion codes to IDs"""
    cursor = main_conn.cursor()
    cursor.execute("SELECT id, code, name FROM expansions")
    
    expansion_map = {}
    for exp_id, code, name in cursor.fetchall():
        if code:
            expansion_map[code] = {'id': exp_id, 'name': name}
    
    return expansion_map

def link_pokemon_3_steps():
    """
    Link Pokemon cards using 3-step strategy:
    1. Find by code in Chinese DB
    2. Find by name in same expansion
    3. Trainers already linked separately
    """
    
    print("\n" + "=" * 80)
    print("🎴 3-STEP POKEMON CARD LINKING")
    print("=" * 80)
    print("\nStrategy:")
    print("  Step 1: Find by code (expansion + collector number)")
    print("  Step 2: Find by same name in same expansion")
    print("  Step 3: Trainers already linked (skip)")
    print("=" * 80)
    
    # Connect to databases
    event_conn = sqlite3.connect('ptcg_events.db', timeout=30.0)
    event_conn.execute('PRAGMA journal_mode=WAL')  # Enable WAL mode for better concurrency
    main_conn = sqlite3.connect(r'c:\AI_Server\Coding\PokemonDBByjules\PTCG_CardDB_Tc\pokemon_cards.db')
    
    event_cursor = event_conn.cursor()
    main_cursor = main_conn.cursor()
    
    # Get expansion mapping
    print("\n📚 Loading expansion mapping...")
    expansion_map = get_expansion_map(main_conn)
    print(f"   Found {len(expansion_map)} expansions")
    
    # Get unmapped cards (excluding energy, ACE SPEC, trainers already mapped)
    print("\n🔍 Finding unmapped Pokemon cards...")
    event_cursor.execute("""
        SELECT DISTINCT
            dc.card_id,
            dc.card_name,
            dc.card_code,
            COUNT(DISTINCT dc.deck_id) as deck_count,
            SUM(dc.quantity) as total_copies
        FROM deck_cards dc
        LEFT JOIN card_mappings cm ON dc.card_id = cm.event_card_id
        WHERE cm.main_card_id IS NULL
        AND dc.card_code != 'ACE SPEC'
        AND dc.card_code != '無代碼'
        AND dc.card_code != ''
        AND dc.card_name NOT LIKE '%エネルギー'
        GROUP BY dc.card_id
        HAVING COUNT(DISTINCT dc.deck_id) > 0
        ORDER BY deck_count DESC, total_copies DESC
    """)
    
    unmapped = event_cursor.fetchall()
    print(f"   Found {len(unmapped)} unmapped cards to process")
    
    # Statistics
    stats = {
        'step1_code_match': 0,
        'step2_name_expansion': 0,
        'failed': 0
    }
    
    new_mappings = []
    failed_cards = []
    
    print("\n🔄 Processing cards...\n")
    
    for idx, (card_id, card_name, card_code, deck_count, total_copies) in enumerate(unmapped):
        if idx % 100 == 0 and idx > 0:
            print(f"   Processed {idx}/{len(unmapped)} cards...")
        
        # Parse card code
        expansion_code, collector_number = parse_card_code(card_code)
        
        if not expansion_code or not collector_number:
            stats['failed'] += 1
            failed_cards.append((card_name, card_code, deck_count, 'Invalid code'))
            continue
        
        # STEP 1: Find by code (expansion + collector number)
        if expansion_code in expansion_map:
            expansion_id = expansion_map[expansion_code]['id']
            
            main_cursor.execute("""
                SELECT c.id, c.name, c.collector_number
                FROM cards c
                WHERE c.expansion_id = ? AND c.collector_number = ?
                LIMIT 1
            """, (expansion_id, collector_number))
            
            result = main_cursor.fetchone()
            
            if result:
                chinese_id, chinese_name, coll_num = result
                new_mappings.append({
                    'event_card_id': card_id,
                    'main_card_id': chinese_id,
                    'japanese_name': card_name,
                    'chinese_name': chinese_name,
                    'card_code': card_code,
                    'deck_count': deck_count,
                    'method': 'step1_code_match',
                    'expansion': expansion_code
                })
                stats['step1_code_match'] += 1
                if deck_count >= 10:  # Only print high-usage cards
                    print(f"✅ Step 1: [{expansion_code} {collector_number}] {card_name} → {chinese_name} ({deck_count} decks)")
                continue
        
        # STEP 2: Find by same name in same expansion
        if expansion_code in expansion_map:
            expansion_id = expansion_map[expansion_code]['id']
            
            # Try exact name match
            main_cursor.execute("""
                SELECT c.id, c.name, c.collector_number
                FROM cards c
                WHERE c.expansion_id = ? AND c.name = ?
                LIMIT 1
            """, (expansion_id, card_name))
            
            result = main_cursor.fetchone()
            
            if result:
                chinese_id, chinese_name, coll_num = result
                new_mappings.append({
                    'event_card_id': card_id,
                    'main_card_id': chinese_id,
                    'japanese_name': card_name,
                    'chinese_name': chinese_name,
                    'card_code': card_code,
                    'deck_count': deck_count,
                    'method': 'step2_name_expansion',
                    'expansion': expansion_code
                })
                stats['step2_name_expansion'] += 1
                if deck_count >= 10:
                    print(f"🔄 Step 2: [{expansion_code}] {card_name} → {chinese_name} ({deck_count} decks)")
                continue
        
        # No match found
        stats['failed'] += 1
        failed_cards.append((card_name, card_code, deck_count, 'Not found'))
    
    print(f"\n   Processed all {len(unmapped)} cards")
    
    # Save new mappings
    if new_mappings:
        print(f"\n💾 Saving {len(new_mappings)} new mappings...")
        
        saved_count = 0
        skipped_count = 0
        
        for mapping in new_mappings:
            # Check if already exists
            event_cursor.execute("""
                SELECT COUNT(*) FROM card_mappings 
                WHERE event_card_id = ?
            """, (mapping['event_card_id'],))
            
            if event_cursor.fetchone()[0] > 0:
                skipped_count += 1
                continue
            
            # Insert new mapping
            event_cursor.execute("""
                INSERT INTO card_mappings 
                (event_card_id, main_card_id, event_card_name, main_card_name, match_type, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                mapping['event_card_id'],
                mapping['main_card_id'],
                mapping['japanese_name'],
                mapping['chinese_name'],
                mapping['method'],
                datetime.now().isoformat()
            ))
            saved_count += 1
        
        # Commit with retry logic
        max_retries = 3
        for attempt in range(max_retries):
            try:
                event_conn.commit()
                break
            except sqlite3.OperationalError as e:
                if 'locked' in str(e) and attempt < max_retries - 1:
                    print(f"   Database locked, retrying... (attempt {attempt + 1}/{max_retries})")
                    import time
                    time.sleep(2)
                else:
                    raise
        
        print(f"   ✅ Saved {saved_count} new mappings")
        if skipped_count > 0:
            print(f"   ⚠️  Skipped {skipped_count} (already existed)")
    
    # Print statistics
    print("\n" + "=" * 80)
    print("📊 LINKING RESULTS")
    print("=" * 80)
    print(f"Total processed:              {len(unmapped):>6,}")
    print(f"\nStep 1 (Code match):          {stats['step1_code_match']:>6,}")
    print(f"Step 2 (Name in expansion):   {stats['step2_name_expansion']:>6,}")
    print(f"Failed:                       {stats['failed']:>6,}")
    print("-" * 80)
    print(f"Total new mappings:           {len(new_mappings):>6,}")
    print("=" * 80)
    
    # Calculate coverage
    print("\n📈 COVERAGE UPDATE")
    print("=" * 80)
    
    event_cursor.execute("SELECT COUNT(DISTINCT card_id) FROM deck_cards")
    total_unique = event_cursor.fetchone()[0]
    
    event_cursor.execute("""
        SELECT COUNT(DISTINCT dc.card_id)
        FROM deck_cards dc
        JOIN card_mappings cm ON dc.card_id = cm.event_card_id
    """)
    mapped = event_cursor.fetchone()[0]
    
    coverage = (mapped / total_unique * 100) if total_unique > 0 else 0
    
    print(f"Total unique cards:           {total_unique:>6,}")
    print(f"Mapped cards:                 {mapped:>6,}")
    print(f"Unmapped cards:               {total_unique - mapped:>6,}")
    print(f"Coverage:                     {coverage:>6.2f}%")
    print("=" * 80)
    
    # Show top newly mapped cards
    if new_mappings:
        print("\n🎯 TOP 15 NEWLY MAPPED CARDS (by deck usage):")
        print("-" * 80)
        
        sorted_mappings = sorted(new_mappings, key=lambda x: x['deck_count'], reverse=True)
        
        for idx, m in enumerate(sorted_mappings[:15], 1):
            method_symbol = "✅" if m['method'] == 'step1_code_match' else "🔄"
            print(f"{idx:>2}. {method_symbol} {m['japanese_name']:<30} → {m['chinese_name']}")
            print(f"     Code: {m['card_code']:<20} Decks: {m['deck_count']:<6} ({m['expansion']})")
    
    # Show top failed cards
    if failed_cards:
        print("\n❌ TOP 10 FAILED CARDS (by deck usage):")
        print("-" * 80)
        
        sorted_failed = sorted(failed_cards, key=lambda x: x[2], reverse=True)
        
        for idx, (name, code, deck_count, reason) in enumerate(sorted_failed[:10], 1):
            print(f"{idx:>2}. {name:<35} {code:<20} ({deck_count} decks)")
            print(f"     Reason: {reason}")
    
    event_conn.close()
    main_conn.close()
    
    return stats, len(new_mappings)

if __name__ == '__main__':
    print("\n🎴 Pokemon TCG Card Linking - 3-Step Strategy")
    
    stats, new_count = link_pokemon_3_steps()
    
    print(f"\n✅ Linking complete!")
    print(f"   New mappings added: {new_count}")
    print(f"   Step 1 success: {stats['step1_code_match']}")
    print(f"   Step 2 success: {stats['step2_name_expansion']}")
    print(f"\nNote: Trainer cards already linked separately (504 mappings)")
