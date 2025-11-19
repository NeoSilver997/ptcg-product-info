import sqlite3

chinese_db_path = r"c:\AI_Server\Coding\PokemonDBByjules\PTCG_CardDB_Tc\pokemon_cards.db"
event_db_path = r"c:\AI_Server\Coding\ptcg-product-info\ptcg_events.db"

print("=== 搜尋 デデンネGX ===\n")

# 1. 在中文資料庫搜尋
print("1️⃣ 在中文資料庫搜尋:")
conn = sqlite3.connect(chinese_db_path)
cursor = conn.cursor()

# 搜尋可能的中文名稱
search_terms = ['デデンネ', '電飛鼠', '咚咚鼠', 'Dedenne']
for term in search_terms:
    cursor.execute("""
        SELECT id, name, card_type, collector_number
        FROM cards
        WHERE name LIKE ?
        LIMIT 5
    """, (f'%{term}%',))
    
    results = cursor.fetchall()
    if results:
        print(f"\n   包含 '{term}' 的卡片:")
        for row in results:
            print(f"      ID {row[0]}: {row[1]} ({row[2]}) [{row[3]}]")

conn.close()

# 2. 在賽事資料庫查看使用情況
print(f"\n2️⃣ デデンネGX 在賽事資料庫中的使用:")
event_conn = sqlite3.connect(event_db_path)
event_cursor = event_conn.cursor()

event_cursor.execute("""
    SELECT 
        card_id,
        card_name,
        card_code,
        COUNT(DISTINCT deck_id) as deck_count,
        SUM(quantity) as total_cards
    FROM deck_cards
    WHERE card_name LIKE '%デデンネ%'
    GROUP BY card_id
    ORDER BY deck_count DESC
""")

results = event_cursor.fetchall()
print(f"\n   找到 {len(results)} 個 デデンネ 相關的卡片ID:")
for row in results:
    print(f"      ID: {row[0]}, 名稱: {row[1]}, 卡號: {row[2] or '無'}")
    print(f"         使用: {row[3]} 套牌, {row[4]} 張卡片")

# 3. 檢查對應狀態
print(f"\n3️⃣ 檢查對應狀態:")
event_cursor.execute("""
    SELECT 
        dc.card_id,
        dc.card_name,
        dc.card_code,
        cm.main_card_id,
        COUNT(DISTINCT dc.deck_id) as deck_count
    FROM deck_cards dc
    LEFT JOIN card_mappings cm ON dc.card_id = cm.event_card_id
    WHERE dc.card_name LIKE '%デデンネ%'
    GROUP BY dc.card_id
    ORDER BY deck_count DESC
""")

results = event_cursor.fetchall()
for row in results:
    status = "✅ 已對應" if row[3] else "❌ 未對應"
    print(f"\n   {status} - {row[1]} [{row[2] or '無卡號'}]")
    print(f"      事件卡ID: {row[0]}, 中文卡ID: {row[3] or 'None'}, 使用: {row[4]} 套牌")

event_conn.close()

print(f"\n💡 建議: 如果中文資料庫中沒有 デデンネGX，可能需要:")
print(f"   1. 確認正確的中文翻譯名稱")
print(f"   2. 檢查是否在不同系列中有此卡片")
print(f"   3. 如果確實缺少，需要從官方網站補充資料")
