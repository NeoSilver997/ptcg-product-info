import sqlite3
import shutil
from datetime import datetime

# 備份數據庫
chinese_db_path = r"c:\AI_Server\Coding\PokemonDBByjules\PTCG_CardDB_Tc\pokemon_cards.db"
backup_path = chinese_db_path.replace('.db', f'_backup_before_delete_{datetime.now().strftime("%Y%m%d_%H%M%S")}.db')
shutil.copy2(chinese_db_path, backup_path)
print(f"✅ 數據庫已備份: {backup_path}\n")

conn = sqlite3.connect(chinese_db_path)
cursor = conn.cursor()

# 先查詢要刪除的卡片
cursor.execute("""
    SELECT id, name, card_type, collector_number
    FROM cards
    WHERE name GLOB '*[ァ-ヺ]*'
""")

to_delete = cursor.fetchall()
print(f"=== 將要刪除的 {len(to_delete)} 張日文名稱卡片 ===\n")
for card in to_delete[:10]:
    print(f"  ID {card[0]}: {card[1]} ({card[2]}) [{card[3]}]")
if len(to_delete) > 10:
    print(f"  ... 還有 {len(to_delete) - 10} 張")

# 刪除
cursor.execute("""
    DELETE FROM cards
    WHERE name GLOB '*[ァ-ヺ]*'
""")

deleted_count = cursor.rowcount
conn.commit()
conn.close()

print(f"\n✅ 已刪除 {deleted_count} 張日文名稱的卡片")
print(f"📊 備份位置: {backup_path}")
