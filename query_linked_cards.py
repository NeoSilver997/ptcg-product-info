"""
Query utility for linked card data - Japanese event cards with Chinese names from main database.
"""

import sqlite3
import json
from typing import List, Dict, Any


class LinkedCardQuery:
    """Query cards with Japanese and Chinese names."""
    
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
    
    def close(self):
        """Close connections."""
        if self.event_conn:
            self.event_conn.close()
        if self.main_conn:
            self.main_conn.close()
    
    def get_card_by_japanese_name(self, japanese_name: str) -> List[Dict]:
        """Find cards by Japanese name."""
        cursor = self.event_conn.cursor()
        cursor.execute("""
            SELECT 
                cm.*,
                COUNT(dc.id) as usage_count
            FROM card_mappings cm
            LEFT JOIN deck_cards dc ON cm.event_card_id = dc.card_id
            WHERE cm.event_card_name LIKE ?
            GROUP BY cm.event_card_id
        """, (f'%{japanese_name}%',))
        
        return [dict(row) for row in cursor.fetchall()]
    
    def get_card_by_chinese_name(self, chinese_name: str) -> List[Dict]:
        """Find cards by Chinese name."""
        cursor = self.event_conn.cursor()
        cursor.execute("""
            SELECT 
                cm.*,
                COUNT(dc.id) as usage_count
            FROM card_mappings cm
            LEFT JOIN deck_cards dc ON cm.event_card_id = dc.card_id
            WHERE cm.main_card_name LIKE ?
            GROUP BY cm.event_card_id
        """, (f'%{chinese_name}%',))
        
        return [dict(row) for row in cursor.fetchall()]
    
    def get_deck_with_translations(self, deck_id: str) -> Dict:
        """Get complete deck with card translations."""
        event_cursor = self.event_conn.cursor()
        
        # Get deck info
        event_cursor.execute("""
            SELECT 
                d.*,
                e.event_date,
                e.event_host,
                p.player_name,
                p.player_area
            FROM decks d
            LEFT JOIN events e ON d.event_id = e.event_id
            LEFT JOIN players p ON d.player_id = p.player_id
            WHERE d.deck_id = ?
        """, (deck_id,))
        
        deck = dict(event_cursor.fetchone() or {})
        if not deck:
            return None
        
        # Get cards with translations
        event_cursor.execute("""
            SELECT 
                dc.card_name as japanese_name,
                dc.card_code,
                dc.quantity,
                cm.main_card_name as chinese_name,
                cm.main_card_id
            FROM deck_cards dc
            LEFT JOIN card_mappings cm ON dc.card_id = cm.event_card_id
            WHERE dc.deck_id = ?
            ORDER BY 
                CASE 
                    WHEN dc.card_name LIKE '%ex%' THEN 1
                    WHEN dc.card_name LIKE '%V%' THEN 2
                    WHEN dc.card_name LIKE '%エネルギー%' THEN 5
                    ELSE 3
                END,
                dc.card_name
        """, (deck_id,))
        
        deck['cards'] = [dict(row) for row in event_cursor.fetchall()]
        
        return deck
    
    def get_winning_decks_with_translations(self, limit=10):
        """Get recent winning decks with card translations."""
        event_cursor = self.event_conn.cursor()
        
        event_cursor.execute("""
            SELECT deck_id
            FROM decks
            WHERE rank = '1位'
            ORDER BY import_timestamp DESC
            LIMIT ?
        """, (limit,))
        
        deck_ids = [row[0] for row in event_cursor.fetchall()]
        
        decks = []
        for deck_id in deck_ids:
            deck = self.get_deck_with_translations(deck_id)
            if deck:
                decks.append(deck)
        
        return decks
    
    def get_popular_cards_bilingual(self, limit=30):
        """Get most popular cards with both Japanese and Chinese names."""
        cursor = self.event_conn.cursor()
        cursor.execute("""
            SELECT 
                dc.card_name as japanese_name,
                dc.card_code,
                cm.main_card_name as chinese_name,
                COUNT(DISTINCT dc.deck_id) as deck_count,
                SUM(dc.quantity) as total_copies,
                ROUND(AVG(dc.quantity), 2) as avg_per_deck
            FROM deck_cards dc
            LEFT JOIN card_mappings cm ON dc.card_id = cm.event_card_id
            WHERE dc.card_name NOT LIKE '%エネルギー%'
            GROUP BY dc.card_id
            ORDER BY deck_count DESC
            LIMIT ?
        """, (limit,))
        
        return [dict(row) for row in cursor.fetchall()]
    
    def get_card_full_details(self, main_card_id: int) -> Dict:
        """Get full card details from main database."""
        cursor = self.main_conn.cursor()
        cursor.execute("""
            SELECT 
                c.*,
                e.name as expansion_name,
                e.code as expansion_code,
                i.name as illustrator_name
            FROM cards c
            LEFT JOIN expansions e ON c.expansion_id = e.id
            LEFT JOIN illustrators i ON c.illustrator_id = i.id
            WHERE c.id = ?
        """, (main_card_id,))
        
        card = cursor.fetchone()
        if not card:
            return None
        
        card_dict = dict(card)
        
        # Get skills
        cursor.execute("""
            SELECT skill_number, name, cost, damage, effect
            FROM skills
            WHERE card_id = ?
            ORDER BY skill_number
        """, (main_card_id,))
        card_dict['skills'] = [dict(row) for row in cursor.fetchall()]
        
        # Get abilities
        cursor.execute("""
            SELECT name, description
            FROM abilities
            WHERE card_id = ?
        """, (main_card_id,))
        card_dict['abilities'] = [dict(row) for row in cursor.fetchall()]
        
        return card_dict
    
    def search_cards(self, keyword: str, search_japanese=True, search_chinese=True):
        """Search cards by keyword in both languages."""
        cursor = self.event_conn.cursor()
        
        conditions = []
        if search_japanese:
            conditions.append("cm.event_card_name LIKE ?")
        if search_chinese:
            conditions.append("cm.main_card_name LIKE ?")
        
        where_clause = " OR ".join(conditions)
        params = [f'%{keyword}%'] * len(conditions)
        
        cursor.execute(f"""
            SELECT 
                cm.event_card_name as japanese_name,
                cm.main_card_name as chinese_name,
                cm.event_card_code,
                cm.main_card_id,
                COUNT(DISTINCT dc.deck_id) as usage_count
            FROM card_mappings cm
            LEFT JOIN deck_cards dc ON cm.event_card_id = dc.card_id
            WHERE {where_clause}
            GROUP BY cm.event_card_id
            ORDER BY usage_count DESC
        """, params)
        
        return [dict(row) for row in cursor.fetchall()]


