import sqlite3

event_db_path = r"c:\AI_Server\Coding\ptcg-product-info\ptcg_events.db"
event_conn = sqlite3.connect(event_db_path)
event_cursor = event_conn.cursor()

print("=== 分析 ハイパーボール 為何不出現在手動對應系統 ===\n")

# 1. 檢查所有 ハイパーボール 的對應狀態
event_cursor.execute("""
    SELECT 
        dc.card_id,
        dc.card_name,
        dc.card_code,
        CASE 
            WHEN cm.event_card_id IS NULL THEN '未對應'
            ELSE '已對應'
        END as mapping_status,
        cm.main_card_id,
        COUNT(DISTINCT dc.deck_id) as deck_count
    FROM deck_cards dc
    LEFT JOIN card_mappings cm ON dc.card_id = cm.event_card_id
    WHERE dc.card_name = 'ハイパーボール'
    GROUP BY dc.card_id
    ORDER BY deck_count DESC
""")

print("1️⃣ 所有 ハイパーボール 卡片ID的對應狀態:")
all_cards = event_cursor.fetchall()
mapped_count = 0
unmapped_count = 0

for row in all_cards:
    print(f"   卡片ID: {row[0]}, 卡號: {row[2] or '無'}, 狀態: {row[3]}, 使用次數: {row[5]}")
    if row[3] == '已對應':
        mapped_count += 1
    else:
        unmapped_count += 1

print(f"\n   總計: {len(all_cards)} 個不同的卡片ID")
print(f"   已對應: {mapped_count} 個")
print(f"   未對應: {unmapped_count} 個")

# 2. 檢查手動對應系統的查詢邏輯
print(f"\n2️⃣ 手動對應系統查詢邏輯測試:")
print(f"   查詢條件: WHERE cm.event_card_id IS NULL")

event_cursor.execute("""
    SELECT 
        dc.card_id,
        dc.card_name,
        dc.card_code,
        COUNT(DISTINCT dc.deck_id) as deck_count
    FROM deck_cards dc
    LEFT JOIN card_mappings cm ON dc.card_id = cm.event_card_id
    WHERE cm.event_card_id IS NULL
      AND dc.card_name = 'ハイパーボール'
    GROUP BY dc.card_id
    ORDER BY deck_count DESC
""")

results = event_cursor.fetchall()
print(f"   查詢結果: {len(results)} 筆")
for row in results[:5]:
    print(f"      卡片ID: {row[0]}, 卡號: {row[2] or '無'}, 使用次數: {row[3]}")

# 3. 檢查是否有重複對應
print(f"\n3️⃣ 檢查 ハイパーボール 的對應記錄:")
event_cursor.execute("""
    SELECT 
        cm.event_card_id,
        cm.event_card_name,
        cm.main_card_id,
        cm.match_type,
        COUNT(*) as mapping_count
    FROM card_mappings cm
    WHERE cm.event_card_name = 'ハイパーボール'
    GROUP BY cm.event_card_id
    ORDER BY mapping_count DESC
""")

mappings = event_cursor.fetchall()
if mappings:
    print(f"   找到 {len(mappings)} 個對應記錄:")
    for row in mappings:
        print(f"      事件卡ID: {row[0]}, 中文卡ID: {row[2]}, 對應類型: {row[3]}, 記錄數: {row[4]}")
else:
    print(f"   ❌ 沒有任何對應記錄！")

# 4. 測試：如果我們搜尋 "高級球" 會找到什麼
print(f"\n4️⃣ 如果手動對應系統搜尋未對應的 'ハイパーボール':")
event_cursor.execute("""
    SELECT COUNT(DISTINCT dc.card_id)
    FROM deck_cards dc
    LEFT JOIN card_mappings cm ON dc.card_id = cm.event_card_id
    WHERE cm.event_card_id IS NULL
      AND dc.card_name LIKE '%ハイパーボール%'
""")

count = event_cursor.fetchone()[0]
print(f"   應該顯示 {count} 個未對應的 ハイパーボール 卡片ID")

event_conn.close()
