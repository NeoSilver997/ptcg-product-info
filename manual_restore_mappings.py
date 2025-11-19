"""Manually restore card_mappings from backup."""
import sqlite3

conn = sqlite3.connect('ptcg_events.db')
c = conn.cursor()

# Attach backup
c.execute("ATTACH DATABASE 'ptcg_events.db.backup_20251117_211659' AS backup")

# Check backup schema
print("Checking backup card_mappings schema...")
c.execute("PRAGMA backup.table_info(card_mappings)")
columns = c.fetchall()
print(f"Backup has {len(columns)} columns:")
for col in columns:
    print(f"  {col[0]}: {col[1]} ({col[2]})")

# Check count
c.execute("SELECT COUNT(*) FROM backup.card_mappings")
count = c.fetchone()[0]
print(f"\nBackup has {count:,} mappings")

# Drop and recreate with correct schema
print("\nDropping existing card_mappings...")
c.execute("DROP TABLE IF EXISTS card_mappings")

print("Creating new card_mappings table...")
# Create with exact backup schema
c.execute("""
    CREATE TABLE card_mappings AS 
    SELECT * FROM backup.card_mappings LIMIT 0
""")

# Copy all data
print("Copying data from backup...")
c.execute("INSERT INTO card_mappings SELECT * FROM backup.card_mappings")
copied = c.rowcount

conn.commit()

print(f"\n✓ Copied {copied:,} card mappings")

# Verify
c.execute("SELECT COUNT(*) FROM card_mappings")
final_count = c.fetchone()[0]
print(f"✓ Final count: {final_count:,} mappings")

conn.close()
