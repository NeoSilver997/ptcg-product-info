"""
Import Pokemon TCG event and deck data from JSON files into SQLite database.

This script processes event_data/ directory containing tournament results and deck lists,
creating a normalized database with events, players, decks, and deck cards.

IMPROVED VERSION: Better duplicate prevention and data integrity checks.
"""

import sqlite3
import json
import os
from pathlib import Path
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class EventDataImporter:
    """Import event tournament data into SQLite database with duplicate prevention."""
    
    def __init__(self, db_path='ptcg_events.db', event_data_dir='event_data'):
        """
        Initialize the importer.
        
        Args:
            db_path: Path to SQLite database file
            event_data_dir: Directory containing event data folders
        """
        self.db_path = db_path
        self.event_data_dir = Path(event_data_dir)
        self.conn = None
        self.imported_events = set()  # Track imported events in this session
        
    def connect(self):
        """Connect to SQLite database."""
        self.conn = sqlite3.connect(self.db_path)
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.conn.execute("PRAGMA journal_mode = WAL")  # Better concurrency
        logger.info(f"Connected to database: {self.db_path}")
        
    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()
            logger.info("Database connection closed")
    
    def create_tables(self):
        """Create database tables with enhanced duplicate prevention."""
        cursor = self.conn.cursor()
        
        # Events table - prevent overwrites
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS events (
                event_id TEXT PRIMARY KEY,
                event_date DATE NOT NULL,
                event_title TEXT,
                event_host TEXT,
                event_address TEXT,
                event_location TEXT,
                event_url TEXT,
                import_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_modified TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Players table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS players (
                player_id TEXT PRIMARY KEY,
                player_name TEXT,
                player_area TEXT,
                first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Event results table - enhanced unique constraint
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS event_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id TEXT NOT NULL,
                player_id TEXT NOT NULL,
                rank TEXT NOT NULL,
                points TEXT,
                deck_id TEXT,
                FOREIGN KEY (event_id) REFERENCES events(event_id) ON DELETE CASCADE,
                FOREIGN KEY (player_id) REFERENCES players(player_id) ON DELETE CASCADE,
                UNIQUE(event_id, player_id, rank)
            )
        """)
        
        # Decks table - prevent overwrites
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS decks (
                deck_id TEXT PRIMARY KEY,
                deck_code TEXT,
                deck_url TEXT,
                event_id TEXT,
                player_id TEXT,
                rank TEXT,
                import_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_modified TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (event_id) REFERENCES events(event_id) ON DELETE CASCADE,
                FOREIGN KEY (player_id) REFERENCES players(player_id) ON DELETE CASCADE
            )
        """)
        
        # Deck cards table - enhanced unique constraint and data validation
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS deck_cards (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                deck_id TEXT NOT NULL,
                card_id TEXT,
                card_name TEXT NOT NULL,
                card_code TEXT,
                quantity INTEGER NOT NULL CHECK (quantity > 0),
                image_url TEXT,
                FOREIGN KEY (deck_id) REFERENCES decks(deck_id) ON DELETE CASCADE,
                UNIQUE(deck_id, card_name, card_code)
            )
        """)
        
        # Create indexes for performance
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_event_date ON events(event_date)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_event_results_event ON event_results(event_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_event_results_player ON event_results(player_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_decks_event ON decks(event_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_deck_cards_deck ON deck_cards(deck_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_deck_cards_card ON deck_cards(card_id)")
        
        self.conn.commit()
        logger.info("Database tables created successfully with duplicate prevention")
    
    def event_exists(self, event_id):
        """Check if event already exists in database."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT 1 FROM events WHERE event_id = ?", (event_id,))
        return cursor.fetchone() is not None
    
    def import_event(self, event_folder):
        """
        Import a single event from its folder with duplicate checking.
        
        Args:
            event_folder: Path to event folder containing event_info.json and deck files
        """
        event_info_path = event_folder / 'event_info.json'
        
        if not event_info_path.exists():
            logger.warning(f"No event_info.json found in {event_folder}")
            return
        
        try:
            # Read event info
            with open(event_info_path, 'r', encoding='utf-8') as f:
                event_data = json.load(f)
            
            event_id = event_data.get('event_id')
            if not event_id:
                logger.warning(f"No event_id in {event_info_path}")
                return
            
            # Check if already imported
            if self.event_exists(event_id):
                logger.info(f"Event {event_id} already exists, skipping")
                return
            
            # Check if already imported in this session
            if event_id in self.imported_events:
                logger.warning(f"Event {event_id} already imported in this session")
                return
            
            # Use transaction for atomic import
            with self.conn:
                # Insert event
                self._insert_event(event_data)
                
                # Insert results (players and rankings)
                for result in event_data.get('results', []):
                    self._insert_result(event_id, result)
                
                # Import deck files
                deck_files = list(event_folder.glob('deck_*.json'))
                for deck_file in deck_files:
                    self._import_deck(deck_file, event_id)
                
                # Mark as imported
                self.imported_events.add(event_id)
            
            logger.info(f"Imported event {event_id} with {len(event_data.get('results', []))} results and {len(deck_files)} decks")
            
        except Exception as e:
            logger.error(f"Error importing event from {event_folder}: {e}")
            raise
    
    def _insert_event(self, event_data):
        """Insert event record (only if not exists)."""
        cursor = self.conn.cursor()
        
        cursor.execute("""
            INSERT OR IGNORE INTO events 
            (event_id, event_date, event_title, event_host, event_address, event_location, event_url)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            event_data.get('event_id'),
            event_data.get('event_date'),
            event_data.get('event_title', ''),
            event_data.get('event_host', ''),
            event_data.get('event_address', ''),
            event_data.get('event_location', ''),
            event_data.get('event_url', '')
        ))
        
        # Update last_modified if event already existed
        if cursor.rowcount == 0:  # Event already existed
            cursor.execute("""
                UPDATE events SET last_modified = CURRENT_TIMESTAMP
                WHERE event_id = ?
            """, (event_data.get('event_id'),))
    
    def _insert_result(self, event_id, result):
        """Insert event result (player ranking) with duplicate prevention."""
        cursor = self.conn.cursor()
        
        player_id = result.get('player_id')
        if not player_id:
            return
        
        # Insert or update player
        cursor.execute("""
            INSERT INTO players (player_id, player_name, player_area)
            VALUES (?, ?, ?)
            ON CONFLICT(player_id) DO UPDATE SET
                player_name = excluded.player_name,
                player_area = excluded.player_area,
                last_seen = CURRENT_TIMESTAMP
        """, (
            player_id,
            result.get('player_name', ''),
            result.get('player_area', '')
        ))
        
        # Insert event result (will be ignored if duplicate)
        cursor.execute("""
            INSERT OR IGNORE INTO event_results 
            (event_id, player_id, rank, points, deck_id)
            VALUES (?, ?, ?, ?, ?)
        """, (
            event_id,
            player_id,
            result.get('rank', ''),
            result.get('points', ''),
            result.get('deck_id', '')
        ))
    
    def _import_deck(self, deck_file, event_id):
        """Import deck data from JSON file with duplicate prevention."""
        try:
            with open(deck_file, 'r', encoding='utf-8') as f:
                deck_data = json.load(f)
            
            deck_id = deck_data.get('deck_id')
            if not deck_id:
                logger.warning(f"No deck_id in {deck_file}")
                return
            
            # Extract rank and player from filename or event results
            rank = self._extract_rank_from_filename(deck_file.name)
            player_id = self._get_player_for_deck(event_id, deck_id)
            
            # Insert deck (only if not exists)
            cursor = self.conn.cursor()
            cursor.execute("""
                INSERT OR IGNORE INTO decks 
                (deck_id, deck_code, deck_url, event_id, player_id, rank)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                deck_id,
                deck_data.get('deck_code', ''),
                deck_data.get('deck_url', ''),
                event_id,
                player_id,
                rank
            ))
            
            # Only insert cards if deck was actually inserted (not ignored)
            if cursor.rowcount > 0:
                # Insert deck cards with validation
                for card in deck_data.get('cards', []):
                    self._insert_deck_card(deck_id, card)
            else:
                logger.debug(f"Deck {deck_id} already exists, skipping card import")
            
        except Exception as e:
            logger.error(f"Error importing deck from {deck_file}: {e}")
            raise
    
    def _insert_deck_card(self, deck_id, card):
        """Insert deck card with duplicate prevention and validation."""
        cursor = self.conn.cursor()
        
        # Validate card data
        card_name = card.get('card_name', '').strip()
        if not card_name:
            logger.warning(f"Skipping card with empty name in deck {deck_id}")
            return
        
        quantity = card.get('quantity', 1)
        if not isinstance(quantity, int) or quantity <= 0:
            logger.warning(f"Invalid quantity {quantity} for card {card_name} in deck {deck_id}, setting to 1")
            quantity = 1
        
        # Insert card (will be ignored if duplicate)
        cursor.execute("""
            INSERT OR IGNORE INTO deck_cards 
            (deck_id, card_id, card_name, card_code, quantity, image_url)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            deck_id,
            card.get('card_id', ''),
            card_name,
            card.get('card_code', ''),
            quantity,
            card.get('image_url', '')
        ))
        
        # If card was ignored (duplicate), update quantity instead
        if cursor.rowcount == 0:
            cursor.execute("""
                UPDATE deck_cards 
                SET quantity = quantity + ?
                WHERE deck_id = ? AND card_name = ? AND card_code = ?
            """, (quantity, deck_id, card_name, card.get('card_code', '')))
    
    def _extract_rank_from_filename(self, filename):
        """Extract rank from deck filename (e.g., deck_1st_xxx.json -> 1位)."""
        rank_map = {
            '1st': '1位',
            '2nd': '2位',
            '3rd': '3位',
            '5th': '5位',
            '9th': '9位'
        }
        
        for rank_en, rank_jp in rank_map.items():
            if rank_en in filename:
                return rank_jp
        
        return ''
    
    def _get_player_for_deck(self, event_id, deck_id):
        """Get player_id associated with a deck from event results."""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT player_id FROM event_results 
            WHERE event_id = ? AND deck_id = ?
        """, (event_id, deck_id))
        
        result = cursor.fetchone()
        return result[0] if result else None
    
    def import_all_events(self):
        """Import all events from event_data directory with progress tracking."""
        if not self.event_data_dir.exists():
            logger.error(f"Event data directory not found: {self.event_data_dir}")
            return
        
        # Get all event folders
        event_folders = [d for d in self.event_data_dir.iterdir() if d.is_dir() and d.name.startswith('event_')]
        logger.info(f"Found {len(event_folders)} event folders")
        
        # Import each event
        imported_count = 0
        skipped_count = 0
        error_count = 0
        
        for event_folder in sorted(event_folders):
            try:
                if self.event_exists(event_folder.name.split('_', 1)[1] if '_' in event_folder.name else event_folder.name):
                    logger.debug(f"Skipping already imported event: {event_folder.name}")
                    skipped_count += 1
                else:
                    self.import_event(event_folder)
                    imported_count += 1
            except Exception as e:
                logger.error(f"Failed to import {event_folder.name}: {e}")
                error_count += 1
        
        logger.info(f"Import complete: {imported_count} imported, {skipped_count} skipped, {error_count} errors")
    
    def validate_data_integrity(self):
        """Validate data integrity after import."""
        cursor = self.conn.cursor()
        issues = []
        
        # Check for decks without 60 cards
        cursor.execute("""
            SELECT d.deck_id, d.rank, SUM(dc.quantity) as total_cards
            FROM decks d
            LEFT JOIN deck_cards dc ON d.deck_id = dc.deck_id
            GROUP BY d.deck_id
            HAVING total_cards != 60 OR total_cards IS NULL
        """)
        
        invalid_decks = cursor.fetchall()
        if invalid_decks:
            issues.append(f"Found {len(invalid_decks)} decks with invalid card counts")
            for deck in invalid_decks[:5]:  # Show first 5
                issues.append(f"  Deck {deck[0]} (Rank: {deck[1]}): {deck[2] or 0} cards")
        
        # Check for orphaned records
        cursor.execute("SELECT COUNT(*) FROM event_results WHERE event_id NOT IN (SELECT event_id FROM events)")
        orphaned_results = cursor.fetchone()[0]
        if orphaned_results > 0:
            issues.append(f"Found {orphaned_results} orphaned event_results")
        
        cursor.execute("SELECT COUNT(*) FROM decks WHERE event_id NOT IN (SELECT event_id FROM events)")
        orphaned_decks = cursor.fetchone()[0]
        if orphaned_decks > 0:
            issues.append(f"Found {orphaned_decks} orphaned decks")
        
        cursor.execute("SELECT COUNT(*) FROM deck_cards WHERE deck_id NOT IN (SELECT deck_id FROM decks)")
        orphaned_cards = cursor.fetchone()[0]
        if orphaned_cards > 0:
            issues.append(f"Found {orphaned_cards} orphaned deck_cards")
        
        if issues:
            logger.warning("Data integrity issues found:")
            for issue in issues:
                logger.warning(f"  {issue}")
        else:
            logger.info("✅ Data integrity validation passed")
        
        return issues
    
    def get_statistics(self):
        """Get database statistics."""
        cursor = self.conn.cursor()
        
        stats = {}
        
        # Count events
        cursor.execute("SELECT COUNT(*) FROM events")
        stats['total_events'] = cursor.fetchone()[0]
        
        # Count players
        cursor.execute("SELECT COUNT(*) FROM players")
        stats['total_players'] = cursor.fetchone()[0]
        
        # Count decks
        cursor.execute("SELECT COUNT(*) FROM decks")
        stats['total_decks'] = cursor.fetchone()[0]
        
        # Count cards
        cursor.execute("SELECT COUNT(*) FROM deck_cards")
        stats['total_card_entries'] = cursor.fetchone()[0]
        
        # Date range
        cursor.execute("SELECT MIN(event_date), MAX(event_date) FROM events")
        date_range = cursor.fetchone()
        stats['earliest_event'] = date_range[0]
        stats['latest_event'] = date_range[1]
        
        # Duplicate check
        cursor.execute("""
            SELECT COUNT(*) FROM (
                SELECT deck_id, card_name, card_code, COUNT(*) as cnt
                FROM deck_cards
                GROUP BY deck_id, card_name, card_code
                HAVING cnt > 1
            )
        """)
        stats['duplicate_card_entries'] = cursor.fetchone()[0]
        
        return stats


