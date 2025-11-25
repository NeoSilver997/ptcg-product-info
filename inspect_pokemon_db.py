"""
Quick script to inspect pokemon_cards.db structure
"""
import sqlite3

db_path = 'pokemon_cards.db'

try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Get table names
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()
    
    print("=" * 70)
    print("Pokemon Cards Database Structure")
    print("=" * 70)
    print(f"\nDatabase: {db_path}")
    print(f"\nTables found: {len(tables)}")
    
    for table in tables:
        table_name = table[0]
        print(f"\n--- Table: {table_name} ---")
        
        # Get table info
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = cursor.fetchall()
        
        print("Columns:")
        for col in columns:
            print(f"  - {col[1]} ({col[2]})")
        
        # Get row count
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        count = cursor.fetchone()[0]
        print(f"Total rows: {count}")
        
        # Show sample data
        if count > 0:
            cursor.execute(f"SELECT * FROM {table_name} LIMIT 1")
            sample = cursor.fetchone()
            print(f"Sample row: {sample[:3] if len(sample) > 3 else sample}...")
    
    conn.close()
    print("\n" + "=" * 70)
    
except Exception as e:
    print(f"Error: {e}")
