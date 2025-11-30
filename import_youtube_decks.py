#!/usr/bin/env python3
"""
Import YouTube video deck codes into the PTCG event database.

This script links deck codes found in YouTube videos to the existing
deck data in the database, and can also scrape new decks from the
official Pokemon TCG website if they are referenced in videos.
"""

import sqlite3
import logging
import time
from datetime import datetime
from typing import List, Dict, Optional, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class YouTubeDeckImporter:
    """
    Import and link deck data from YouTube videos.
    
    Integrates YouTube video deck codes with the existing tournament
    deck database structure.
    """
    
    def __init__(self, db_path: str = 'ptcg_events.db'):
        """
        Initialize the importer.
        
        Args:
            db_path: Path to the SQLite database file.
        """
        self.db_path = db_path
        self.conn = None
    
    def connect(self) -> None:
        """Connect to the database."""
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        logger.info(f"Connected to database: {self.db_path}")
    
    def close(self) -> None:
        """Close the database connection."""
        if self.conn:
            self.conn.close()
            logger.info("Database connection closed")
    
    def get_unlinked_deck_codes(self) -> List[Dict]:
        """
        Get YouTube videos with deck codes that are not yet linked to decks.
        
        Returns:
            List of dictionaries with video info and deck codes.
        """
        cursor = self.conn.cursor()
        
        query = """
            SELECT yv.video_id, yv.channel_name, yv.title, yv.deck_code,
                   yv.published_at, yv.view_count
            FROM youtube_videos yv
            LEFT JOIN youtube_deck_links ydl ON yv.video_id = ydl.video_id
                AND ydl.deck_id IS NOT NULL
            WHERE yv.deck_code IS NOT NULL
                AND ydl.id IS NULL
            ORDER BY yv.published_at DESC
        """
        
        cursor.execute(query)
        rows = cursor.fetchall()
        
        return [dict(row) for row in rows]
    
    def link_existing_decks(self) -> int:
        """
        Link YouTube video deck codes to existing decks in the database.
        
        Matches deck codes from YouTube videos with decks already in the
        decks table (from tournament events).
        
        Returns:
            Number of new links created.
        """
        cursor = self.conn.cursor()
        links_created = 0
        
        # Find videos with deck codes that match existing decks
        query = """
            SELECT yv.video_id, yv.deck_code, d.deck_id
            FROM youtube_videos yv
            JOIN decks d ON (yv.deck_code = d.deck_id OR yv.deck_code = d.deck_code)
            LEFT JOIN youtube_deck_links ydl ON yv.video_id = ydl.video_id
                AND yv.deck_code = ydl.deck_code
            WHERE yv.deck_code IS NOT NULL
                AND ydl.id IS NULL
        """
        
        cursor.execute(query)
        matches = cursor.fetchall()
        
        for match in matches:
            video_id, deck_code, deck_id = match
            
            cursor.execute("""
                INSERT OR REPLACE INTO youtube_deck_links
                (video_id, deck_id, deck_code, source_type)
                VALUES (?, ?, ?, 'youtube')
            """, (video_id, deck_id, deck_code))
            links_created += 1
            
            logger.info(f"Linked video {video_id} to deck {deck_id}")
        
        self.conn.commit()
        logger.info(f"Created {links_created} new deck links")
        return links_created
    
    def import_deck_from_youtube(
        self,
        video_id: str,
        deck_code: str,
        deck_scraper=None
    ) -> Optional[str]:
        """
        Import a deck from YouTube video by scraping the deck code.
        
        Uses the EventDeckScraper to fetch deck details from the official
        Pokemon TCG website.
        
        Args:
            video_id: YouTube video ID.
            deck_code: Pokemon TCG deck code.
            deck_scraper: Optional EventDeckScraper instance.
        
        Returns:
            Deck ID if successful, None otherwise.
        """
        cursor = self.conn.cursor()
        
        # Check if deck already exists
        cursor.execute(
            "SELECT deck_id FROM decks WHERE deck_id = ? OR deck_code = ?",
            (deck_code, deck_code)
        )
        existing = cursor.fetchone()
        
        if existing:
            logger.info(f"Deck {deck_code} already exists")
            return existing[0]
        
        # Try to scrape deck from official site
        if deck_scraper is None:
            try:
                from event_scraper_enhanced import EventDeckScraper
                deck_scraper = EventDeckScraper()
            except ImportError:
                logger.warning("EventDeckScraper not available")
                return None
        
        try:
            deck_data = deck_scraper.scrape_deck_by_id(deck_code)
            
            if not deck_data.get('cards'):
                logger.warning(f"No cards found for deck {deck_code}")
                return None
            
            # Get video info for event_id proxy
            cursor.execute(
                "SELECT channel_id, published_at FROM youtube_videos WHERE video_id = ?",
                (video_id,)
            )
            video_row = cursor.fetchone()
            
            # Create synthetic event_id from video info
            event_id = f"youtube_{video_id}"
            
            # Insert deck into database
            cursor.execute("""
                INSERT OR IGNORE INTO decks
                (deck_id, deck_code, deck_url, event_id)
                VALUES (?, ?, ?, ?)
            """, (
                deck_code,
                deck_data.get('deck_code', deck_code),
                deck_data.get('deck_url', ''),
                event_id
            ))
            
            # Only insert cards if deck was actually inserted
            if cursor.rowcount > 0:
                for card in deck_data.get('cards', []):
                    card_name = card.get('card_name', '').strip()
                    if not card_name:
                        continue
                    
                    cursor.execute("""
                        INSERT OR IGNORE INTO deck_cards
                        (deck_id, card_id, card_name, card_code, quantity, image_url)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (
                        deck_code,
                        card.get('card_id', ''),
                        card_name,
                        card.get('card_code', ''),
                        card.get('quantity', 1),
                        card.get('image_url', '')
                    ))
                
                # Link video to deck
                cursor.execute("""
                    INSERT OR REPLACE INTO youtube_deck_links
                    (video_id, deck_id, deck_code, source_type)
                    VALUES (?, ?, ?, 'youtube_imported')
                """, (video_id, deck_code, deck_code))
                
                self.conn.commit()
                
                total_cards = sum(c.get('quantity', 1) for c in deck_data.get('cards', []))
                logger.info(f"Imported deck {deck_code} with {total_cards} cards")
                
                return deck_code
            else:
                logger.info(f"Deck {deck_code} already existed")
                return deck_code
            
        except Exception as e:
            logger.error(f"Error importing deck {deck_code}: {e}")
            return None
    
    def import_all_youtube_decks(
        self,
        max_imports: int = 50,
        delay_seconds: float = 2.0
    ) -> Dict:
        """
        Import all unlinked deck codes from YouTube videos.
        
        Args:
            max_imports: Maximum number of decks to import.
            delay_seconds: Delay between deck scrapes (be respectful to server).
        
        Returns:
            Dictionary with import statistics.
        """
        stats = {
            'total_unlinked': 0,
            'imported': 0,
            'linked_existing': 0,
            'failed': 0,
            'errors': []
        }
        
        # First, link any existing decks
        stats['linked_existing'] = self.link_existing_decks()
        
        # Get remaining unlinked deck codes
        unlinked = self.get_unlinked_deck_codes()
        stats['total_unlinked'] = len(unlinked)
        
        if not unlinked:
            logger.info("No unlinked deck codes to import")
            return stats
        
        logger.info(f"Found {len(unlinked)} unlinked deck codes")
        
        try:
            from event_scraper_enhanced import EventDeckScraper
            deck_scraper = EventDeckScraper()
        except ImportError:
            logger.error("EventDeckScraper not available")
            stats['errors'].append("EventDeckScraper not available")
            return stats
        
        # Import decks
        for i, item in enumerate(unlinked[:max_imports]):
            video_id = item['video_id']
            deck_code = item['deck_code']
            
            logger.info(f"[{i+1}/{min(len(unlinked), max_imports)}] Importing deck {deck_code}")
            
            result = self.import_deck_from_youtube(video_id, deck_code, deck_scraper)
            
            if result:
                stats['imported'] += 1
            else:
                stats['failed'] += 1
            
            # Respectful delay
            if i < len(unlinked) - 1:
                time.sleep(delay_seconds)
        
        return stats
    
    def get_youtube_deck_summary(self) -> Dict:
        """
        Get summary of YouTube-related deck data.
        
        Returns:
            Dictionary with summary statistics.
        """
        cursor = self.conn.cursor()
        summary = {}
        
        # Total YouTube videos
        cursor.execute("SELECT COUNT(*) FROM youtube_videos")
        summary['total_videos'] = cursor.fetchone()[0]
        
        # Videos with deck codes
        cursor.execute("SELECT COUNT(*) FROM youtube_videos WHERE deck_code IS NOT NULL")
        summary['videos_with_decks'] = cursor.fetchone()[0]
        
        # Linked decks
        cursor.execute("SELECT COUNT(*) FROM youtube_deck_links WHERE deck_id IS NOT NULL")
        summary['linked_decks'] = cursor.fetchone()[0]
        
        # Decks imported from YouTube
        cursor.execute("""
            SELECT COUNT(*) FROM youtube_deck_links 
            WHERE source_type = 'youtube_imported'
        """)
        summary['imported_decks'] = cursor.fetchone()[0]
        
        # Unlinked deck codes
        cursor.execute("""
            SELECT COUNT(*) FROM youtube_videos yv
            LEFT JOIN youtube_deck_links ydl ON yv.video_id = ydl.video_id
                AND ydl.deck_id IS NOT NULL
            WHERE yv.deck_code IS NOT NULL
                AND ydl.id IS NULL
        """)
        summary['unlinked_deck_codes'] = cursor.fetchone()[0]
        
        # Top channels with deck videos
        cursor.execute("""
            SELECT channel_name, COUNT(*) as video_count
            FROM youtube_videos
            WHERE deck_code IS NOT NULL
            GROUP BY channel_id
            ORDER BY video_count DESC
            LIMIT 10
        """)
        summary['top_channels'] = [
            {'channel': row[0], 'deck_videos': row[1]}
            for row in cursor.fetchall()
        ]
        
        return summary


def main():
    """Main function for testing the importer."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Import YouTube deck data')
    parser.add_argument('--db', default='ptcg_events.db', help='Database path')
    parser.add_argument('--link-existing', action='store_true', 
                       help='Link YouTube videos to existing decks')
    parser.add_argument('--import-decks', action='store_true',
                       help='Import new decks from YouTube video codes')
    parser.add_argument('--max-imports', type=int, default=50,
                       help='Maximum decks to import')
    parser.add_argument('--summary', action='store_true',
                       help='Show summary statistics')
    
    args = parser.parse_args()
    
    importer = YouTubeDeckImporter(db_path=args.db)
    
    try:
        importer.connect()
        
        if args.summary:
            summary = importer.get_youtube_deck_summary()
            print("\n" + "=" * 60)
            print("YOUTUBE DECK SUMMARY")
            print("=" * 60)
            for key, value in summary.items():
                if key == 'top_channels':
                    print("\nTop Channels with Deck Videos:")
                    for ch in value:
                        print(f"  - {ch['channel']}: {ch['deck_videos']} videos")
                else:
                    print(f"{key}: {value}")
            print("=" * 60)
            return
        
        if args.link_existing:
            links = importer.link_existing_decks()
            print(f"Created {links} new links to existing decks")
        
        if args.import_decks:
            stats = importer.import_all_youtube_decks(max_imports=args.max_imports)
            print("\n" + "=" * 60)
            print("IMPORT RESULTS")
            print("=" * 60)
            print(f"Total unlinked: {stats['total_unlinked']}")
            print(f"Linked existing: {stats['linked_existing']}")
            print(f"Imported: {stats['imported']}")
            print(f"Failed: {stats['failed']}")
            if stats['errors']:
                print(f"Errors: {', '.join(stats['errors'])}")
            print("=" * 60)
        
    finally:
        importer.close()


if __name__ == "__main__":
    main()