def main():
    """Demo queries."""
    query = LinkedCardQuery()
    
    try:
        query.connect()
        
        print("=" * 80)
        print("BILINGUAL POKEMON CARD QUERY SYSTEM")
        print("=" * 80)
        
        # Popular cards with translations
        print("\n🎴 TOP 15 MOST POPULAR CARDS (Japanese ⇄ Chinese):")
        print("-" * 80)
        popular = query.get_popular_cards_bilingual(15)
        for i, card in enumerate(popular, 1):
            jp_name = card['japanese_name'] or 'N/A'
            cn_name = card['chinese_name'] or '(未映射)'
            code = card['card_code'] or ''
            count = card['deck_count']
            print(f"{i:2d}. {jp_name:25s} ⇄ {cn_name:20s} ({code:15s}) - {count:4d} decks")
        
        # Search example
        print("\n\n🔍 SEARCH EXAMPLE: 'ピカチュウ' (Pikachu):")
        print("-" * 80)
        results = query.search_cards('ピカチュウ', search_japanese=True, search_chinese=False)
        for result in results[:5]:
            print(f"{result['japanese_name']:20s} → {result['chinese_name']:15s} ({result['event_card_code']})")
            print(f"  Used in {result['usage_count']} decks")
        
        # Sample winning deck with translations
        print("\n\n🏆 SAMPLE WINNING DECK (with translations):")
        print("-" * 80)
        decks = query.get_winning_decks_with_translations(1)
        if decks:
            deck = decks[0]
            print(f"Event: {deck['event_host']} ({deck['event_date']})")
            print(f"Player: {deck['player_name']} ({deck['player_area']})")
            print(f"\nDeck List:")
            for card in deck['cards'][:15]:
                jp_name = card['japanese_name']
                cn_name = card['chinese_name'] or '(未映射)'
                qty = card['quantity']
                print(f"  {qty}x {jp_name:25s} → {cn_name}")
        
        print("\n" + "=" * 80)
        
    finally:
        query.close()


if __name__ == '__main__':
    main()
