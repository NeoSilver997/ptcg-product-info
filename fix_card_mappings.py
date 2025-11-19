"""
Fix Remaining Card Mapping Issues
==================================
Handles special cases: basic energy, ACE SPEC cards, promos, and duplicates.
"""

import sqlite3
import re

EVENT_DB = "ptcg_events.db"
MAIN_DB = r"c:\AI_Server\Coding\PokemonDBByjules\PTCG_CardDB_Tc\pokemon_cards.db"

class CardMappingFixer:
    def __init__(self):
        self.event_conn = sqlite3.connect(EVENT_DB)
        self.main_conn = sqlite3.connect(MAIN_DB)
        
    def fix_basic_energy(self):
        """Map basic energy cards by name matching"""
        print("\n" + "="*70)
        print("FIXING BASIC ENERGY MAPPINGS")
        print("="*70)
        
        event_cursor = self.event_conn.cursor()
        main_cursor = self.main_conn.cursor()
        
        # Energy name mappings (Japanese → Chinese)
        energy_mappings = {
            '基本炎エネルギー': '基本火能量',
            '基本闘エネルギー': '基本鬥能量',
            '基本超エネルギー': '基本超能量',
            '基本悪エネルギー': '基本惡能量',
            '基本鋼エネルギー': '基本鋼能量',
            '基本草エネルギー': '基本草能量',
            '基本雷エネルギー': '基本雷能量',
            '基本水エネルギー': '基本水能量',
            '基本無色エネルギー': '基本無色能量'
        }
        
        mapped_count = 0
        
        for jp_name, cn_name in energy_mappings.items():
            # Find in main database
            main_cursor.execute("""
                SELECT id FROM cards WHERE name = ? LIMIT 1
            """, (cn_name,))
            
            result = main_cursor.fetchone()
            if not result:
                print(f"  Warning: {cn_name} not found in main database")
                continue
            
            main_card_id = result[0]
            
            # Insert mapping (use empty string as card_code for basic energy)
            event_cursor.execute("""
                INSERT OR IGNORE INTO card_mappings (event_card_code, event_card_name, main_card_id)
                VALUES (?, ?, ?)
            """, ('', jp_name, main_card_id))
            
            if event_cursor.rowcount > 0:
                mapped_count += 1
                print(f"  ✓ Mapped: {jp_name:20s} → {cn_name}")
        
        self.event_conn.commit()
        print(f"\nMapped {mapped_count} basic energy types")
        
    def fix_ace_spec_cards(self):
        """Map ACE SPEC cards by name matching"""
        print("\n" + "="*70)
        print("FIXING ACE SPEC CARD MAPPINGS")
        print("="*70)
        
        event_cursor = self.event_conn.cursor()
        main_cursor = self.main_conn.cursor()
        
        # Get ACE SPEC cards from event database
        event_cursor.execute("""
            SELECT DISTINCT card_name 
            FROM deck_cards 
            WHERE card_code LIKE 'ACE SPEC%'
        """)
        
        ace_spec_cards = [row[0] for row in event_cursor.fetchall()]
        
        # ACE SPEC name mappings (Japanese → Chinese)
        ace_mappings = {
            'プライムキャッチャー': 'ACE SPEC', # Need to find exact Chinese name
            'シークレットボックス': 'ACE SPEC',
            'マキシマムベルト': 'ACE SPEC',
            'プレシャスキャリー': 'ACE SPEC',
            'きらめく結晶': 'ACE SPEC'
        }
        
        mapped_count = 0
        
        for jp_name in ace_spec_cards:
            # Try to find by name similarity in main database
            main_cursor.execute("""
                SELECT id, name FROM cards 
                WHERE name LIKE ? OR name LIKE ?
                LIMIT 1
            """, (f'%{jp_name[:3]}%', f'%ACE%'))
            
            result = main_cursor.fetchone()
            if result:
                main_card_id, cn_name = result
                
                event_cursor.execute("""
                    INSERT OR IGNORE INTO card_mappings (event_card_code, event_card_name, main_card_id)
                    VALUES (?, ?, ?)
                """, ('ACE SPEC', jp_name, main_card_id))
                
                if event_cursor.rowcount > 0:
                    mapped_count += 1
                    print(f"  ✓ Mapped: {jp_name:30s} → {cn_name}")
            else:
                print(f"  ✗ Could not find: {jp_name}")
        
        self.event_conn.commit()
        print(f"\nMapped {mapped_count} ACE SPEC cards")
    
    def fix_promo_cards(self):
        """Import SV-P promo cards"""
        print("\n" + "="*70)
        print("FIXING PROMO CARDS (SV-P)")
        print("="*70)
        
        event_cursor = self.event_conn.cursor()
        main_cursor = self.main_conn.cursor()
        
        # Get SV-P cards from event database
        event_cursor.execute("""
            SELECT DISTINCT card_code, card_name, COUNT(*) as usage_count
            FROM deck_cards 
            WHERE card_code LIKE 'SV-P%'
            GROUP BY card_code, card_name
            ORDER BY usage_count DESC
        """)
        
        promo_cards = event_cursor.fetchall()
        
        # Ensure SV-P expansion exists
        main_cursor.execute("SELECT id FROM expansions WHERE code = ?", ('SV-P',))
        result = main_cursor.fetchone()
        
        if not result:
            main_cursor.execute(
                "INSERT INTO expansions (name, code) VALUES (?, ?)",
                ('SV Promotional Cards', 'SV-P')
            )
            self.main_conn.commit()
            expansion_id = main_cursor.lastrowid
            print(f"  Created SV-P expansion with ID {expansion_id}")
        else:
            expansion_id = result[0]
            print(f"  Using existing SV-P expansion (ID {expansion_id})")
        
        imported_count = 0
        
        for card_code, card_name, usage_count in promo_cards[:10]:  # Import top 10 for now
            # Parse collector number
            match = re.search(r'(\d+)/SV-P', card_code)
            if not match:
                continue
            
            collector_number = match.group(1)
            
            # Check if already exists
            main_cursor.execute("""
                SELECT id FROM cards 
                WHERE expansion_id = ? AND collector_number = ?
            """, (expansion_id, collector_number))
            
            if main_cursor.fetchone():
                continue
            
            # Insert card
            main_cursor.execute("""
                INSERT INTO cards (
                    name, card_type, expansion_id, collector_number, web_card_id
                ) VALUES (?, ?, ?, ?, ?)
            """, (card_name, '寶可夢', expansion_id, collector_number, card_code))
            
            imported_count += 1
            print(f"  ✓ Imported: {card_code:20s} - {card_name:30s} ({usage_count} uses)")
        
        self.main_conn.commit()
        print(f"\nImported {imported_count} promo cards")
    
    def fix_duplicate_cards(self):
        """Handle cards that appear in multiple expansions"""
        print("\n" + "="*70)
        print("FIXING DUPLICATE CARD MAPPINGS")
        print("="*70)
        
        event_cursor = self.event_conn.cursor()
        main_cursor = self.main_conn.cursor()
        
        # Find unmapped cards with card codes
        event_cursor.execute("""
            SELECT DISTINCT dc.card_code, dc.card_name
            FROM deck_cards dc
            LEFT JOIN card_mappings cm ON dc.card_code = cm.event_card_code
            WHERE cm.main_card_id IS NULL 
              AND dc.card_code != ''
              AND dc.card_code NOT LIKE 'ACE SPEC%'
            LIMIT 50
        """)
        
        unmapped = event_cursor.fetchall()
        mapped_count = 0
        
        for card_code, card_name in unmapped:
            # Parse expansion and collector number
            parts = card_code.split()
            if len(parts) < 2:
                continue
            
            expansion_code = parts[0]
            collector_part = parts[1]
            
            # Extract collector number (handle formats like "091/071")
            match = re.match(r'(\d+)', collector_part)
            if not match:
                continue
            
            collector_number = match.group(1)
            
            # Find in main database by name (fuzzy match)
            main_cursor.execute("""
                SELECT c.id, c.name, e.code 
                FROM cards c
                JOIN expansions e ON c.expansion_id = e.id
                WHERE c.name LIKE ?
                LIMIT 1
            """, (f'%{card_name[:5]}%',))
            
            result = main_cursor.fetchone()
            if result:
                main_card_id, cn_name, exp_code = result
                
                # Insert mapping
                event_cursor.execute("""
                    INSERT OR IGNORE INTO card_mappings (event_card_code, event_card_name, main_card_id)
                    VALUES (?, ?, ?)
                """, (card_code, card_name, main_card_id))
                
                if event_cursor.rowcount > 0:
                    mapped_count += 1
                    print(f"  ✓ {card_code:20s} → {cn_name:30s} (from {exp_code})")
        
        self.event_conn.commit()
        print(f"\nMapped {mapped_count} duplicate cards")
    
    def run(self):
        """Execute all fixes"""
        print("="*70)
        print("CARD MAPPING FIX SCRIPT")
        print("="*70)
        
        self.fix_basic_energy()
        self.fix_ace_spec_cards()
        self.fix_promo_cards()
        self.fix_duplicate_cards()
        
        print("\n" + "="*70)
        print("FIX COMPLETE")
        print("="*70)
        
        # Show updated statistics
        event_cursor = self.event_conn.cursor()
        
        event_cursor.execute("SELECT COUNT(*) FROM card_mappings")
        total_mappings = event_cursor.fetchone()[0]
        
        event_cursor.execute("SELECT COUNT(DISTINCT card_code) FROM deck_cards")
        total_event_cards = event_cursor.fetchone()[0]
        
        coverage = (total_mappings / total_event_cards * 100) if total_event_cards > 0 else 0
        
        print(f"\nUpdated Statistics:")
        print(f"  Total Mappings: {total_mappings}")
        print(f"  Coverage: {coverage:.2f}%")
        
        self.event_conn.close()
        self.main_conn.close()

if __name__ == "__main__":
    fixer = CardMappingFixer()
    fixer.run()
