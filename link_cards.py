"""
Link event database cards with main Pokemon card database.

This script creates a mapping between Japanese card names in the event database
and Chinese card names in the main database using expansion codes and collector numbers.
"""

import sqlite3
import json
from pathlib import Path
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class CardLinker:
    """Link event cards with main card database."""
    
    def __init__(self, event_db='ptcg_events.db', main_db=r'c:\AI_Server\Coding\PokemonDBByjules\PTCG_CardDB_Tc\pokemon_cards.db'):
        self.event_db_path = event_db
        self.main_db_path = main_db
        self.event_conn = None
        self.main_conn = None
        
    def connect(self):
        """Connect to both databases."""
        self.event_conn = sqlite3.connect(self.event_db_path)
        self.event_conn.row_factory = sqlite3.Row
        self.main_conn = sqlite3.connect(self.main_db_path)
        self.main_conn.row_factory = sqlite3.Row
        logger.info("Connected to both databases")
    
    def close(self):
        """Close database connections."""
        if self.event_conn:
            self.event_conn.close()
        if self.main_conn:
            self.main_conn.close()
        logger.info("Database connections closed")
    
    def create_mapping_table(self):
        """Create table to store card mappings."""
        cursor = self.event_conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS card_mappings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_card_id TEXT,
                event_card_name TEXT,
                event_card_code TEXT,
                main_card_id INTEGER,
                main_card_name TEXT,
                main_collector_number TEXT,
                main_expansion_code TEXT,
                match_confidence TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_event_card_id ON card_mappings(event_card_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_main_card_id ON card_mappings(main_card_id)")
        
        self.event_conn.commit()
        logger.info("Created card_mappings table")
    
    def build_expansion_map(self):
        """Build mapping between expansion codes."""
        cursor = self.main_conn.cursor()
        cursor.execute("SELECT id, code, name FROM expansions")
        
        expansion_map = {}
        for row in cursor:
            expansion_map[row['code']] = {
                'id': row['id'],
                'name': row['name']
            }
        
        logger.info(f"Built expansion map with {len(expansion_map)} expansions")
        return expansion_map
    
    def parse_card_code(self, card_code):
        """
        Parse card code like 'SV8a 120/187' into expansion and number.
        
        Returns: (expansion_code, collector_number) or (None, None)
        """
        if not card_code or card_code == 'ACE SPEC':
            return None, None
        
        parts = card_code.split()
        if len(parts) < 2:
            return None, None
        
        expansion = parts[0]
        number_part = parts[1]
        
        # Extract just the collector number (before the /)
        if '/' in number_part:
            number = number_part.split('/')[0]
        else:
            number = number_part
        
        return expansion, number
    
    def link_cards(self):
        """Link event cards with main database cards."""
        expansion_map = self.build_expansion_map()
        
        # Get unique card codes from event database
        event_cursor = self.event_conn.cursor()
        event_cursor.execute("""
            SELECT DISTINCT card_id, card_name, card_code
            FROM deck_cards
            WHERE card_code != '' AND card_code != 'ACE SPEC'
            ORDER BY card_code
        """)
        
        event_cards = event_cursor.fetchall()
        logger.info(f"Processing {len(event_cards)} unique event cards")
        
        mappings = []
        matched = 0
        unmatched = 0
        
        for idx, event_card in enumerate(event_cards):
            if idx % 100 == 0:
                logger.info(f"Processing card {idx}/{len(event_cards)}")
            expansion_code, collector_number = self.parse_card_code(event_card['card_code'])
            
            if not expansion_code or not collector_number:
                unmatched += 1
                continue
            
            # Check if expansion exists in main database
            if expansion_code not in expansion_map:
                logger.debug(f"Expansion not found: {expansion_code} for card {event_card['card_name']}")
                unmatched += 1
                continue
            
            expansion_id = expansion_map[expansion_code]['id']
            
            # Find matching card in main database
            main_cursor = self.main_conn.cursor()
            main_cursor.execute("""
                SELECT id, name, collector_number
                FROM cards
                WHERE expansion_id = ? AND collector_number = ?
            """, (expansion_id, collector_number))
            
            main_card = main_cursor.fetchone()
            
            if main_card:
                mappings.append({
                    'event_card_id': event_card['card_id'],
                    'event_card_name': event_card['card_name'],
                    'event_card_code': event_card['card_code'],
                    'main_card_id': main_card['id'],
                    'main_card_name': main_card['name'],
                    'main_collector_number': main_card['collector_number'],
                    'main_expansion_code': expansion_code,
                    'match_confidence': 'high'
                })
                matched += 1
            else:
                logger.debug(f"No match found for {event_card['card_name']} ({event_card['card_code']})")
                unmatched += 1
        
        logger.info(f"Matched: {matched}, Unmatched: {unmatched}")
        return mappings
    
    def save_mappings(self, mappings):
        """Save card mappings to database, preserving existing manual links."""
        cursor = self.event_conn.cursor()
        
        # Don't clear existing mappings - preserve manual links
        # Only insert new mappings that don't already exist
        for mapping in mappings:
            # Check if this mapping already exists
            cursor.execute("""
                SELECT id FROM card_mappings 
                WHERE event_card_id = ? AND main_card_id = ?
            """, (mapping['event_card_id'], mapping['main_card_id']))
            
            if not cursor.fetchone():  # Only insert if it doesn't exist
                cursor.execute("""
                    INSERT INTO card_mappings (
                        event_card_id, event_card_name, event_card_code,
                        main_card_id, main_card_name, main_collector_number,
                        main_expansion_code, match_confidence
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    mapping['event_card_id'], mapping['event_card_name'], mapping['event_card_code'],
                    mapping['main_card_id'], mapping['main_card_name'], mapping['main_collector_number'],
                    mapping['main_expansion_code'], mapping['match_confidence']
                ))
        
        self.event_conn.commit()
        logger.info(f"Saved {len(mappings)} new card mappings (preserved existing manual links)")
    
    def export_mappings_json(self, output_file='card_mappings.json'):
        """Export mappings to JSON file."""
        cursor = self.event_conn.cursor()
        cursor.execute("""
            SELECT * FROM card_mappings
            ORDER BY event_card_name
        """)
        
        mappings = [dict(row) for row in cursor.fetchall()]
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(mappings, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Exported mappings to {output_file}")
    
    def get_statistics(self):
        """Get mapping statistics."""
        event_cursor = self.event_conn.cursor()
        main_cursor = self.main_conn.cursor()
        
        stats = {}
        
        # Total unique event cards
        event_cursor.execute("SELECT COUNT(DISTINCT card_id) FROM deck_cards")
        stats['total_event_cards'] = event_cursor.fetchone()[0]
        
        # Mapped cards
        event_cursor.execute("SELECT COUNT(*) FROM card_mappings")
        stats['mapped_cards'] = event_cursor.fetchone()[0]
        
        # Coverage percentage
        stats['coverage_percentage'] = round(
            (stats['mapped_cards'] / stats['total_event_cards']) * 100, 2
        ) if stats['total_event_cards'] > 0 else 0
        
        # Cards by expansion
        event_cursor.execute("""
            SELECT main_expansion_code, COUNT(*) as count
            FROM card_mappings
            GROUP BY main_expansion_code
            ORDER BY count DESC
            LIMIT 10
        """)
        stats['top_expansions'] = [
            {'expansion': row[0], 'count': row[1]}
            for row in event_cursor.fetchall()
        ]
        
        return stats
    
    def get_linked_card_info(self, event_card_id):
        """Get full card information with Chinese name from main database."""
        cursor = self.event_conn.cursor()
        cursor.execute("""
            SELECT 
                cm.event_card_name as japanese_name,
                cm.event_card_code,
                cm.main_card_id,
                cm.main_card_name as chinese_name
            FROM card_mappings cm
            WHERE cm.event_card_id = ?
        """, (event_card_id,))
        
        result = cursor.fetchone()
        if not result:
            return None
        
        mapping = dict(result)
        
        # Get full card details from main database
        main_cursor = self.main_conn.cursor()
        main_cursor.execute("""
            SELECT 
                c.*,
                e.name as expansion_name,
                e.code as expansion_code
            FROM cards c
            LEFT JOIN expansions e ON c.expansion_id = e.id
            WHERE c.id = ?
        """, (mapping['main_card_id'],))
        
        card_details = main_cursor.fetchone()
        if card_details:
            mapping['card_details'] = dict(card_details)
        
        return mapping


def main():
    """Main execution."""
    logger.info("Starting card linking process")
    
    linker = CardLinker()
    
    try:
        linker.connect()
        linker.create_mapping_table()
        
        # Link cards
        mappings = linker.link_cards()
        
        # Save to database
        linker.save_mappings(mappings)
        
        # Export to JSON
        linker.export_mappings_json('exports/card_mappings.json')
        
        # Show statistics
        stats = linker.get_statistics()
        
        print("\n" + "=" * 70)
        print("CARD LINKING STATISTICS")
        print("=" * 70)
        print(f"Total Event Cards: {stats['total_event_cards']}")
        print(f"Mapped Cards: {stats['mapped_cards']}")
        print(f"Coverage: {stats['coverage_percentage']}%")
        print("\nTop Expansions:")
        for exp in stats['top_expansions']:
            expansion_name = exp['expansion'] or 'Unknown'
            print(f"  {expansion_name:10s} : {exp['count']:4d} cards")
        print("=" * 70)
        
        # Sample mappings
        print("\n📝 SAMPLE CARD MAPPINGS (Japanese → Chinese):")
        print("-" * 70)
        cursor = linker.event_conn.cursor()
        cursor.execute("""
            SELECT event_card_name, event_card_code, main_card_name
            FROM card_mappings
            ORDER BY RANDOM()
            LIMIT 10
        """)
        for row in cursor.fetchall():
            print(f"{row[0]:20s} ({row[1]:15s}) → {row[2]}")
        
    finally:
        linker.close()
    
    logger.info("Card linking completed")


if __name__ == '__main__':
    main()
