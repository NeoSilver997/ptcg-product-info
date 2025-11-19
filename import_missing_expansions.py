"""
Import Missing Expansions Script
=================================
Imports MA, SVN, SV-P expansion cards from event database into main database.

Usage:
    python import_missing_expansions.py

This script:
1. Extracts card codes for MA, SVN, SV-P expansions from card_code_cache.json
2. Fetches full card details from event database (ptcg_events.db)
3. Imports new expansions and cards into main database (pokemon_cards.db)
"""

import sqlite3
import json
import re
from pathlib import Path

# Database paths
EVENT_DB = "ptcg_events.db"
MAIN_DB = r"c:\AI_Server\Coding\PokemonDBByjules\PTCG_CardDB_Tc\pokemon_cards.db"
CACHE_FILE = "card_code_cache.json"

class ExpansionImporter:
    def __init__(self):
        self.event_conn = sqlite3.connect(EVENT_DB)
        self.main_conn = sqlite3.connect(MAIN_DB)
        self.cache = self.load_cache()
        
    def load_cache(self):
        """Load card code cache"""
        with open(CACHE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def extract_expansion_cards(self):
        """Extract cards for missing expansions from cache"""
        ma_cards = []
        svn_cards = []
        svp_cards = []
        
        for card_id, card_code in self.cache.items():
            if isinstance(card_code, str):
                if card_code.startswith('MA '):
                    ma_cards.append((card_id, card_code))
                elif card_code.startswith('SVN '):
                    svn_cards.append((card_id, card_code))
                elif card_code.startswith('SV-P '):
                    svp_cards.append((card_id, card_code))
        
        print(f"Found {len(ma_cards)} MA cards")
        print(f"Found {len(svn_cards)} SVN cards")
        print(f"Found {len(svp_cards)} SV-P cards")
        
        return {
            'MA': ma_cards,
            'SVN': svn_cards,
            'SV-P': svp_cards
        }
    
    def get_card_details(self, card_ids):
        """Get card details from event database"""
        cursor = self.event_conn.cursor()
        
        # Query card usage statistics
        placeholders = ','.join('?' * len(card_ids))
        query = f"""
        SELECT 
            dc.card_code,
            dc.card_name,
            COUNT(DISTINCT dc.deck_id) as deck_count,
            COUNT(*) as total_copies
        FROM deck_cards dc
        WHERE dc.card_code IN ({placeholders})
        GROUP BY dc.card_code, dc.card_name
        ORDER BY deck_count DESC
        """
        
        cursor.execute(query, card_ids)
        results = {}
        
        for row in cursor.fetchall():
            card_code, card_name, deck_count, total_copies = row
            results[card_code] = {
                'name': card_name,
                'card_code': card_code,
                'deck_count': deck_count,
                'total_copies': total_copies
            }
        
        return results
    
    def parse_card_code(self, card_code):
        """Parse card code into expansion and collector number"""
        # Format: "MA 019/043" or "SV-P 123"
        match = re.match(r'([A-Z0-9\-]+)\s+(\d+)/(\d+)', card_code)
        if match:
            expansion = match.group(1)
            collector_number = match.group(2)
            total_in_set = match.group(3)
            return expansion, collector_number, total_in_set
        
        # Promo format without set total
        match = re.match(r'([A-Z0-9\-]+)\s+(\d+)', card_code)
        if match:
            expansion = match.group(1)
            collector_number = match.group(2)
            return expansion, collector_number, None
        
        return None, None, None
    
    def ensure_expansion_exists(self, expansion_code):
        """Ensure expansion exists in main database"""
        cursor = self.main_conn.cursor()
        
        # Check if expansion exists
        cursor.execute("SELECT id FROM expansions WHERE code = ?", (expansion_code,))
        result = cursor.fetchone()
        
        if result:
            return result[0]
        
        # Insert new expansion
        expansion_names = {
            'MA': 'Master Art',
            'SVN': 'SV Night Wanderer',
            'SV-P': 'SV Promotional Cards'
        }
        
        expansion_name = expansion_names.get(expansion_code, expansion_code)
        cursor.execute(
            "INSERT INTO expansions (name, code) VALUES (?, ?)",
            (expansion_name, expansion_code)
        )
        self.main_conn.commit()
        
        expansion_id = cursor.lastrowid
        print(f"Created expansion: {expansion_name} ({expansion_code}) with ID {expansion_id}")
        return expansion_id
    
    def import_cards(self, expansion_code, cards_data):
        """Import cards into main database"""
        cursor = self.main_conn.cursor()
        expansion_id = self.ensure_expansion_exists(expansion_code)
        
        imported_count = 0
        skipped_count = 0
        
        for card_code, details in cards_data.items():
            _, collector_number, _ = self.parse_card_code(card_code)
            
            if not collector_number:
                print(f"Warning: Could not parse card code: {card_code}")
                skipped_count += 1
                continue
            
            # Check if card already exists
            cursor.execute("""
                SELECT id FROM cards 
                WHERE expansion_id = ? AND collector_number = ?
            """, (expansion_id, collector_number))
            
            if cursor.fetchone():
                skipped_count += 1
                continue
            
            # Insert card with minimal data (name and collector number)
            # Card type defaults to '寶可夢' (Pokemon) for now
            cursor.execute("""
                INSERT INTO cards (
                    name, 
                    card_type, 
                    expansion_id, 
                    collector_number,
                    web_card_id
                ) VALUES (?, ?, ?, ?, ?)
            """, (
                details['name'],
                '寶可夢',  # Default card type
                expansion_id,
                collector_number,
                card_code
            ))
            
            imported_count += 1
        
        self.main_conn.commit()
        print(f"Expansion {expansion_code}: Imported {imported_count} cards, skipped {skipped_count} existing cards")
        return imported_count
    
    def run(self):
        """Main import process"""
        print("="*60)
        print("MISSING EXPANSION IMPORT")
        print("="*60)
        
        # Extract cards from cache
        print("\n1. Extracting cards from cache...")
        expansion_cards = self.extract_expansion_cards()
        
        total_imported = 0
        
        for expansion_code, cards in expansion_cards.items():
            if not cards:
                print(f"\nNo {expansion_code} cards to import")
                continue
            
            print(f"\n2. Processing {expansion_code} expansion...")
            
            # Get card codes
            card_codes = [card_code for _, card_code in cards]
            
            # Get detailed info from event database
            print(f"   Fetching details for {len(card_codes)} cards...")
            card_details = self.get_card_details(card_codes)
            
            print(f"   Found details for {len(card_details)} cards")
            
            # Show top cards
            print(f"\n   Top 5 most-used {expansion_code} cards:")
            sorted_cards = sorted(card_details.items(), 
                                key=lambda x: x[1]['deck_count'], 
                                reverse=True)
            for i, (code, details) in enumerate(sorted_cards[:5], 1):
                print(f"   {i}. {code:15s} - {details['name']:30s} ({details['deck_count']} decks)")
            
            # Import into main database
            print(f"\n3. Importing {expansion_code} cards into main database...")
            imported = self.import_cards(expansion_code, card_details)
            total_imported += imported
        
        print("\n" + "="*60)
        print(f"IMPORT COMPLETE: {total_imported} total cards imported")
        print("="*60)
        
        self.event_conn.close()
        self.main_conn.close()

if __name__ == "__main__":
    importer = ExpansionImporter()
    importer.run()