def main():
    """Main execution function with enhanced error handling."""
    logger.info("Starting improved event data import with duplicate prevention")
    
    # Initialize importer
    importer = EventDataImporter(
        db_path='ptcg_events.db',
        event_data_dir='event_data'
    )
    
    try:
        # Connect and create tables
        importer.connect()
        importer.create_tables()
        
        # Import all events
        importer.import_all_events()
        
        # Validate data integrity
        integrity_issues = importer.validate_data_integrity()
        
        # Show statistics
        stats = importer.get_statistics()
        logger.info("=" * 60)
        logger.info("DATABASE STATISTICS")
        logger.info("=" * 60)
        logger.info(f"Total Events: {stats['total_events']}")
        logger.info(f"Total Players: {stats['total_players']}")
        logger.info(f"Total Decks: {stats['total_decks']}")
        logger.info(f"Total Card Entries: {stats['total_card_entries']}")
        logger.info(f"Date Range: {stats['earliest_event']} to {stats['latest_event']}")
        logger.info(f"Duplicate Card Entries: {stats['duplicate_card_entries']}")
        logger.info("=" * 60)
        
        if integrity_issues:
            logger.warning("⚠️  Data integrity issues detected - consider running cleanup scripts")
        else:
            logger.info("✅ All data integrity checks passed")
        
    except Exception as e:
        logger.error(f"Import failed: {e}")
        raise
    finally:
        importer.close()
    
    logger.info("Import process completed")


