"""
Archive decks containing:
- GX cards
- VMAX cards  
- V cards
- ヒスイのヘビーボール (Hisuian Heavy Ball)
"""

import sqlite3
import json
import os
from datetime import datetime

def archive_special_decks():
    """Archive decks with GX, VMAX, V cards, and Hisuian Heavy Ball"""
    
    conn = sqlite3.connect('ptcg_events.db')
    cursor = conn.cursor()
    
    print("🔍 Searching for special decks...")
    print("  - GX cards")
    print("  - VMAX cards")
    print("  - V cards (excluding VMAX, VSTAR)")
    print("  - ヒスイのヘビーボール (Hisuian Heavy Ball)")
    print()
    
    # Find all decks with these card types
    query = """
    SELECT DISTINCT
        d.deck_id,
        d.deck_url,
        p.player_name,
        e.event_id,
        e.event_date,
        e.event_title,
        er.rank,
        COUNT(DISTINCT dc.card_id) as total_cards,
        GROUP_CONCAT(
            CASE 
                WHEN dc.card_name LIKE '%GX' THEN 'GX: ' || dc.card_name || ' (' || dc.card_code || ')'
                WHEN dc.card_name LIKE '%VMAX' THEN 'VMAX: ' || dc.card_name || ' (' || dc.card_code || ')'
                WHEN dc.card_name LIKE '%V' AND dc.card_name NOT LIKE '%VMAX' AND dc.card_name NOT LIKE '%VSTAR' THEN 'V: ' || dc.card_name || ' (' || dc.card_code || ')'
                WHEN dc.card_name = 'ヒスイのヘビーボール' THEN 'Item: ' || dc.card_name || ' (' || dc.card_code || ')'
            END,
            ' | '
        ) as special_cards
    FROM decks d
    JOIN deck_cards dc ON d.deck_id = dc.deck_id
    JOIN event_results er ON d.deck_id = er.deck_id
    JOIN events e ON er.event_id = e.event_id
    LEFT JOIN players p ON d.player_id = p.player_id
    WHERE (
        dc.card_name LIKE '%GX'
        OR dc.card_name LIKE '%VMAX'
        OR (dc.card_name LIKE '%V' AND dc.card_name NOT LIKE '%VMAX' AND dc.card_name NOT LIKE '%VSTAR')
        OR dc.card_name = 'ヒスイのヘビーボール'
    )
    GROUP BY d.deck_id
    ORDER BY e.event_date DESC, er.rank
    """
    
    cursor.execute(query)
    special_decks = cursor.fetchall()
    
    print(f"📊 Found {len(special_decks)} decks with special cards\n")
    
    # Categorize decks
    gx_decks = []
    vmax_decks = []
    v_decks = []
    hisuian_decks = []
    
    archived_decks = []
    
    for deck_info in special_decks:
        deck_id, deck_url, player_name, event_id, event_date, event_title, rank, total_cards, special_cards = deck_info
        
        # Get full deck list
        cursor.execute("""
            SELECT card_name, card_code, quantity
            FROM deck_cards
            WHERE deck_id = ?
            ORDER BY card_name
        """, (deck_id,))
        
        all_cards = cursor.fetchall()
        
        # Get special cards with Chinese names
        cursor.execute("""
            SELECT 
                dc.card_name as japanese_name,
                cm.main_card_name as chinese_name,
                dc.card_code,
                dc.quantity,
                CASE 
                    WHEN dc.card_name LIKE '%GX' THEN 'GX'
                    WHEN dc.card_name LIKE '%VMAX' THEN 'VMAX'
                    WHEN dc.card_name LIKE '%V' AND dc.card_name NOT LIKE '%VMAX' AND dc.card_name NOT LIKE '%VSTAR' THEN 'V'
                    WHEN dc.card_name = 'ヒスイのヘビーボール' THEN 'Hisuian Heavy Ball'
                END as card_type
            FROM deck_cards dc
            LEFT JOIN card_mappings cm ON dc.card_id = cm.event_card_id
            WHERE dc.deck_id = ?
            AND (
                dc.card_name LIKE '%GX'
                OR dc.card_name LIKE '%VMAX'
                OR (dc.card_name LIKE '%V' AND dc.card_name NOT LIKE '%VMAX' AND dc.card_name NOT LIKE '%VSTAR')
                OR dc.card_name = 'ヒスイのヘビーボール'
            )
            ORDER BY card_type, dc.card_name
        """, (deck_id,))
        
        special_card_details = cursor.fetchall()
        
        deck_data = {
            'deck_id': deck_id,
            'deck_url': deck_url,
            'player_name': player_name,
            'event': {
                'event_id': event_id,
                'date': event_date,
                'title': event_title
            },
            'rank': rank,
            'total_cards': total_cards,
            'special_cards': [],
            'full_decklist': []
        }
        
        # Categorize this deck
        has_gx = False
        has_vmax = False
        has_v = False
        has_hisuian = False
        
        # Add special card details
        for jp_name, cn_name, code, qty, card_type in special_card_details:
            deck_data['special_cards'].append({
                'japanese_name': jp_name,
                'chinese_name': cn_name if cn_name else '未對應',
                'card_code': code,
                'quantity': qty,
                'type': card_type
            })
            
            if card_type == 'GX':
                has_gx = True
            elif card_type == 'VMAX':
                has_vmax = True
            elif card_type == 'V':
                has_v = True
            elif card_type == 'Hisuian Heavy Ball':
                has_hisuian = True
        
        # Add full decklist
        for card_name, card_code, quantity in all_cards:
            deck_data['full_decklist'].append({
                'name': card_name,
                'code': card_code,
                'quantity': quantity
            })
        
        archived_decks.append(deck_data)
        
        # Categorize
        if has_gx:
            gx_decks.append(deck_data)
        if has_vmax:
            vmax_decks.append(deck_data)
        if has_v:
            v_decks.append(deck_data)
        if has_hisuian:
            hisuian_decks.append(deck_data)
    
    # Create archive directory
    archive_dir = 'archive/special_cards'
    os.makedirs(archive_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # Save combined archive
    json_file = f'{archive_dir}/special_decks_{timestamp}.json'
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(archived_decks, f, ensure_ascii=False, indent=2)
    
    print(f"💾 Archived to: {json_file}")
    
    # Generate summary report
    report_file = f'{archive_dir}/special_decks_summary_{timestamp}.txt'
    
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write("=" * 80 + "\n")
        f.write("SPECIAL CARDS DECK ARCHIVE SUMMARY\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("=" * 80 + "\n\n")
        
        f.write(f"Total decks archived: {len(special_decks)}\n\n")
        
        f.write("BY CARD TYPE:\n")
        f.write("-" * 80 + "\n")
        f.write(f"GX cards:                  {len(gx_decks):>6} decks\n")
        f.write(f"VMAX cards:                {len(vmax_decks):>6} decks\n")
        f.write(f"V cards:                   {len(v_decks):>6} decks\n")
        f.write(f"ヒスイのヘビーボール:           {len(hisuian_decks):>6} decks\n")
        f.write("=" * 80 + "\n\n")
        
        # GX cards statistics
        cursor.execute("""
            SELECT 
                dc.card_name,
                dc.card_code,
                COUNT(DISTINCT dc.deck_id) as deck_count,
                SUM(dc.quantity) as total_copies
            FROM deck_cards dc
            WHERE dc.card_name LIKE '%GX'
            GROUP BY dc.card_id
            ORDER BY deck_count DESC, total_copies DESC
        """)
        
        gx_stats = cursor.fetchall()
        
        f.write(f"GX CARDS USAGE ({len(gx_stats)} unique cards):\n")
        f.write("-" * 80 + "\n")
        f.write(f"{'Rank':<6}{'Card Name':<40}{'Code':<20}{'Decks':<8}Cards\n")
        f.write("-" * 80 + "\n")
        
        for idx, (name, code, deck_count, total_copies) in enumerate(gx_stats, 1):
            f.write(f"{idx:<6}{name:<40}{code:<20}{deck_count:<8}{total_copies}\n")
        
        f.write("\n" + "=" * 80 + "\n\n")
        
        # VMAX cards statistics
        cursor.execute("""
            SELECT 
                dc.card_name,
                dc.card_code,
                COUNT(DISTINCT dc.deck_id) as deck_count,
                SUM(dc.quantity) as total_copies
            FROM deck_cards dc
            WHERE dc.card_name LIKE '%VMAX'
            GROUP BY dc.card_id
            ORDER BY deck_count DESC, total_copies DESC
        """)
        
        vmax_stats = cursor.fetchall()
        
        f.write(f"VMAX CARDS USAGE ({len(vmax_stats)} unique cards):\n")
        f.write("-" * 80 + "\n")
        f.write(f"{'Rank':<6}{'Card Name':<40}{'Code':<20}{'Decks':<8}Cards\n")
        f.write("-" * 80 + "\n")
        
        for idx, (name, code, deck_count, total_copies) in enumerate(vmax_stats, 1):
            f.write(f"{idx:<6}{name:<40}{code:<20}{deck_count:<8}{total_copies}\n")
        
        f.write("\n" + "=" * 80 + "\n\n")
        
        # V cards statistics (excluding VMAX, VSTAR)
        cursor.execute("""
            SELECT 
                dc.card_name,
                dc.card_code,
                COUNT(DISTINCT dc.deck_id) as deck_count,
                SUM(dc.quantity) as total_copies
            FROM deck_cards dc
            WHERE dc.card_name LIKE '%V'
            AND dc.card_name NOT LIKE '%VMAX'
            AND dc.card_name NOT LIKE '%VSTAR'
            GROUP BY dc.card_id
            ORDER BY deck_count DESC, total_copies DESC
            LIMIT 50
        """)
        
        v_stats = cursor.fetchall()
        
        f.write(f"V CARDS USAGE (Top 50 of many):\n")
        f.write("-" * 80 + "\n")
        f.write(f"{'Rank':<6}{'Card Name':<40}{'Code':<20}{'Decks':<8}Cards\n")
        f.write("-" * 80 + "\n")
        
        for idx, (name, code, deck_count, total_copies) in enumerate(v_stats, 1):
            f.write(f"{idx:<6}{name:<40}{code:<20}{deck_count:<8}{total_copies}\n")
        
        f.write("\n" + "=" * 80 + "\n\n")
        
        # Hisuian Heavy Ball statistics
        cursor.execute("""
            SELECT 
                dc.card_name,
                dc.card_code,
                COUNT(DISTINCT dc.deck_id) as deck_count,
                SUM(dc.quantity) as total_copies
            FROM deck_cards dc
            WHERE dc.card_name = 'ヒスイのヘビーボール'
            GROUP BY dc.card_id
            ORDER BY deck_count DESC, total_copies DESC
        """)
        
        hisuian_stats = cursor.fetchall()
        
        f.write(f"ヒスイのヘビーボール USAGE ({len(hisuian_stats)} versions):\n")
        f.write("-" * 80 + "\n")
        f.write(f"{'Rank':<6}{'Card Name':<40}{'Code':<20}{'Decks':<8}Cards\n")
        f.write("-" * 80 + "\n")
        
        for idx, (name, code, deck_count, total_copies) in enumerate(hisuian_stats, 1):
            f.write(f"{idx:<6}{name:<40}{code:<20}{deck_count:<8}{total_copies}\n")
        
        f.write("\n" + "=" * 80 + "\n\n")
        
        f.write("SAMPLE DECKS:\n")
        f.write("-" * 80 + "\n")
        
        for deck in archived_decks[:10]:
            f.write(f"\nDeck ID: {deck['deck_id']}\n")
            f.write(f"Player: {deck['player_name']}\n")
            f.write(f"Event: {deck['event']['title']}\n")
            f.write(f"Date: {deck['event']['date']}\n")
            f.write(f"Rank: {deck['rank']}\n")
            f.write(f"Total Cards: {deck['total_cards']}\n")
            f.write(f"URL: {deck['deck_url']}\n")
            f.write(f"\nSpecial Cards in this deck:\n")
            
            for card in deck['special_cards']:
                f.write(f"  [{card['type']}] {card['japanese_name']} ({card['card_code']}) x{card['quantity']}\n")
                if card['chinese_name'] != '未對應':
                    f.write(f"    Chinese: {card['chinese_name']}\n")
            
            f.write("-" * 80 + "\n")
    
    print(f"📄 Summary report: {report_file}\n")
    
    # Print console summary
    print("=" * 80)
    print("SPECIAL CARDS STATISTICS")
    print("=" * 80)
    
    print(f"\n📊 DECK COUNTS BY CARD TYPE:")
    print(f"  GX cards:                  {len(gx_decks):>6} decks")
    print(f"  VMAX cards:                {len(vmax_decks):>6} decks")
    print(f"  V cards:                   {len(v_decks):>6} decks")
    print(f"  ヒスイのヘビーボール:           {len(hisuian_decks):>6} decks")
    
    print(f"\n🎴 UNIQUE CARD COUNTS:")
    print(f"  GX cards:                  {len(gx_stats):>6} unique")
    print(f"  VMAX cards:                {len(vmax_stats):>6} unique")
    print(f"  V cards:                   {len(v_stats):>6}+ unique")
    print(f"  ヒスイのヘビーボール:           {len(hisuian_stats):>6} versions")
    
    print("\n" + "=" * 80)
    print("TOP 5 MOST USED CARDS BY TYPE")
    print("=" * 80)
    
    print("\n⭐ GX Cards:")
    for idx, (name, code, deck_count, total_copies) in enumerate(gx_stats[:5], 1):
        print(f"  {idx}. {name:<35} {code:<20} ({deck_count} decks, {total_copies} copies)")
    
    print("\n⭐ VMAX Cards:")
    for idx, (name, code, deck_count, total_copies) in enumerate(vmax_stats[:5], 1):
        print(f"  {idx}. {name:<35} {code:<20} ({deck_count} decks, {total_copies} copies)")
    
    print("\n⭐ V Cards:")
    for idx, (name, code, deck_count, total_copies) in enumerate(v_stats[:5], 1):
        print(f"  {idx}. {name:<35} {code:<20} ({deck_count} decks, {total_copies} copies)")
    
    if hisuian_stats:
        print("\n⭐ ヒスイのヘビーボール:")
        for idx, (name, code, deck_count, total_copies) in enumerate(hisuian_stats, 1):
            print(f"  {idx}. {name:<35} {code:<20} ({deck_count} decks, {total_copies} copies)")
    
    conn.close()
    
    return {
        'total_decks': len(special_decks),
        'gx_decks': len(gx_decks),
        'vmax_decks': len(vmax_decks),
        'v_decks': len(v_decks),
        'hisuian_decks': len(hisuian_decks),
        'gx_unique': len(gx_stats),
        'vmax_unique': len(vmax_stats),
        'v_unique': len(v_stats),
        'hisuian_versions': len(hisuian_stats),
        'json_file': json_file,
        'report_file': report_file
    }

if __name__ == '__main__':
    print("🎴 Special Cards Deck Archive Tool")
    print("=" * 80)
    print("Archiving decks with:")
    print("  - GX cards (Sun & Moon era)")
    print("  - VMAX cards (Sword & Shield era)")
    print("  - V cards (Sword & Shield era)")
    print("  - ヒスイのヘビーボール (Hisuian Heavy Ball)")
    print("=" * 80)
    print()
    
    result = archive_special_decks()
    
    print(f"\n✅ Archive complete!")
    print(f"   - {result['total_decks']} decks archived")
    print(f"   - {result['gx_unique']} unique GX cards")
    print(f"   - {result['vmax_unique']} unique VMAX cards")
    print(f"   - {result['v_unique']}+ unique V cards")
    print(f"   - Files saved to archive/special_cards/")
