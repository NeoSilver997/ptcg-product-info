import sqlite3
import shutil
from datetime import datetime

# 數據庫路徑
chinese_db_path = r"c:\AI_Server\Coding\PokemonDBByjules\PTCG_CardDB_Tc\pokemon_cards.db"

# 備份數據庫
backup_path = chinese_db_path.replace('.db', f'_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.db')
shutil.copy2(chinese_db_path, backup_path)
print(f"✅ 數據庫已備份: {backup_path}\n")

# 連接到數據庫
conn = sqlite3.connect(chinese_db_path)
cursor = conn.cursor()

print("=== 修正 ボウルタウン (ID 4887) 的資料 ===\n")

# 檢查修正前的資料
cursor.execute("""
    SELECT id, name, card_type, collector_number
    FROM cards
    WHERE id = 4887
""")

before = cursor.fetchone()
print(f"修正前:")
print(f"  ID: {before[0]}")
print(f"  名稱: {before[1]}")
print(f"  卡片類型: {before[2]}")
print(f"  收藏編號: {before[3]}")

# 執行修正
cursor.execute("""
    UPDATE cards
    SET name = '深缽鎮',
        card_type = '競技場卡'
    WHERE id = 4887
""")

conn.commit()

# 檢查修正後的資料
cursor.execute("""
    SELECT id, name, card_type, collector_number
    FROM cards
    WHERE id = 4887
""")

after = cursor.fetchone()
print(f"\n修正後:")
print(f"  ID: {after[0]}")
print(f"  名稱: {after[1]}")
print(f"  卡片類型: {after[2]}")
print(f"  收藏編號: {after[3]}")

print(f"\n✅ 修正完成！")
print(f"📊 受影響的記錄: {cursor.rowcount} 筆")

# 檢查賽事數據庫中的對應關係是否仍然有效
print(f"\n=== 驗證賽事數據庫中的對應關係 ===\n")

event_db_path = r"c:\AI_Server\Coding\ptcg-product-info\ptcg_events.db"
event_conn = sqlite3.connect(event_db_path)
event_cursor = event_conn.cursor()

# 檢查有多少 ボウルタウン 對應到 ID 4887
event_cursor.execute("""
    SELECT COUNT(*) as count
    FROM card_mappings
    WHERE event_card_name = 'ボウルタウン' AND main_card_id = 4887
""")

mapping_count = event_cursor.fetchone()[0]
print(f"賽事數據庫中對應到 ID 4887 的 ボウルタウン 記錄: {mapping_count} 筆")

# 測試查詢：取得對應的中文名稱
event_cursor.execute("""
    SELECT 
        cm.event_card_name as japanese,
        c.name as chinese,
        cm.match_type
    FROM card_mappings cm
    JOIN cards c ON cm.main_card_id = c.id
    WHERE cm.event_card_name = 'ボウルタウン' AND cm.main_card_id = 4887
    LIMIT 5
""", {'db_path': chinese_db_path})

print(f"\n測試查詢結果（前5筆）:")
for row in event_cursor.fetchall():
    print(f"  日文: {row[0]} → 中文: {row[1]} (對應類型: {row[2]})")

event_conn.close()
conn.close()

print(f"\n🎉 所有修正完成！現在 ボウルタウン 應該會正確顯示為「深缽鎮」")
