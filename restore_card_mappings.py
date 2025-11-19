"""Check and restore card_mappings table."""
import sqlite3

# Check current database
conn = sqlite3.connect('ptcg_events.db')
c = conn.cursor()

print("Tables in current database:")
c.execute("SELECT name FROM sqlite_master WHERE type='table'")
for table in c.fetchall():
    print(f"  - {table[0]}")

# Check if card_mappings exists
c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='card_mappings'")
if not c.fetchone():
    print("\n❌ card_mappings table is missing!")
    
    # Check backup
    print("\nChecking backup database...")
    c.execute("ATTACH DATABASE 'ptcg_events.db.backup_20251117_211659' AS backup")
    
    c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='card_mappings'", ())
    
    # Try to find card_mappings in backup
    c.execute("SELECT COUNT(*) FROM backup.sqlite_master WHERE type='table' AND name='card_mappings'")
    if c.fetchone()[0] > 0:
        print("✓ Found card_mappings in backup!")
        
        # Create table and copy data
        print("\nRestoring card_mappings table...")
        
        # Get backup schema
        c.execute("PRAGMA backup.table_info(card_mappings)")
        backup_columns = c.fetchall()
        print(f"\nBackup table has {len(backup_columns)} columns:")
        for col in backup_columns:
            print(f"  {col[1]} ({col[2]})")
        
        c.execute("""
            CREATE TABLE IF NOT EXISTS card_mappings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_card_id TEXT NOT NULL,
                main_card_id INTEGER NOT NULL,
                event_card_name TEXT,
                main_card_name TEXT,
                match_type TEXT,
                match_confidence REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(event_card_id)
            )
        """)
        
        # Copy data with only matching columns
        c.execute("""
            INSERT INTO card_mappings 
            (id, event_card_id, main_card_id, event_card_name, main_card_name, match_type, match_confidence, created_at)
            SELECT id, event_card_id, main_card_id, event_card_name, main_card_name, match_type, match_confidence, created_at
            FROM backup.card_mappings
        """)
        mappings_copied = c.rowcount
        
        conn.commit()
        print(f"✓ Copied {mappings_copied:,} card mappings")
    else:
        print("❌ card_mappings not found in backup either")
        print("   You'll need to re-run the linking scripts")
else:
    print("\n✓ card_mappings table exists")
    c.execute("SELECT COUNT(*) FROM card_mappings")
    count = c.fetchone()[0]
    print(f"  Contains {count:,} mappings")

conn.close()
