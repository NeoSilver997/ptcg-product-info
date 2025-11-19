"""
Fix corrupted database by dumping and recreating.
"""

import sqlite3
import os
import shutil
from datetime import datetime

def fix_database():
    """Fix corrupted database"""
    
    db_path = 'ptcg_events.db'
    backup_path = f'ptcg_events_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.db'
    
    print(f"Creating backup: {backup_path}")
    shutil.copy2(db_path, backup_path)
    
    print("Attempting database recovery...")
    
    try:
        # Try to dump and recover
        conn = sqlite3.connect(db_path)
        
        # Get the SQL dump
        print("Dumping database...")
        dump = '\n'.join(conn.iterdump())
        conn.close()
        
        # Create new database
        new_db = 'ptcg_events_recovered.db'
        if os.path.exists(new_db):
            os.remove(new_db)
        
        print(f"Creating recovered database: {new_db}")
        new_conn = sqlite3.connect(new_db)
        new_conn.executescript(dump)
        new_conn.close()
        
        # Replace old database with recovered one
        print("Replacing old database with recovered version...")
        os.replace(new_db, db_path)
        
        print("✓ Database recovery complete!")
        
        # Verify the recovered database
        print("\nVerifying recovered database...")
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM events")
        events = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM decks")
        decks = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM deck_cards")
        cards = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM card_mappings")
        mappings = cursor.fetchone()[0]
        
        print(f"\nRecovered database stats:")
        print(f"  Events: {events:,}")
        print(f"  Decks: {decks:,}")
        print(f"  Deck Cards: {cards:,}")
        print(f"  Card Mappings: {mappings:,}")
        
        conn.close()
        
    except Exception as e:
        print(f"Error during recovery: {e}")
        print(f"\nBackup preserved at: {backup_path}")
        return False
    
    return True

if __name__ == "__main__":
    print("="*60)
    print("Database Recovery Tool")
    print("="*60 + "\n")
    
    if fix_database():
        print("\n✓ Database successfully recovered!")
    else:
        print("\n✗ Recovery failed. Check backup file.")
