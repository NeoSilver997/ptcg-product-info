"""
Enhanced card mapping using online sources.

This script attempts to map unmapped cards by:
1. Using the official Pokemon Card website API
2. Fetching card data from card_code_cache.json
3. Cross-referencing with web card IDs
"""

import sqlite3
import json
import requests
import time
from pathlib import Path
import logging
from typing import Dict, List, Optional

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class OnlineCardMapper:
    """Map cards using online sources and cached data."""
    
    def __init__(self, 
                 event_db='ptcg_events.db',
                 main_db=r'c:\AI_Server\Coding\PokemonDBByjules\PTCG_CardDB_Tc\pokemon_cards.db',
                 cache_file='card_code_cache.json'):
        self.event_db_path = event_db
        self.main_db_path = main_db
        self.cache_file = cache_file
        self.event_conn = None
        self.main_conn = None
        self.card_cache = {}
        
    def connect(self):
        """Connect to databases."""
        self.event_conn = sqlite3.connect(self.event_db_path)
        self.event_conn.row_factory = sqlite3.Row
        self.main_conn = sqlite3.connect(self.main_db_path)
        self.main_conn.row_factory = sqlite3.Row
        logger.info("Connected to databases")
        
    def close(self):
        """Close connections."""
        if self.event_conn:
            self.event_conn.close()
        if self.main_conn:
            self.main_conn.close()
        logger.info("Closed database connections")
    
    def load_card_cache(self):
        """Load card code cache from JSON file."""
        if not Path(self.cache_file).exists():
            logger.warning(f"Cache file not found: {self.cache_file}")
            return {}
        
        try:
            with open(self.cache_file, 'r', encoding='utf-8') as f:
                cache = json.load(f)
            logger.info(f"Loaded {len(cache)} cards from cache")
            return cache
        except Exception as e:
            logger.error(f"Error loading cache: {e}")
            return {}
    
    def get_unmapped_cards(self) -> List[Dict]:
        """Get cards that haven't been mapped yet."""
        cursor = self.event_conn.cursor()
        cursor.execute("""
            SELECT DISTINCT
                dc.card_id,
                dc.card_name,
                dc.card_code,
                COUNT(dc.deck_id) as usage_count
            FROM deck_cards dc
            LEFT JOIN card_mappings cm ON dc.card_id = cm.event_card_id
            WHERE cm.event_card_id IS NULL
            AND dc.card_code != ''
            AND dc.card_code != 'ACE SPEC'
            GROUP BY dc.card_id
            ORDER BY usage_count DESC
        """)
        
        unmapped = [dict(row) for row in cursor.fetchall()]
        logger.info(f"Found {len(unmapped)} unmapped cards")
        return unmapped
    
    def map_by_card_id(self, event_card_id: str, card_code: str) -> Optional[Dict]:
        """Try to map using card_id from event database."""
        # Check if card_id exists in main database as web_card_id
        cursor = self.main_conn.cursor()
        cursor.execute("""
            SELECT id, name, collector_number, web_card_id, expansion_id
            FROM cards
            WHERE web_card_id = ?
        """, (event_card_id,))
        
        result = cursor.fetchone()
        if result:
            return dict(result)
        return None
    
    def map_by_cache(self, card_code: str, card_name: str) -> Optional[Dict]:
        """Try to map using card_code_cache.json."""
        if not self.card_cache:
            self.card_cache = self.load_card_cache()
        
        # Look for card in cache by code
        for cached_card in self.card_cache.values():
            if isinstance(cached_card, dict):
                cached_code = cached_card.get('card_code', '')
                if cached_code == card_code:
                    # Try to find in main database by card name or other attributes
                    return self.find_in_main_db_by_attributes(cached_card)
        
        return None
    
    def find_in_main_db_by_attributes(self, cached_card: Dict) -> Optional[Dict]:
        """Find card in main database using cached attributes."""
        cursor = self.main_conn.cursor()
        
        # Try by web_card_id if available
        if 'card_id' in cached_card:
            cursor.execute("""
                SELECT id, name, collector_number, web_card_id
                FROM cards
                WHERE web_card_id = ?
            """, (cached_card['card_id'],))
            result = cursor.fetchone()
            if result:
                return dict(result)
        
        return None
    
    def map_by_name_similarity(self, japanese_name: str) -> List[Dict]:
        """Find similar cards by name (fuzzy matching)."""
        cursor = self.main_conn.cursor()
        
        # Try exact substring match
        cursor.execute("""
            SELECT id, name, collector_number, web_card_id
            FROM cards
            WHERE name LIKE ?
            LIMIT 5
        """, (f'%{japanese_name[:3]}%',))
        
        results = [dict(row) for row in cursor.fetchall()]
        return results
    
    def fetch_card_from_api(self, card_id: str) -> Optional[Dict]:
        """Fetch card data from Pokemon Card API."""
        # Note: This would require the actual API endpoint
        # Placeholder for demonstration
        logger.debug(f"Would fetch card {card_id} from API")
        return None
    
    def create_new_mappings(self, unmapped_cards: List[Dict]) -> List[Dict]:
        """Create new mappings for unmapped cards."""
        new_mappings = []
        mapped_count = 0
        
        for idx, card in enumerate(unmapped_cards):
            if idx % 50 == 0:
                logger.info(f"Processing {idx}/{len(unmapped_cards)}")
            
            card_id = card['card_id']
            card_name = card['card_name']
            card_code = card['card_code']
            
            main_card = None
            match_method = None
            
            # Method 1: Try mapping by card_id (as web_card_id)
            main_card = self.map_by_card_id(card_id, card_code)
            if main_card:
                match_method = 'card_id_match'
                mapped_count += 1
            
            # Method 2: Try mapping using cache
            if not main_card:
                main_card = self.map_by_cache(card_code, card_name)
                if main_card:
                    match_method = 'cache_match'
                    mapped_count += 1
            
            # Method 3: Try API (if available)
            if not main_card:
                main_card = self.fetch_card_from_api(card_id)
                if main_card:
                    match_method = 'api_match'
                    mapped_count += 1
            
            # Store mapping if found
            if main_card:
                # Get expansion code
                expansion_code = self.get_expansion_code(main_card['expansion_id']) if 'expansion_id' in main_card else ''
                
                new_mappings.append({
                    'event_card_id': card_id,
                    'event_card_name': card_name,
                    'event_card_code': card_code,
                    'main_card_id': main_card['id'],
                    'main_card_name': main_card['name'],
                    'main_collector_number': main_card.get('collector_number', ''),
                    'main_expansion_code': expansion_code,
                    'match_confidence': 'medium',
                    'match_method': match_method
                })
        
        logger.info(f"Created {mapped_count} new mappings from {len(unmapped_cards)} unmapped cards")
        return new_mappings
    
    def get_expansion_code(self, expansion_id: int) -> str:
        """Get expansion code from expansion_id."""
        cursor = self.main_conn.cursor()
        cursor.execute("SELECT code FROM expansions WHERE id = ?", (expansion_id,))
        result = cursor.fetchone()
        return result['code'] if result else ''
    
    def save_new_mappings(self, mappings: List[Dict]):
        """Save new mappings to database."""
        if not mappings:
            logger.info("No new mappings to save")
            return
        
        cursor = self.event_conn.cursor()
        
        # Add match_method column if not exists
        cursor.execute("""
            SELECT COUNT(*) FROM pragma_table_info('card_mappings') 
            WHERE name='match_method'
        """)
        
        if cursor.fetchone()[0] == 0:
            cursor.execute("""
                ALTER TABLE card_mappings 
                ADD COLUMN match_method TEXT
            """)
            self.event_conn.commit()
        
        # Insert new mappings
        cursor.executemany("""
            INSERT OR IGNORE INTO card_mappings (
                event_card_id, event_card_name, event_card_code,
                main_card_id, main_card_name, main_collector_number,
                main_expansion_code, match_confidence, match_method
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [
            (
                m['event_card_id'], m['event_card_name'], m['event_card_code'],
                m['main_card_id'], m['main_card_name'], m['main_collector_number'],
                m['main_expansion_code'], m['match_confidence'], m.get('match_method', 'online')
            )
            for m in mappings
        ])
        
        self.event_conn.commit()
        logger.info(f"Saved {len(mappings)} new mappings")
    
    def export_unmapped_cards(self, output_file='exports/unmapped_cards.json'):
        """Export unmapped cards for manual review."""
        unmapped = self.get_unmapped_cards()
        
        # Add more details
        for card in unmapped:
            # Parse card code
            if card['card_code'] and ' ' in card['card_code']:
                parts = card['card_code'].split()
                card['expansion'] = parts[0]
                card['number'] = parts[1].split('/')[0] if '/' in parts[1] else parts[1]
        
        Path(output_file).parent.mkdir(exist_ok=True)
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(unmapped, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Exported {len(unmapped)} unmapped cards to {output_file}")
        return unmapped
    
    def get_statistics(self):
        """Get mapping statistics."""
        cursor = self.event_conn.cursor()
        
        stats = {}
        
        # Total cards
        cursor.execute("SELECT COUNT(DISTINCT card_id) FROM deck_cards")
        stats['total_cards'] = cursor.fetchone()[0]
        
        # Mapped cards
        cursor.execute("SELECT COUNT(*) FROM card_mappings")
        stats['mapped_cards'] = cursor.fetchone()[0]
        
        # Unmapped cards
        stats['unmapped_cards'] = stats['total_cards'] - stats['mapped_cards']
        
        # Coverage
        stats['coverage'] = round(
            (stats['mapped_cards'] / stats['total_cards']) * 100, 2
        ) if stats['total_cards'] > 0 else 0
        
        # By match method
        cursor.execute("""
            SELECT match_method, COUNT(*) as count
            FROM card_mappings
            WHERE match_method IS NOT NULL
            GROUP BY match_method
        """)
        stats['by_method'] = {row[0]: row[1] for row in cursor.fetchall()}
        
        return stats


def main():
    """Main execution."""
    logger.info("Starting online card mapping")
    
    mapper = OnlineCardMapper()
    
    try:
        mapper.connect()
        
        # Get unmapped cards
        unmapped = mapper.get_unmapped_cards()
        logger.info(f"Found {len(unmapped)} unmapped cards")
        
        # Show top unmapped cards
        print("\n" + "=" * 80)
        print("TOP 20 UNMAPPED CARDS (by usage)")
        print("=" * 80)
        for i, card in enumerate(unmapped[:20], 1):
            print(f"{i:2d}. {card['card_name']:30s} ({card['card_code']:15s}) - {card['usage_count']:4d} decks")
        
        # Try to create new mappings
        print("\n" + "=" * 80)
        print("ATTEMPTING TO MAP USING ONLINE SOURCES")
        print("=" * 80)
        
        new_mappings = mapper.create_new_mappings(unmapped)
        
        if new_mappings:
            print(f"\n✅ Found {len(new_mappings)} new mappings!")
            
            # Show sample mappings
            print("\nSample new mappings:")
            for mapping in new_mappings[:10]:
                print(f"  {mapping['event_card_name']} → {mapping['main_card_name']}")
                print(f"    Method: {mapping.get('match_method', 'unknown')}")
            
            # Save new mappings
            mapper.save_new_mappings(new_mappings)
        else:
            print("\n❌ No new mappings found using online sources")
        
        # Export unmapped cards for manual review
        print("\n" + "=" * 80)
        print("EXPORTING UNMAPPED CARDS")
        print("=" * 80)
        remaining_unmapped = mapper.export_unmapped_cards()
        print(f"Exported {len(remaining_unmapped)} unmapped cards to exports/unmapped_cards.json")
        
        # Show statistics
        stats = mapper.get_statistics()
        print("\n" + "=" * 80)
        print("UPDATED MAPPING STATISTICS")
        print("=" * 80)
        print(f"Total Cards:     {stats['total_cards']:,}")
        print(f"Mapped:          {stats['mapped_cards']:,}")
        print(f"Unmapped:        {stats['unmapped_cards']:,}")
        print(f"Coverage:        {stats['coverage']:.1f}%")
        
        if stats['by_method']:
            print("\nBy mapping method:")
            for method, count in stats['by_method'].items():
                print(f"  {method:20s}: {count:4d} cards")
        
        print("=" * 80)
        
    finally:
        mapper.close()
    
    logger.info("Online mapping completed")


if __name__ == '__main__':
    main()
