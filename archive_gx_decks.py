"""
Archive all decks containing GX cards from the event database.
This script identifies decks with GX cards and exports them for reference.
"""

import sqlite3
import json
import os
from datetime import datetime

def archive_gx_decks():
    """Find and archive all decks containing GX cards"""
    
    conn = sqlite3.connect('ptcg_events.db')
    cursor = conn.cursor()
    
    # Find all decks with GX cards
    print("🔍 Searching for decks with GX cards...")
    query = """
    SELECT DISTINCT
        d.deck_id,
        d.deck_url,
        p.player_name,
        e.event_id,
        e.event_date,
        e.event_title,
        er.rank,
        COUNT(dc.card_id) as total_cards,
        GROUP_CONCAT(
            CASE WHEN dc.card_name LIKE '%GX' THEN dc.card_name || ' (' || dc.card_code || ')' END,
            ', '
        ) as gx_cards
    FROM decks d
    JOIN deck_cards dc ON d.deck_id = dc.deck_id
    JOIN event_results er ON d.deck_id = er.deck_id
    JOIN events e ON er.event_id = e.event_id
    LEFT JOIN players p ON d.player_id = p.player_id
    WHERE dc.card_name LIKE '%GX'
    GROUP BY d.deck_id
    ORDER BY e.event_date DESC, er.rank
    """
    
    cursor.execute(query)
    gx_decks = cursor.fetchall()
    
    print(f"\n📊 Found {len(gx_decks)} decks containing GX cards\n")
    
    # Get detailed information for each deck
    archived_decks = []
    
    for deck_info in gx_decks:
        deck_id, deck_url, player_name, event_id, event_date, event_title, rank, total_cards, gx_cards = deck_info
        
        # Get full deck list
        cursor.execute("""
            SELECT card_name, card_code, quantity
            FROM deck_cards
            WHERE deck_id = ?
            ORDER BY card_name
        """, (deck_id,))
        
        all_cards = cursor.fetchall()
        
        # Get Chinese names for mapped cards
        cursor.execute("""
            SELECT 
                dc.card_name as japanese_name,
                cm.main_card_name as chinese_name,
                dc.card_code,
                dc.quantity
            FROM deck_cards dc
            LEFT JOIN card_mappings cm ON dc.card_id = cm.event_card_id
            WHERE dc.deck_id = ? AND dc.card_name LIKE '%GX'
            ORDER BY dc.card_name
        """, (deck_id,))
        
        gx_card_details = cursor.fetchall()
        
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
            'gx_cards': [],
            'full_decklist': []
        }
        
        # Add GX card details
        for jp_name, cn_name, code, qty in gx_card_details:
            deck_data['gx_cards'].append({
                'japanese_name': jp_name,
                'chinese_name': cn_name if cn_name else '未對應',
                'card_code': code,
                'quantity': qty
            })
        
        # Add full decklist
        for card_name, card_code, quantity in all_cards:
            deck_data['full_decklist'].append({
                'name': card_name,
                'code': card_code,
                'quantity': quantity
            })
        
        archived_decks.append(deck_data)
    
    # Create archive directory
    archive_dir = 'archive/gx_decks'
    os.makedirs(archive_dir, exist_ok=True)
    
    # Save to JSON file
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    json_file = f'{archive_dir}/gx_decks_{timestamp}.json'
    
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(archived_decks, f, ensure_ascii=False, indent=2)
    
    print(f"💾 Archived to: {json_file}")
    
    # Generate summary report
    report_file = f'{archive_dir}/gx_decks_summary_{timestamp}.txt'
    
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write("=" * 80 + "\n")
        f.write("GX DECKS ARCHIVE SUMMARY\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("=" * 80 + "\n\n")
        
        f.write(f"Total decks with GX cards: {len(gx_decks)}\n\n")
        
        # Count GX cards usage
        cursor.execute("""
            SELECT 
                dc.card_name,
                dc.card_code,
                COUNT(DISTINCT dc.deck_id) as deck_count,
                SUM(dc.quantity) as total_copies,
                cm.main_card_name as chinese_name
            FROM deck_cards dc
            LEFT JOIN card_mappings cm ON dc.card_id = cm.event_card_id
            WHERE dc.card_name LIKE '%GX'
            GROUP BY dc.card_id
            ORDER BY deck_count DESC, total_copies DESC
        """)
        
        gx_stats = cursor.fetchall()
        
        f.write(f"Unique GX cards found: {len(gx_stats)}\n")
        f.write("=" * 80 + "\n\n")
        
        f.write("GX CARD USAGE STATISTICS:\n")
        f.write("-" * 80 + "\n")
        f.write(f"{'Rank':<6}{'Japanese Name':<30}{'Card Code':<20}{'Decks':<8}{'Cards':<8}Chinese Name\n")
        f.write("-" * 80 + "\n")
        
        for idx, (jp_name, code, deck_count, total_copies, cn_name) in enumerate(gx_stats, 1):
            cn_display = cn_name if cn_name else '未對應'
            f.write(f"{idx:<6}{jp_name:<30}{code:<20}{deck_count:<8}{total_copies:<8}{cn_display}\n")
        
        f.write("\n" + "=" * 80 + "\n\n")
        
        f.write("DECK DETAILS:\n")
        f.write("-" * 80 + "\n")
        
        for deck in archived_decks:
            f.write(f"\nDeck ID: {deck['deck_id']}\n")
            f.write(f"Player: {deck['player_name']}\n")
            f.write(f"Event: {deck['event']['title']}\n")
            f.write(f"Date: {deck['event']['date']}\n")
            f.write(f"Rank: {deck['rank']}\n")
            f.write(f"Total Cards: {deck['total_cards']}\n")
            f.write(f"URL: {deck['deck_url']}\n")
            f.write(f"\nGX Cards in this deck:\n")
            
            for gx in deck['gx_cards']:
                f.write(f"  - {gx['japanese_name']} ({gx['card_code']}) x{gx['quantity']}\n")
                if gx['chinese_name'] != '未對應':
                    f.write(f"    Chinese: {gx['chinese_name']}\n")
            
            f.write("-" * 80 + "\n")
    
    print(f"📄 Summary report: {report_file}\n")
    
    # Print summary to console
    print("=" * 80)
    print("GX CARD STATISTICS")
    print("=" * 80)
    print(f"{'Rank':<6}{'Japanese Name':<30}{'Code':<20}{'Decks':<8}{'Cards':<8}Status")
    print("-" * 80)
    
    cursor.execute("""
        SELECT 
            dc.card_name,
            dc.card_code,
            COUNT(DISTINCT dc.deck_id) as deck_count,
            SUM(dc.quantity) as total_copies,
            CASE WHEN cm.main_card_id IS NOT NULL THEN '已對應' ELSE '未對應' END as status
        FROM deck_cards dc
        LEFT JOIN card_mappings cm ON dc.card_id = cm.event_card_id
        WHERE dc.card_name LIKE '%GX'
        GROUP BY dc.card_id
        ORDER BY deck_count DESC, total_copies DESC
    """)
    
    gx_stats = cursor.fetchall()
    
    mapped_count = 0
    unmapped_count = 0
    
    for idx, (jp_name, code, deck_count, total_copies, status) in enumerate(gx_stats, 1):
        if status == '已對應':
            mapped_count += 1
        else:
            unmapped_count += 1
        
        print(f"{idx:<6}{jp_name:<30}{code:<20}{deck_count:<8}{total_copies:<8}{status}")
    
    print("=" * 80)
    print(f"\nTotal GX cards: {len(gx_stats)}")
    print(f"Mapped (已對應): {mapped_count}")
    print(f"Unmapped (未對應): {unmapped_count}")
    print(f"Mapping rate: {mapped_count/len(gx_stats)*100:.1f}%")
    
    conn.close()
    
    return {
        'total_decks': len(gx_decks),
        'total_gx_cards': len(gx_stats),
        'mapped': mapped_count,
        'unmapped': unmapped_count,
        'json_file': json_file,
        'report_file': report_file
    }

if __name__ == '__main__':
    print("🎴 GX Decks Archive Tool")
    print("=" * 80)
    print()
    
    result = archive_gx_decks()
    
    print(f"\n✅ Archive complete!")
    print(f"   - {result['total_decks']} decks archived")
    print(f"   - {result['total_gx_cards']} unique GX cards found")
    print(f"   - Files saved to archive/gx_decks/")
