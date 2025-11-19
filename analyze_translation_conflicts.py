"""
Translation Conflict Analysis
============================
Analyze Japanese cards mapped to multiple different Chinese names.
Identifies potential mapping errors and legitimate card variants.
"""

import sqlite3

EVENT_DB = "ptcg_events.db"
MAIN_DB = r"c:\AI_Server\Coding\PokemonDBByjules\PTCG_CardDB_Tc\pokemon_cards.db"

def analyze_translation_conflicts():
    conn_event = sqlite3.connect(EVENT_DB)
    conn_main = sqlite3.connect(MAIN_DB)
    
    cursor_event = conn_event.cursor()
    cursor_main = conn_main.cursor()
    
    print("="*100)
    print("TRANSLATION CONFLICT ANALYSIS - SAME JAPANESE NAME, DIFFERENT CHINESE NAMES")
    print("="*100)
    
    # Find Japanese names that map to multiple different Chinese names
    cursor_event.execute("""
        SELECT 
            cm.event_card_name as japanese_name,
            COUNT(DISTINCT cm.main_card_name) as chinese_variants,
            SUM(CASE WHEN dc.card_id IS NOT NULL THEN 1 ELSE 0 END) as total_usage
        FROM card_mappings cm
        LEFT JOIN deck_cards dc ON cm.event_card_code = dc.card_code 
            AND cm.event_card_name = dc.card_name
        WHERE cm.main_card_name IS NOT NULL
        GROUP BY cm.event_card_name
        HAVING COUNT(DISTINCT cm.main_card_name) > 1
        ORDER BY total_usage DESC, chinese_variants DESC
    """)
    
    conflicts = cursor_event.fetchall()
    
    print(f"\n📊 Found {len(conflicts)} Japanese cards with multiple Chinese translations")
    print(f"{'='*100}\n")
    
    mapping_errors = []
    legitimate_variants = []
    
    for i, (jp_name, variant_count, total_usage) in enumerate(conflicts, 1):
        print(f"\n{'='*100}")
        print(f"{i}. 【{jp_name}】 - {variant_count} Chinese variants, {total_usage} total instances")
        print("="*100)
        
        # Get detailed breakdown
        cursor_event.execute("""
            SELECT DISTINCT 
                cm.main_card_name,
                cm.main_card_id,
                cm.event_card_code,
                COUNT(DISTINCT dc.deck_id) as deck_count,
                SUM(dc.quantity) as total_quantity,
                cm.match_type,
                cm.match_confidence
            FROM card_mappings cm
            LEFT JOIN deck_cards dc ON cm.event_card_code = dc.card_code 
                AND cm.event_card_name = dc.card_name
            WHERE cm.event_card_name = ?
            GROUP BY cm.main_card_name, cm.main_card_id, cm.event_card_code
            ORDER BY deck_count DESC
        """, (jp_name,))
        
        variants = cursor_event.fetchall()
        
        # Analyze each variant
        variant_details = []
        for cn_name, card_id, code, deck_count, total_qty, match_type, confidence in variants:
            code_display = code if code else "[NO CODE]"
            
            # Get card details from main database
            if card_id:
                cursor_main.execute("""
                    SELECT 
                        c.card_type, 
                        c.hp, 
                        c.rarity, 
                        e.code as expansion_code,
                        e.name as expansion_name,
                        c.collector_number
                    FROM cards c
                    LEFT JOIN expansions e ON c.expansion_id = e.id
                    WHERE c.id = ?
                """, (card_id,))
                
                card_info = cursor_main.fetchone()
                if card_info:
                    card_type, hp, rarity, exp_code, exp_name, collector = card_info
                    hp_str = f"HP{hp}" if hp else "N/A"
                    
                    variant_details.append({
                        'chinese_name': cn_name,
                        'card_type': card_type,
                        'hp': hp_str,
                        'rarity': rarity,
                        'expansion': exp_code,
                        'expansion_name': exp_name,
                        'collector': collector,
                        'event_code': code_display,
                        'deck_count': deck_count,
                        'total_qty': total_qty,
                        'match_type': match_type,
                        'confidence': confidence
                    })
        
        # Display variant details
        for vd in variant_details:
            print(f"\n  ✓ {vd['chinese_name']}")
            print(f"     Card Type: {vd['card_type']}")
            print(f"     Stats: {vd['hp']}, Rarity: {vd['rarity']}")
            print(f"     Expansion: [{vd['expansion']}] {vd['expansion_name']}")
            print(f"     Collector #: {vd['collector']}")
            print(f"     Event Code: {vd['event_code']}")
            print(f"     Usage: {vd['deck_count']} decks, {vd['total_qty']} cards")
            print(f"     Match: {vd['match_type']} (confidence: {vd['confidence']})")
        
        # Determine if this is an error or legitimate variant
        if len(variant_details) >= 2:
            types = set(vd['card_type'] for vd in variant_details)
            
            if len(types) > 1:
                print(f"\n  ⚠️  MAPPING ERROR: Different card types detected!")
                print(f"      Card types: {', '.join(types)}")
                mapping_errors.append({
                    'japanese': jp_name,
                    'variants': variant_details,
                    'reason': f"Different card types: {', '.join(types)}"
                })
            else:
                # Check if names are similar (legitimate variants like different professor versions)
                names = [vd['chinese_name'] for vd in variant_details]
                if all('博士的研究' in name for name in names):
                    print(f"\n  ✅ LEGITIMATE VARIANT: Different professor versions")
                    legitimate_variants.append({
                        'japanese': jp_name,
                        'variants': variant_details,
                        'reason': "Different professor versions (same card, different artwork)"
                    })
                else:
                    print(f"\n  ❓ NEEDS REVIEW: Same type but different Chinese names")
                    mapping_errors.append({
                        'japanese': jp_name,
                        'variants': variant_details,
                        'reason': "Same card type but different translations"
                    })
    
    # Summary
    print("\n" + "="*100)
    print("SUMMARY")
    print("="*100)
    
    print(f"\n📊 Total Conflicts: {len(conflicts)}")
    print(f"   ✅ Legitimate Variants: {len(legitimate_variants)}")
    print(f"   ⚠️  Mapping Errors: {len(mapping_errors)}")
    
    if mapping_errors:
        print(f"\n⚠️  MAPPING ERRORS DETECTED:")
        for i, error in enumerate(mapping_errors, 1):
            print(f"\n{i}. {error['japanese']}")
            print(f"   Reason: {error['reason']}")
            print(f"   Affected variants:")
            for vd in error['variants']:
                print(f"     • {vd['chinese_name']} [{vd['card_type']}] - {vd['deck_count']} decks")
    
    if legitimate_variants:
        print(f"\n✅ LEGITIMATE VARIANTS:")
        for i, variant in enumerate(legitimate_variants, 1):
            print(f"\n{i}. {variant['japanese']}")
            print(f"   Reason: {variant['reason']}")
            for vd in variant['variants']:
                print(f"     • {vd['chinese_name']} - {vd['deck_count']} decks")
    
    conn_event.close()
    conn_main.close()

if __name__ == "__main__":
    analyze_translation_conflicts()
