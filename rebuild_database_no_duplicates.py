"""
Rebuild database with duplicate prevention.

This script:
1. Backs up the current database
2. Creates a new database with UNIQUE constraints
3. Imports data without duplicates
"""

import sqlite3
import shutil
from datetime import datetime
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def backup_database(db_path='ptcg_events.db'):
    """Create backup of current database."""
    backup_path = f'{db_path}.backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}'
    shutil.copy2(db_path, backup_path)
    logger.info(f"Backup created: {backup_path}")
    return backup_path


def get_unique_deck_cards(old_conn):
    """Get unique deck cards from old database, eliminating duplicates."""
    cursor = old_conn.cursor()
    
    # Get all deck cards, grouped by deck_id, card_name, card_code
    # Sum quantities for true duplicates
    query = """
    SELECT 
        deck_id,
        card_id,
        card_name,
        card_code,
        SUM(quantity) as total_quantity,
        image_url
    FROM deck_cards
    GROUP BY deck_id, card_name, card_code
    ORDER BY deck_id, card_name
    """
    
    cursor.execute(query)
    return cursor.fetchall()


def rebuild_database(source_db='ptcg_events.db', target_db='ptcg_events_clean.db'):
    """Rebuild database without duplicates."""
    
    # Create new clean database
    if Path(target_db).exists():
        Path(target_db).unlink()
    
    target_conn = sqlite3.connect(target_db)
    target_conn.execute("PRAGMA foreign_keys = ON")
    
    # Attach source database
    target_conn.execute(f"ATTACH DATABASE '{source_db}' AS source")
    
    cursor = target_conn.cursor()
    
    # Create tables with UNIQUE constraints
    logger.info("Creating tables with duplicate prevention...")
    
    # Events table
    cursor.execute("""
        CREATE TABLE events (
            event_id TEXT PRIMARY KEY,
            event_date DATE NOT NULL,
            event_title TEXT,
            event_host TEXT,
            event_address TEXT,
            event_location TEXT,
            event_url TEXT,
            import_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Players table
    cursor.execute("""
        CREATE TABLE players (
            player_id TEXT PRIMARY KEY,
            player_name TEXT,
            player_area TEXT,
            first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Event results table
    cursor.execute("""
        CREATE TABLE event_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id TEXT NOT NULL,
            player_id TEXT NOT NULL,
            rank TEXT NOT NULL,
            points TEXT,
            deck_id TEXT,
            FOREIGN KEY (event_id) REFERENCES events(event_id),
            FOREIGN KEY (player_id) REFERENCES players(player_id),
            UNIQUE(event_id, player_id, rank)
        )
    """)
    
    # Decks table
    cursor.execute("""
        CREATE TABLE decks (
            deck_id TEXT PRIMARY KEY,
            deck_code TEXT,
            deck_url TEXT,
            event_id TEXT,
            player_id TEXT,
            rank TEXT,
            import_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (event_id) REFERENCES events(event_id),
            FOREIGN KEY (player_id) REFERENCES players(player_id)
        )
    """)
    
    # Deck cards table WITH UNIQUE CONSTRAINT
    cursor.execute("""
        CREATE TABLE deck_cards (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            deck_id TEXT NOT NULL,
            card_id TEXT,
            card_name TEXT NOT NULL,
            card_code TEXT,
            quantity INTEGER NOT NULL,
            image_url TEXT,
            FOREIGN KEY (deck_id) REFERENCES decks(deck_id),
            UNIQUE(deck_id, card_name, card_code)
        )
    """)
    
    # Create indexes
    cursor.execute("CREATE INDEX idx_event_date ON events(event_date)")
    cursor.execute("CREATE INDEX idx_event_results_event ON event_results(event_id)")
    cursor.execute("CREATE INDEX idx_event_results_player ON event_results(player_id)")
    cursor.execute("CREATE INDEX idx_decks_event ON decks(event_id)")
    cursor.execute("CREATE INDEX idx_deck_cards_deck ON deck_cards(deck_id)")
    cursor.execute("CREATE INDEX idx_deck_cards_card ON deck_cards(card_id)")
    
    target_conn.commit()
    logger.info("Tables created successfully")
    
    # Copy data
    logger.info("Copying events...")
    cursor.execute("INSERT INTO events SELECT * FROM source.events")
    events_copied = cursor.rowcount
    
    logger.info("Copying players...")
    cursor.execute("INSERT INTO players SELECT * FROM source.players")
    players_copied = cursor.rowcount
    
    logger.info("Copying event results...")
    cursor.execute("INSERT INTO event_results SELECT * FROM source.event_results")
    results_copied = cursor.rowcount
    
    logger.info("Copying decks...")
    cursor.execute("INSERT INTO decks SELECT * FROM source.decks")
    decks_copied = cursor.rowcount
    
    # Copy deck cards without duplicates
    logger.info("Copying deck cards (removing duplicates)...")
    
    # Get unique cards from source
    cursor.execute("""
        SELECT 
            deck_id,
            card_id,
            card_name,
            card_code,
            SUM(quantity) as total_quantity,
            image_url
        FROM source.deck_cards
        GROUP BY deck_id, card_name, card_code
        ORDER BY deck_id, card_name
    """)
    unique_cards = cursor.fetchall()
    
    for card in unique_cards:
        cursor.execute("""
            INSERT INTO deck_cards 
            (deck_id, card_id, card_name, card_code, quantity, image_url)
            VALUES (?, ?, ?, ?, ?, ?)
        """, card)
    
    cards_copied = len(unique_cards)
    
    target_conn.commit()
    
    # Get statistics
    cursor.execute("SELECT COUNT(*) FROM source.deck_cards")
    original_cards = cursor.fetchone()[0]
    
    duplicates_removed = original_cards - cards_copied
    
    logger.info("=" * 60)
    logger.info("REBUILD SUMMARY")
    logger.info("=" * 60)
    logger.info(f"Events copied: {events_copied}")
    logger.info(f"Players copied: {players_copied}")
    logger.info(f"Event results copied: {results_copied}")
    logger.info(f"Decks copied: {decks_copied}")
    logger.info(f"Original deck cards: {original_cards:,}")
    logger.info(f"Unique deck cards: {cards_copied:,}")
    logger.info(f"Duplicates removed: {duplicates_removed:,}")
    logger.info("=" * 60)
    
    # Close connection
    target_conn.close()
    
    return cards_copied, duplicates_removed


def main():
    """Main execution."""
    logger.info("Starting database rebuild to remove duplicates")
    
    db_path = 'ptcg_events.db'
    
    # Check if database exists
    if not Path(db_path).exists():
        logger.error(f"Database not found: {db_path}")
        return
    
    # Create backup
    backup_path = backup_database(db_path)
    
    try:
        # Rebuild database
        clean_db = 'ptcg_events_clean.db'
        
        cards_copied, duplicates = rebuild_database(db_path, clean_db)
        
        # Replace old database with clean one
        logger.info(f"Replacing {db_path} with clean database...")
        shutil.move(db_path, f'{db_path}.old')
        shutil.move(clean_db, db_path)
        
        logger.info("✓ Database rebuild complete!")
        logger.info(f"✓ Removed {duplicates:,} duplicate card entries")
        logger.info(f"✓ Backup preserved at: {backup_path}")
        
    except Exception as e:
        logger.error(f"Rebuild failed: {e}")
        logger.info(f"Original database preserved at: {backup_path}")
        raise


if __name__ == '__main__':
    main()
