"""
修復 マキシマムベルト 的翻譯錯誤
將錯誤連結的 貴重手推車 改為正確的 極限腰帶
"""

import sqlite3

DB_PATH = 'ptcg_events.db'

def fix_maximumbelt_translation():
    """修復 マキシマムベルト 的中文翻譯"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    print("=" * 80)
    print("🔧 修復 マキシマムベルト 翻譯")
    print("=" * 80)
    
    # 1. 檢查當前錯誤的連結
    print("\n【檢查當前狀態】")
    cursor.execute("""
        SELECT 
            event_card_id,
            event_card_name,
            main_card_name,
            match_type
        FROM card_mappings
        WHERE event_card_name = 'マキシマムベルト'
    """)
    
    current_mappings = cursor.fetchall()
    print(f"找到 {len(current_mappings)} 個 マキシマムベルト 的對應:")
    
    wrong_count = 0
    correct_count = 0
    for card_id, jp_name, cn_name, match_type in current_mappings:
        print(f"  - Card ID {card_id}: {jp_name} → {cn_name} ({match_type})")
        if cn_name == '貴重手推車':
            wrong_count += 1
        elif cn_name == '極限腰帶':
            correct_count += 1
    
    print(f"\n錯誤連結 (貴重手推車): {wrong_count} 個")
    print(f"正確連結 (極限腰帶): {correct_count} 個")
    
    if wrong_count == 0:
        print("\n✅ 沒有發現錯誤連結，無需修復！")
        conn.close()
        return
    
    # 2. 查找正確的中文卡片 ID
    print("\n【查找正確的中文卡片】")
    
    # 從主資料庫查找極限腰帶
    main_db_path = r'c:\AI_Server\Coding\PokemonDBByjules\PTCG_CardDB_Tc\pokemon_cards.db'
    main_conn = sqlite3.connect(main_db_path)
    main_cursor = main_conn.cursor()
    
    main_cursor.execute("""
        SELECT 
            c.id, 
            c.name, 
            e.code, 
            c.collector_number
        FROM cards c
        LEFT JOIN expansions e ON c.expansion_id = e.id
        WHERE c.name LIKE '%極限腰帶%'
        LIMIT 5
    """)
    
    correct_cards = main_cursor.fetchall()
    print(f"找到 {len(correct_cards)} 個極限腰帶卡片:")
    for card_id, name, exp_code, coll_num in correct_cards:
        print(f"  - ID {card_id}: {name} ({exp_code} {coll_num})")
    
    if not correct_cards:
        print("❌ 錯誤：找不到極限腰帶卡片！")
        main_conn.close()
        conn.close()
        return
    
    # 使用第一個找到的正確卡片
    correct_card_id, correct_card_name, correct_exp_code, correct_coll_num = correct_cards[0]
    print(f"\n將使用: {correct_card_name} (ID: {correct_card_id}, {correct_exp_code} {correct_coll_num})")
    
    # 3. 更新錯誤的對應
    print("\n【開始修復】")
    
    cursor.execute("""
        UPDATE card_mappings
        SET 
            main_card_id = ?,
            main_card_name = ?,
            main_expansion_code = ?,
            main_collector_number = ?
        WHERE event_card_name = 'マキシマムベルト'
        AND main_card_name = '貴重手推車'
    """, (correct_card_id, correct_card_name, correct_exp_code or '', correct_coll_num or ''))
    
    updated_count = cursor.rowcount
    conn.commit()
    
    print(f"✅ 已更新 {updated_count} 個錯誤對應")
    
    # 4. 更新用戶翻譯表
    print("\n【更新用戶翻譯表】")
    try:
        cursor.execute("""
            INSERT OR REPLACE INTO user_translations 
            (japanese_name, chinese_name, updated_at)
            VALUES ('マキシマムベルト', '極限腰帶', CURRENT_TIMESTAMP)
        """)
        conn.commit()
        print("✅ 已更新用戶翻譯記錄")
    except Exception as e:
        print(f"⚠️ 更新用戶翻譯表失敗: {e}")
    
    # 5. 驗證修復結果
    print("\n【驗證修復結果】")
    cursor.execute("""
        SELECT 
            event_card_name,
            COUNT(*) as count,
            main_card_name
        FROM card_mappings
        WHERE event_card_name = 'マキシマムベルト'
        GROUP BY main_card_name
    """)
    
    final_mappings = cursor.fetchall()
    print("修復後的對應:")
    for jp_name, count, cn_name in final_mappings:
        print(f"  - {jp_name} → {cn_name}: {count} 個")
    
    main_conn.close()
    conn.close()
    
    print("\n" + "=" * 80)
    print("✅ 修復完成！")
    print("=" * 80)


if __name__ == '__main__':
    fix_maximumbelt_translation()