if __name__ == '__main__':
    main()
    
    def import_event(self, event_folder):
        """
        Import a single event from its folder.
        
        Args:
            event_folder: Path to event folder containing event_info.json and deck files
        """
        event_info_path = event_folder / 'event_info.json'
        
        if not event_info_path.exists():
            logger.warning(f"No event_info.json found in {event_folder}")
            return
        
        try:
            # Read event info
            with open(event_info_path, 'r', encoding='utf-8') as f:
                event_data = json.load(f)
            
            event_id = event_data.get('event_id')
            if not event_id:
                logger.warning(f"No event_id in {event_info_path}")
                return
            
            # Insert event
            self._insert_event(event_data)
            
            # Insert results (players and rankings)
            for result in event_data.get('results', []):
                self._insert_result(event_id, result)
            
            # Import deck files
            deck_files = list(event_folder.glob('deck_*.json'))
            for deck_file in deck_files:
                self._import_deck(deck_file, event_id)
            
            logger.info(f"Imported event {event_id} with {len(event_data.get('results', []))} results and {len(deck_files)} decks")
            
        except Exception as e:
            logger.error(f"Error importing event from {event_folder}: {e}")
            raise
    
    def _insert_event(self, event_data):
        """Insert event record."""
        cursor = self.conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO events 
            (event_id, event_date, event_title, event_host, event_address, event_location, event_url)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            event_data.get('event_id'),
            event_data.get('event_date'),
            event_data.get('event_title', ''),
            event_data.get('event_host', ''),
            event_data.get('event_address', ''),
            event_data.get('event_location', ''),
            event_data.get('event_url', '')
        ))
        
        self.conn.commit()
    
    def _insert_result(self, event_id, result):
        """Insert event result (player ranking)."""
        cursor = self.conn.cursor()
        
        player_id = result.get('player_id')
        if not player_id:
            return
        
        # Insert or update player
        cursor.execute("""
            INSERT INTO players (player_id, player_name, player_area)
            VALUES (?, ?, ?)
            ON CONFLICT(player_id) DO UPDATE SET
                player_name = excluded.player_name,
                player_area = excluded.player_area,
                last_seen = CURRENT_TIMESTAMP
        """, (
            player_id,
            result.get('player_name', ''),
            result.get('player_area', '')
        ))
        
        # Insert event result
        cursor.execute("""
            INSERT OR IGNORE INTO event_results 
            (event_id, player_id, rank, points, deck_id)
            VALUES (?, ?, ?, ?, ?)
        """, (
            event_id,
            player_id,
            result.get('rank', ''),
            result.get('points', ''),
            result.get('deck_id', '')
        ))
        
        self.conn.commit()
    
    def _import_deck(self, deck_file, event_id):
        """Import deck data from JSON file."""
        try:
            with open(deck_file, 'r', encoding='utf-8') as f:
                deck_data = json.load(f)
            
            deck_id = deck_data.get('deck_id')
            if not deck_id:
                logger.warning(f"No deck_id in {deck_file}")
                return
            
            # Extract rank and player from filename or event results
            rank = self._extract_rank_from_filename(deck_file.name)
            player_id = self._get_player_for_deck(event_id, deck_id)
            
            # Insert deck
            cursor = self.conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO decks 
                (deck_id, deck_code, deck_url, event_id, player_id, rank)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                deck_id,
                deck_data.get('deck_code', ''),
                deck_data.get('deck_url', ''),
                event_id,
                player_id,
                rank
            ))
            
            # Insert deck cards
            for card in deck_data.get('cards', []):
                cursor.execute("""
                    INSERT OR IGNORE INTO deck_cards 
                    (deck_id, card_id, card_name, card_code, quantity, image_url)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    deck_id,
                    card.get('card_id', ''),
                    card.get('card_name', ''),
                    card.get('card_code', ''),
                    card.get('quantity', 1),
                    card.get('image_url', '')
                ))
            
            self.conn.commit()
            
        except Exception as e:
            logger.error(f"Error importing deck from {deck_file}: {e}")
    
    def _extract_rank_from_filename(self, filename):
        """Extract rank from deck filename (e.g., deck_1st_xxx.json -> 1位)."""
        rank_map = {
            '1st': '1位',
            '2nd': '2位',
            '3rd': '3位',
            '5th': '5位',
            '9th': '9位'
        }
        
        for rank_en, rank_jp in rank_map.items():
            if rank_en in filename:
                return rank_jp
        
        return ''
    
    def _get_player_for_deck(self, event_id, deck_id):
        """Get player_id associated with a deck from event results."""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT player_id FROM event_results 
            WHERE event_id = ? AND deck_id = ?
        """, (event_id, deck_id))
        
        result = cursor.fetchone()
        return result[0] if result else None
    
    def import_all_events(self):
        """Import all events from event_data directory with progress tracking."""
        if not self.event_data_dir.exists():
            logger.error(f"Event data directory not found: {self.event_data_dir}")
            return
        
        # Get all event folders
        event_folders = [d for d in self.event_data_dir.iterdir() if d.is_dir() and d.name.startswith('event_')]
        logger.info(f"Found {len(event_folders)} event folders")
        
        # Import each event
        imported_count = 0
        skipped_count = 0
        error_count = 0
        
        for event_folder in sorted(event_folders):
            try:
                # Extract event_id from folder name
                event_id = event_folder.name.split('_', 1)[1] if '_' in event_folder.name else event_folder.name
                if self.event_exists(event_id):
                    logger.debug(f"Skipping already imported event: {event_folder.name}")
                    skipped_count += 1
                else:
                    self.import_event(event_folder)
                    imported_count += 1
            except Exception as e:
                logger.error(f"Failed to import {event_folder.name}: {e}")
                error_count += 1
        
        logger.info(f"Import complete: {imported_count} imported, {skipped_count} skipped, {error_count} errors")
    
    def get_statistics(self):
        """Get database statistics."""
        cursor = self.conn.cursor()
        
        stats = {}
        
        # Count events
        cursor.execute("SELECT COUNT(*) FROM events")
        stats['total_events'] = cursor.fetchone()[0]
        
        # Count players
        cursor.execute("SELECT COUNT(*) FROM players")
        stats['total_players'] = cursor.fetchone()[0]
        
        # Count decks
        cursor.execute("SELECT COUNT(*) FROM decks")
        stats['total_decks'] = cursor.fetchone()[0]
        
        # Count cards
        cursor.execute("SELECT COUNT(*) FROM deck_cards")
        stats['total_card_entries'] = cursor.fetchone()[0]
        
        # Date range
        cursor.execute("SELECT MIN(event_date), MAX(event_date) FROM events")
        date_range = cursor.fetchone()
        stats['earliest_event'] = date_range[0]
        stats['latest_event'] = date_range[1]
        
        return stats


def main():
    """Main execution function."""
    logger.info("Starting event data import")
    
    # Initialize importer
    importer = EventDataImporter(
        db_path='ptcg_events.db',
        event_data_dir='event_data'
    )
    
    try:
        # Connect and create tables
        importer.connect()
        importer.create_tables()
        
        # Import all events
        importer.import_all_events()
        
        # Show statistics
        stats = importer.get_statistics()
        logger.info("=" * 50)
        logger.info("DATABASE STATISTICS")
        logger.info("=" * 50)
        logger.info(f"Total Events: {stats['total_events']}")
        logger.info(f"Total Players: {stats['total_players']}")
        logger.info(f"Total Decks: {stats['total_decks']}")
        logger.info(f"Total Card Entries: {stats['total_card_entries']}")
        logger.info(f"Date Range: {stats['earliest_event']} to {stats['latest_event']}")
        logger.info("=" * 50)
        
    except Exception as e:
        logger.error(f"Import failed: {e}")
        raise
    finally:
        importer.close()
    
    logger.info("Import process completed")


if __name__ == '__main__':
    main()
