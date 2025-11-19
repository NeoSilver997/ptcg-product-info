"""
Map Cards by Name Matching
==========================
Maps unmapped cards by finding already-mapped cards with the same name.

Logic:
1. Find all unmapped cards
2. For each unmapped card, search for a mapped card with same name
3. Create mapping using the found card's main_card_id

This handles cards that appear in multiple expansions but aren't all mapped.
"""

import sqlite3

EVENT_DB = "ptcg_events.db"
MAIN_DB = r"c:\AI_Server\Coding\PokemonDBByjules\PTCG_CardDB_Tc\pokemon_cards.db"

class NameBasedMapper:
    def __init__(self):
        self.event_conn = sqlite3.connect(EVENT_DB)
        self.main_conn = sqlite3.connect(MAIN_DB)
        
    def map_by_name(self):
        """Map unmapped cards by matching names with already-mapped cards"""
        print("="*80)
        print("MAPPING CARDS BY NAME MATCHING")
        print("="*80)
        
        event_cursor = self.event_conn.cursor()
        
        # Get all unmapped cards
        event_cursor.execute("""
            SELECT DISTINCT dc.card_code, dc.card_name
            FROM deck_cards dc
            LEFT JOIN card_mappings cm ON dc.card_code = cm.event_card_code
            WHERE cm.main_card_id IS NULL
              AND dc.card_code != ''
              AND dc.card_code NOT LIKE 'ACE SPEC%'
        """)
        
        unmapped_cards = event_cursor.fetchall()
        
        print(f"\nFound {len(unmapped_cards)} unmapped cards")
        print("\nSearching for name matches...\n")
        
        mapped_count = 0
        not_found_count = 0
        
        for card_code, card_name in unmapped_cards:
            # Find a mapped card with the same name
            event_cursor.execute("""
                SELECT cm.main_card_id
                FROM card_mappings cm
                WHERE cm.event_card_name = ?
                LIMIT 1
            """, (card_name,))
            
            result = event_cursor.fetchone()
            
            if result:
                main_card_id = result[0]
                
                # Get Chinese name for display
                main_cursor = self.main_conn.cursor()
                main_cursor.execute("""
                    SELECT c.name, e.code
                    FROM cards c
                    LEFT JOIN expansions e ON c.expansion_id = e.id
                    WHERE c.id = ?
                """, (main_card_id,))
                
                main_result = main_cursor.fetchone()
                if main_result:
                    cn_name, exp_code = main_result
                    
                    # Insert mapping
                    event_cursor.execute("""
                        INSERT OR IGNORE INTO card_mappings (event_card_code, event_card_name, main_card_id)
                        VALUES (?, ?, ?)
                    """, (card_code, card_name, main_card_id))
                    
                    if event_cursor.rowcount > 0:
                        mapped_count += 1
                        print(f"✓ {card_code:20s} {card_name:30s} → {cn_name} ({exp_code})")
            else:
                not_found_count += 1
        
        self.event_conn.commit()
        
        print("\n" + "="*80)
        print("MAPPING COMPLETE")
        print("="*80)
        print(f"\nSuccessfully mapped: {mapped_count} cards")
        print(f"No matching name found: {not_found_count} cards")
        
        # Show updated statistics
        event_cursor.execute("SELECT COUNT(*) FROM card_mappings")
        total_mappings = event_cursor.fetchone()[0]
        
        event_cursor.execute("SELECT COUNT(DISTINCT card_code) FROM deck_cards")
        total_cards = event_cursor.fetchone()[0]
        
        coverage = (total_mappings / total_cards * 100) if total_cards > 0 else 0
        
        print(f"\nUpdated Statistics:")
        print(f"  Total Mappings: {total_mappings}")
        print(f"  Coverage: {coverage:.2f}%")
        
    def run(self):
        """Execute mapping"""
        self.map_by_name()
        self.event_conn.close()
        self.main_conn.close()

if __name__ == "__main__":
    mapper = NameBasedMapper()
    mapper.run()
