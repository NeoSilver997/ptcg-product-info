"""
Import Complete MA and SVN Expansions
======================================
Import all cards from MA and SVN expansions (not just trainers).
"""

import sqlite3
import re

EVENT_DB = "ptcg_events.db"
MAIN_DB = r"c:\AI_Server\Coding\PokemonDBByjules\PTCG_CardDB_Tc\pokemon_cards.db"

class FullExpansionImporter:
    def __init__(self):
        self.event_conn = sqlite3.connect(EVENT_DB)
        self.main_conn = sqlite3.connect(MAIN_DB)
        
    def get_expansion_id(self, expansion_code):
        """Get expansion ID from main database"""
        cursor = self.main_conn.cursor()
        cursor.execute("SELECT id FROM expansions WHERE code = ?", (expansion_code,))
        result = cursor.fetchone()
        return result[0] if result else None
    
    def import_expansion_cards(self, expansion_code):
        """Import all cards for an expansion"""
        print(f"\n{'='*70}")
        print(f"IMPORTING {expansion_code} EXPANSION CARDS")
        print("="*70)
        
        expansion_id = self.get_expansion_id(expansion_code)
        if not expansion_id:
            print(f"Error: Expansion {expansion_code} not found")
            return 0
        
        event_cursor = self.event_conn.cursor()
        main_cursor = self.main_conn.cursor()
        
        # Get all cards from this expansion in event database
        event_cursor.execute(f"""
            SELECT DISTINCT card_code, card_name, COUNT(DISTINCT deck_id) as usage
            FROM deck_cards 
            WHERE card_code LIKE '{expansion_code} %'
            GROUP BY card_code, card_name
            ORDER BY usage DESC
        """)
        
        cards = event_cursor.fetchall()
        print(f"\nFound {len(cards)} unique {expansion_code} cards in event database")
        
        imported = 0
        skipped = 0
        
        for card_code, card_name, usage in cards:
            # Parse collector number
            match = re.search(r'(\d+)/(\d+)', card_code)
            if not match:
                print(f"  Warning: Could not parse {card_code}")
                continue
            
            collector_number = match.group(1)
            
            # Check if already exists
            main_cursor.execute("""
                SELECT id FROM cards 
                WHERE expansion_id = ? AND collector_number = ?
            """, (expansion_id, collector_number))
            
            if main_cursor.fetchone():
                skipped += 1
                continue
            
            # Insert card
            main_cursor.execute("""
                INSERT INTO cards (
                    name, 
                    card_type, 
                    expansion_id, 
                    collector_number,
                    web_card_id
                ) VALUES (?, ?, ?, ?, ?)
            """, (
                card_name,
                '寶可夢',  # Default type
                expansion_id,
                collector_number,
                card_code
            ))
            
            imported += 1
            print(f"  ✓ Imported: {card_code:20s} - {card_name:30s} ({usage:4d} decks)")
        
        self.main_conn.commit()
        
        print(f"\n{expansion_code} Summary:")
        print(f"  Imported: {imported} cards")
        print(f"  Skipped:  {skipped} existing cards")
        
        return imported
    
    def run(self):
        """Import all cards"""
        print("="*70)
        print("FULL EXPANSION IMPORT")
        print("="*70)
        
        total = 0
        total += self.import_expansion_cards('MA')
        total += self.import_expansion_cards('SVN')
        
        print("\n" + "="*70)
        print(f"IMPORT COMPLETE: {total} total cards imported")
        print("="*70)
        
        self.event_conn.close()
        self.main_conn.close()

if __name__ == "__main__":
    importer = FullExpansionImporter()
    importer.run()
