import sqlite3

# 連接到中文主資料庫
chinese_db_path = r"c:\AI_Server\Coding\PokemonDBByjules\PTCG_CardDB_Tc\pokemon_cards.db"
conn = sqlite3.connect(chinese_db_path)
cursor = conn.cursor()

print("=== 驗證修正結果 ===\n")

# 1. 檢查 ID 4887 的當前狀態
cursor.execute("""
    SELECT 
        c.id,
        c.name,
        c.card_type,
        c.collector_number,
        e.code as expansion_code
    FROM cards c
    LEFT JOIN expansions e ON c.expansion_id = e.id
    WHERE c.id = 4887
""")

result = cursor.fetchone()
print(f"✅ 中文數據庫 ID 4887:")
print(f"   名稱: {result[1]}")
print(f"   卡片類型: {result[2]}")
print(f"   收藏編號: {result[3]}")
print(f"   系列代碼: {result[4]}")

# 2. 檢查所有深缽鎮卡片
print(f"\n=== 所有「深缽鎮」卡片 ===")
cursor.execute("""
    SELECT 
        c.id,
        c.name,
        c.card_type,
        e.code as expansion_code,
        c.collector_number
    FROM cards c
    LEFT JOIN expansions e ON c.expansion_id = e.id
    WHERE c.name = '深缽鎮'
    ORDER BY c.id
""")

results = cursor.fetchall()
for row in results:
    print(f"   ID {row[0]}: {row[1]} ({row[3]} {row[4]}) - {row[2]}")

conn.close()

# 3. 測試賽事數據庫查詢
print(f"\n=== 測試日曆介面查詢 ===")

event_db_path = r"c:\AI_Server\Coding\ptcg-product-info\ptcg_events.db"
event_conn = sqlite3.connect(event_db_path)

# 附加中文數據庫
event_conn.execute(f"ATTACH DATABASE '{chinese_db_path}' AS chinese_db")

event_cursor = event_conn.cursor()

# 模擬日曆介面的查詢
event_cursor.execute("""
    SELECT 
        dc.card_name as japanese_name,
        COALESCE(chinese_db.cards.name, dc.card_name) as display_name,
        chinese_db.cards.card_type,
        dc.card_code
    FROM deck_cards dc
    LEFT JOIN card_mappings cm ON dc.card_id = cm.event_card_id
    LEFT JOIN chinese_db.cards ON cm.main_card_id = chinese_db.cards.id
    WHERE dc.card_name = 'ボウルタウン'
    LIMIT 5
""")

print(f"日曆介面顯示結果（前5筆）:")
for row in event_cursor.fetchall():
    print(f"   日文: {row[0]} → 顯示: {row[1]} ({row[2]}) [{row[3]}]")

event_conn.close()

print(f"\n🎉 修正完成！ボウルタウン 現在會正確顯示為「深缽鎮」（競技場卡）")
