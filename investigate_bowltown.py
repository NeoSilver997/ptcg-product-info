import sqlite3

# 連接到中文主資料庫
chinese_db_path = r"c:\AI_Server\Coding\PokemonDBByjules\PTCG_CardDB_Tc\pokemon_cards.db"
conn = sqlite3.connect(chinese_db_path)
cursor = conn.cursor()

print("=== 檢查 '深缽鎮' 卡片資訊 ===\n")

cursor.execute("""
    SELECT 
        c.id,
        c.name,
        c.card_type,
        c.collector_number,
        e.name as expansion_name,
        e.code as expansion_code,
        c.image_url
    FROM cards c
    LEFT JOIN expansions e ON c.expansion_id = e.id
    WHERE c.name = '深缽鎮'
""")

results = cursor.fetchall()

for row in results:
    print(f"卡片 ID: {row[0]}")
    print(f"名稱: {row[1]}")
    print(f"卡片類型: {row[2]}")
    print(f"收藏編號: {row[3]}")
    print(f"系列名稱: {row[4]}")
    print(f"系列代碼: {row[5]}")
    print(f"圖片URL: {row[6]}")
    print("-" * 50)

print("\n=== 檢查 SVN 系列中編號 041 的卡片 ===\n")

cursor.execute("""
    SELECT 
        c.id,
        c.name,
        c.card_type,
        c.collector_number,
        e.name as expansion_name,
        e.code as expansion_code
    FROM cards c
    LEFT JOIN expansions e ON c.expansion_id = e.id
    WHERE e.code = 'SVN' AND c.collector_number = '041'
""")

result = cursor.fetchone()

if result:
    print(f"卡片 ID: {result[0]}")
    print(f"名稱: {result[1]}")
    print(f"卡片類型: {result[2]}")
    print(f"收藏編號: {result[3]}")
    print(f"系列名稱: {result[4]}")
    print(f"系列代碼: {result[5]}")
else:
    print("❌ 未找到 SVN 系列編號 041 的卡片")

# 檢查賽事數據庫中 ボウルタウン 的所有出現
print("\n=== 檢查賽事數據庫中 ボウルタウン 的使用情況 ===\n")

event_db_path = r"c:\AI_Server\Coding\ptcg-product-info\ptcg_events.db"
event_conn = sqlite3.connect(event_db_path)
event_cursor = event_conn.cursor()

event_cursor.execute("""
    SELECT DISTINCT card_code
    FROM deck_cards
    WHERE card_name = 'ボウルタウン' AND card_code IS NOT NULL AND card_code != ''
    ORDER BY card_code
""")

codes = event_cursor.fetchall()
print(f"ボウルタウン 出現的卡號:")
for code in codes:
    print(f"  • {code[0]}")

event_conn.close()
conn.close()
