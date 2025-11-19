import sqlite3

event_db_path = r"c:\AI_Server\Coding\ptcg-product-info\ptcg_events.db"
chinese_db_path = r"c:\AI_Server\Coding\PokemonDBByjules\PTCG_CardDB_Tc\pokemon_cards.db"

event_conn = sqlite3.connect(event_db_path)
event_cursor = event_conn.cursor()

print("=== 檢查 ハイパーボール 在賽事資料庫中的狀態 ===\n")

# 1. 檢查在 deck_cards 中的記錄
event_cursor.execute("""
    SELECT card_id, card_name, card_code, COUNT(*) as usage_count
    FROM deck_cards
    WHERE card_name = 'ハイパーボール'
    GROUP BY card_id
    ORDER BY usage_count DESC
    LIMIT 10
""")

print("1️⃣ ハイパーボール 在 deck_cards 中的記錄:")
for row in event_cursor.fetchall():
    print(f"   卡片ID: {row[0]}")
    print(f"   名稱: {row[1]}")
    print(f"   卡號: {row[2]}")
    print(f"   使用次數: {row[3]}")
    print()

# 2. 檢查對應狀態
event_cursor.execute("""
    SELECT event_card_id, event_card_name, main_card_id, match_type
    FROM card_mappings
    WHERE event_card_name = 'ハイパーボール'
    LIMIT 5
""")

mappings = event_cursor.fetchall()
print(f"2️⃣ ハイパーボール 的對應記錄數: {len(mappings)}")
if mappings:
    for row in mappings:
        print(f"   事件卡ID: {row[0]}, 中文卡ID: {row[2]}, 對應類型: {row[3]}")
else:
    print("   ❌ 沒有找到任何對應記錄！")

# 3. 檢查未對應的 ハイパーボール
event_cursor.execute("""
    SELECT DISTINCT dc.card_id, dc.card_name, dc.card_code
    FROM deck_cards dc
    LEFT JOIN card_mappings cm ON dc.card_id = cm.event_card_id
    WHERE dc.card_name = 'ハイパーボール' AND cm.main_card_id IS NULL
    LIMIT 10
""")

unmapped = event_cursor.fetchall()
print(f"\n3️⃣ 未對應的 ハイパーボール 記錄: {len(unmapped)}")
for row in unmapped:
    print(f"   卡片ID: {row[0]}, 卡號: {row[2] or '無卡號'}")

# 4. 檢查中文資料庫中是否有大師球
event_conn.close()

chinese_conn = sqlite3.connect(chinese_db_path)
chinese_cursor = chinese_conn.cursor()

print(f"\n4️⃣ 搜尋中文資料庫:")
search_terms = ['大師球', '高級球', '超級球', '精靈球']
for term in search_terms:
    chinese_cursor.execute("""
        SELECT id, name, card_type, collector_number
        FROM cards
        WHERE name LIKE ?
        LIMIT 3
    """, (f'%{term}%',))
    
    results = chinese_cursor.fetchall()
    if results:
        print(f"\n   搜尋 '{term}':")
        for row in results:
            print(f"      ID {row[0]}: {row[1]} ({row[2]}) [{row[3]}]")

chinese_conn.close()
