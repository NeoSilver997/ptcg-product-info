import sqlite3

db_path = r"c:\AI_Server\Coding\PokemonDBByjules\PTCG_CardDB_Tc\pokemon_cards.db"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("=== 檢查恢復後的資料庫 ===\n")

# 總卡片數
cursor.execute("SELECT COUNT(*) FROM cards")
total = cursor.fetchone()[0]
print(f"總卡片數: {total}")

# 日文名稱卡片
cursor.execute("SELECT COUNT(*) FROM cards WHERE name GLOB '*[ァ-ヺ]*'")
japanese = cursor.fetchone()[0]
print(f"日文名稱卡片: {japanese}")

# 顯示幾張日文卡片
cursor.execute("""
    SELECT id, name, card_type, collector_number
    FROM cards
    WHERE name GLOB '*[ァ-ヺ]*'
    LIMIT 10
""")

print(f"\n前10張日文名稱卡片:")
for row in cursor.fetchall():
    print(f"  ID {row[0]}: {row[1]} ({row[2]}) [{row[3]}]")

conn.close()

print(f"\n✅ 資料庫已從備份恢復")
print(f"📌 重要：pokemon_cards.db 應該是只讀的，不應該修改")
