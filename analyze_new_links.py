"""
分析新連結的卡片數據
顯示手動連結的統計信息和詳細列表
"""

import sqlite3
from collections import defaultdict
from datetime import datetime

# Database path
DB_PATH = 'ptcg_events.db'

def analyze_new_links():
    """分析新連結的卡片"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    print("=" * 80)
    print("📊 新連結卡片分析報告")
    print("=" * 80)
    print(f"生成時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    # 1. 總體統計
    print("\n【總體統計】")
    print("-" * 80)
    
    # 總卡片數
    cursor.execute("SELECT COUNT(DISTINCT card_id) FROM deck_cards")
    total_cards = cursor.fetchone()[0]
    
    # 已對應卡片數
    cursor.execute("SELECT COUNT(DISTINCT event_card_id) FROM card_mappings")
    mapped_cards = cursor.fetchone()[0]
    
    # 手動連結數量
    cursor.execute("SELECT COUNT(*) FROM card_mappings WHERE match_type = 'manual_link'")
    manual_links = cursor.fetchone()[0]
    
    # 其他對應類型統計
    cursor.execute("""
        SELECT match_type, COUNT(*) as count
        FROM card_mappings
        WHERE match_type != 'manual_link'
        GROUP BY match_type
        ORDER BY count DESC
    """)
    other_links = cursor.fetchall()
    
    coverage = (mapped_cards / total_cards * 100) if total_cards > 0 else 0
    
    print(f"總卡片數: {total_cards:,}")
    print(f"已對應卡片: {mapped_cards:,} ({coverage:.1f}%)")
    print(f"未對應卡片: {total_cards - mapped_cards:,}")
    print(f"\n手動連結: {manual_links:,}")
    
    print("\n其他連結類型:")
    for match_type, count in other_links:
        print(f"  - {match_type}: {count:,}")
    
    # 2. 手動連結詳細列表
    print("\n\n【手動連結卡片列表】")
    print("-" * 80)
    
    cursor.execute("""
        SELECT 
            cm.event_card_id,
            cm.event_card_name,
            cm.event_card_code,
            cm.main_card_name,
            cm.main_expansion_code,
            cm.main_collector_number,
            COUNT(DISTINCT dc.deck_id) as deck_count,
            SUM(dc.quantity) as total_quantity
        FROM card_mappings cm
        JOIN deck_cards dc ON cm.event_card_id = dc.card_id
        WHERE cm.match_type = 'manual_link'
        GROUP BY cm.event_card_id
        ORDER BY deck_count DESC, total_quantity DESC
    """)
    
    manual_link_details = cursor.fetchall()
    
    if manual_link_details:
        print(f"\n共 {len(manual_link_details)} 個手動連結:")
        print()
        for i, (event_id, jp_name, jp_code, cn_name, exp_code, coll_num, decks, qty) in enumerate(manual_link_details, 1):
            print(f"{i}. 【{jp_name}】")
            print(f"   日文代碼: {jp_code or '無'}")
            print(f"   → 中文卡片: {cn_name}")
            print(f"   中文代碼: {exp_code} {coll_num}")
            print(f"   使用統計: {decks:,} 套牌 | {qty:,} 張")
            print()
    else:
        print("目前沒有手動連結的卡片")
    
    # 3. 按日文卡片名稱分組統計
    print("\n【按日文卡片名稱分組統計】")
    print("-" * 80)
    
    cursor.execute("""
        SELECT 
            cm.event_card_name,
            COUNT(DISTINCT cm.event_card_id) as variant_count,
            cm.main_card_name,
            SUM(deck_stats.deck_count) as total_decks,
            SUM(deck_stats.total_quantity) as total_cards
        FROM card_mappings cm
        JOIN (
            SELECT card_id, 
                   COUNT(DISTINCT deck_id) as deck_count,
                   SUM(quantity) as total_quantity
            FROM deck_cards
            GROUP BY card_id
        ) deck_stats ON cm.event_card_id = deck_stats.card_id
        WHERE cm.match_type = 'manual_link'
        GROUP BY cm.event_card_name, cm.main_card_name
        ORDER BY total_decks DESC
    """)
    
    grouped_stats = cursor.fetchall()
    
    if grouped_stats:
        print(f"\n共 {len(grouped_stats)} 個不同的日文卡片名稱:")
        print()
        for i, (jp_name, variants, cn_name, decks, cards) in enumerate(grouped_stats, 1):
            print(f"{i}. {jp_name} → {cn_name}")
            print(f"   變體數: {variants} 個")
            print(f"   總使用: {decks:,} 套牌 | {cards:,} 張")
            print()
    
    # 4. 用戶翻譯表統計（如果存在）
    print("\n【用戶翻譯記錄】")
    print("-" * 80)
    
    try:
        cursor.execute("""
            SELECT japanese_name, chinese_name, updated_at
            FROM user_translations
            ORDER BY updated_at DESC
        """)
        translations = cursor.fetchall()
        
        if translations:
            print(f"\n共 {len(translations)} 個翻譯記錄:")
            print()
            for i, (jp_name, cn_name, updated_at) in enumerate(translations, 1):
                print(f"{i}. {jp_name} → {cn_name}")
                print(f"   更新時間: {updated_at}")
                print()
        else:
            print("目前沒有用戶翻譯記錄")
    except sqlite3.OperationalError:
        print("user_translations 表不存在")
    
    # 5. 最高使用率的手動連結卡片 TOP 10
    print("\n【最高使用率手動連結卡片 TOP 10】")
    print("-" * 80)
    
    cursor.execute("""
        SELECT 
            cm.event_card_name,
            cm.main_card_name,
            COUNT(DISTINCT dc.deck_id) as deck_count,
            SUM(dc.quantity) as total_quantity,
            ROUND(COUNT(DISTINCT dc.deck_id) * 100.0 / (SELECT COUNT(DISTINCT deck_id) FROM deck_cards), 2) as usage_rate
        FROM card_mappings cm
        JOIN deck_cards dc ON cm.event_card_id = dc.card_id
        WHERE cm.match_type = 'manual_link'
        GROUP BY cm.event_card_name, cm.main_card_name
        ORDER BY deck_count DESC
        LIMIT 10
    """)
    
    top_cards = cursor.fetchall()
    
    if top_cards:
        print()
        for i, (jp_name, cn_name, decks, qty, usage) in enumerate(top_cards, 1):
            print(f"{i}. {jp_name} → {cn_name}")
            print(f"   使用率: {usage}% ({decks:,} 套牌 / {qty:,} 張)")
            print()
    
    conn.close()
    
    print("=" * 80)
    print("分析完成！")
    print("=" * 80)


def export_manual_links_csv():
    """導出手動連結到 CSV"""
    import csv
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT 
            cm.event_card_id,
            cm.event_card_name,
            cm.event_card_code,
            cm.main_card_id,
            cm.main_card_name,
            cm.main_expansion_code,
            cm.main_collector_number,
            COUNT(DISTINCT dc.deck_id) as deck_count,
            SUM(dc.quantity) as total_quantity
        FROM card_mappings cm
        JOIN deck_cards dc ON cm.event_card_id = dc.card_id
        WHERE cm.match_type = 'manual_link'
        GROUP BY cm.event_card_id
        ORDER BY deck_count DESC
    """)
    
    results = cursor.fetchall()
    
    filename = f'manual_links_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
    
    with open(filename, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)
        writer.writerow([
            'Event Card ID', 'Japanese Name', 'Japanese Code',
            'Main Card ID', 'Chinese Name', 'Expansion Code', 'Collector Number',
            'Deck Count', 'Total Quantity'
        ])
        writer.writerows(results)
    
    conn.close()
    
    print(f"\n✅ 已導出 {len(results)} 個手動連結到: {filename}")
    return filename


if __name__ == '__main__':
    analyze_new_links()
    
    # 詢問是否導出 CSV
    print("\n是否導出手動連結到 CSV? (y/n): ", end='')
    try:
        choice = input().strip().lower()
        if choice == 'y':
            export_manual_links_csv()
    except:
        pass
