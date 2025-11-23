"""
AI-powered Pokemon TCG deck builder and analyzer.

This module provides AI capabilities for:
- Analyzing existing tournament decks
- Building new competitive decks
- Recommending card improvements
- Understanding card synergies
"""

import sqlite3
import json
from collections import Counter, defaultdict
from typing import List, Dict, Tuple, Optional
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class CardDatabase:
    """Manages card data and relationships from tournament database."""
    
    def __init__(self, db_path='ptcg_events.db'):
        """Initialize card database connection."""
        self.db_path = db_path
        self.conn = None
        self._card_cache = {}
        self._synergy_cache = {}
    
    def connect(self):
        """Connect to the database."""
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        logger.info(f"Connected to card database: {self.db_path}")
    
    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()
    
    def get_all_cards(self) -> List[Dict]:
        """Get all unique cards from the database."""
        query = """
            SELECT DISTINCT card_id, card_name, card_code
            FROM deck_cards
            WHERE card_name IS NOT NULL
            ORDER BY card_name
        """
        cursor = self.conn.execute(query)
        return [dict(row) for row in cursor.fetchall()]
    
    def get_card_usage_stats(self, min_usage=1) -> List[Dict]:
        """Get card usage statistics across all decks."""
        query = """
            SELECT 
                card_id,
                card_name,
                card_code,
                COUNT(DISTINCT deck_id) as deck_count,
                AVG(quantity) as avg_quantity,
                SUM(quantity) as total_copies
            FROM deck_cards
            WHERE card_name IS NOT NULL
            GROUP BY card_id
            HAVING deck_count >= ?
            ORDER BY deck_count DESC, total_copies DESC
        """
        cursor = self.conn.execute(query, (min_usage,))
        return [dict(row) for row in cursor.fetchall()]
    
    def get_card_synergies(self, card_name: str, min_cooccurrence=2) -> List[Dict]:
        """Find cards that frequently appear together with the given card."""
        query = """
            SELECT 
                dc2.card_name,
                dc2.card_code,
                COUNT(DISTINCT dc1.deck_id) as cooccurrence,
                AVG(dc2.quantity) as avg_quantity
            FROM deck_cards dc1
            JOIN deck_cards dc2 ON dc1.deck_id = dc2.deck_id
            WHERE dc1.card_name = ?
            AND dc2.card_name != ?
            AND dc2.card_name IS NOT NULL
            GROUP BY dc2.card_id
            HAVING cooccurrence >= ?
            ORDER BY cooccurrence DESC
            LIMIT 20
        """
        cursor = self.conn.execute(query, (card_name, card_name, min_cooccurrence))
        return [dict(row) for row in cursor.fetchall()]
    
    def get_deck_by_id(self, deck_id: str) -> Optional[Dict]:
        """Get complete deck information."""
        # Get deck metadata
        deck_query = """
            SELECT d.*, e.event_date, e.event_title, p.player_name
            FROM decks d
            LEFT JOIN events e ON d.event_id = e.event_id
            LEFT JOIN players p ON d.player_id = p.player_id
            WHERE d.deck_id = ?
        """
        cursor = self.conn.execute(deck_query, (deck_id,))
        deck_info = cursor.fetchone()
        
        if not deck_info:
            return None
        
        # Get deck cards
        cards_query = """
            SELECT card_name, card_code, quantity
            FROM deck_cards
            WHERE deck_id = ?
            ORDER BY card_name
        """
        cursor = self.conn.execute(cards_query, (deck_id,))
        cards = [dict(row) for row in cursor.fetchall()]
        
        return {
            'deck_info': dict(deck_info),
            'cards': cards,
            'total_cards': sum(card['quantity'] for card in cards)
        }
    
    def get_winning_decks(self, limit=50) -> List[Dict]:
        """Get decks that won tournaments (rank = '1位')."""
        query = """
            SELECT 
                d.deck_id,
                d.rank,
                e.event_date,
                e.event_title,
                p.player_name
            FROM decks d
            JOIN events e ON d.event_id = e.event_id
            JOIN players p ON d.player_id = p.player_id
            WHERE d.rank = '1位'
            ORDER BY e.event_date DESC
            LIMIT ?
        """
        cursor = self.conn.execute(query, (limit,))
        return [dict(row) for row in cursor.fetchall()]


class DeckAnalyzer:
    """Analyzes deck composition and performance patterns."""
    
    def __init__(self, card_db: CardDatabase):
        """Initialize with card database."""
        self.card_db = card_db
    
    def analyze_deck(self, deck_id: str) -> Dict:
        """Analyze a deck's composition and strengths."""
        deck = self.card_db.get_deck_by_id(deck_id)
        
        if not deck:
            return {'error': 'Deck not found'}
        
        cards = deck['cards']
        
        # Categorize cards
        pokemon_cards = []
        trainer_cards = []
        energy_cards = []
        
        for card in cards:
            name = card['card_name']
            if 'エネルギー' in name:
                energy_cards.append(card)
            elif any(keyword in name for keyword in ['博士', 'サポート', 'ボス', 'グッズ', 'スタジアム', 'ボール', 'いれかえ']):
                trainer_cards.append(card)
            else:
                pokemon_cards.append(card)
        
        # Calculate statistics
        total_cards = sum(card['quantity'] for card in cards)
        
        analysis = {
            'deck_id': deck_id,
            'deck_info': deck['deck_info'],
            'total_cards': total_cards,
            'composition': {
                'pokemon': {
                    'count': sum(card['quantity'] for card in pokemon_cards),
                    'unique': len(pokemon_cards),
                    'cards': pokemon_cards
                },
                'trainers': {
                    'count': sum(card['quantity'] for card in trainer_cards),
                    'unique': len(trainer_cards),
                    'cards': trainer_cards
                },
                'energy': {
                    'count': sum(card['quantity'] for card in energy_cards),
                    'unique': len(energy_cards),
                    'cards': energy_cards
                }
            },
            'is_valid': total_cards == 60,
            'has_basic_pokemon': len(pokemon_cards) > 0,
            'has_energy': len(energy_cards) > 0
        }
        
        return analysis
    
    def get_deck_archetype(self, deck_id: str) -> str:
        """Determine deck archetype based on key cards."""
        deck = self.card_db.get_deck_by_id(deck_id)
        
        if not deck:
            return 'Unknown'
        
        cards = deck['cards']
        
        # Look for signature cards
        for card in cards:
            name = card['card_name']
            # Check for ex/V cards as archetype markers
            if 'ex' in name or 'EX' in name:
                return name.split(' ')[0] + ' Deck'
        
        return 'Standard Deck'
    
    def compare_decks(self, deck_id1: str, deck_id2: str) -> Dict:
        """Compare two decks and find similarities/differences."""
        deck1 = self.card_db.get_deck_by_id(deck_id1)
        deck2 = self.card_db.get_deck_by_id(deck_id2)
        
        if not deck1 or not deck2:
            return {'error': 'One or both decks not found'}
        
        cards1 = {card['card_name']: card['quantity'] for card in deck1['cards']}
        cards2 = {card['card_name']: card['quantity'] for card in deck2['cards']}
        
        all_cards = set(cards1.keys()) | set(cards2.keys())
        
        shared = []
        only_deck1 = []
        only_deck2 = []
        
        for card_name in all_cards:
            q1 = cards1.get(card_name, 0)
            q2 = cards2.get(card_name, 0)
            
            if q1 > 0 and q2 > 0:
                shared.append({'card_name': card_name, 'deck1_qty': q1, 'deck2_qty': q2})
            elif q1 > 0:
                only_deck1.append({'card_name': card_name, 'quantity': q1})
            else:
                only_deck2.append({'card_name': card_name, 'quantity': q2})
        
        similarity = len(shared) / len(all_cards) if all_cards else 0
        
        return {
            'similarity': similarity,
            'shared_cards': len(shared),
            'unique_to_deck1': len(only_deck1),
            'unique_to_deck2': len(only_deck2),
            'details': {
                'shared': shared,
                'only_deck1': only_deck1,
                'only_deck2': only_deck2
            }
        }


class DeckBuilder:
    """AI-powered deck builder using tournament data patterns."""
    
    def __init__(self, card_db: CardDatabase):
        """Initialize with card database."""
        self.card_db = card_db
        self.analyzer = DeckAnalyzer(card_db)
    
    def build_deck_from_archetype(self, archetype: str, core_cards: List[Tuple[str, int]]) -> Dict:
        """
        Build a deck around core cards using tournament data.
        
        Args:
            archetype: Deck archetype name (e.g., "Lightning Deck")
            core_cards: List of (card_name, quantity) tuples
        
        Returns:
            Complete deck with 60 cards
        """
        deck = {'cards': [], 'total': 0}
        used_cards = set()
        
        # Add core cards
        for card_name, quantity in core_cards:
            deck['cards'].append({
                'card_name': card_name,
                'quantity': quantity
            })
            deck['total'] += quantity
            used_cards.add(card_name)
        
        # Find synergies for core cards
        synergy_suggestions = []
        for card_name, _ in core_cards:
            synergies = self.card_db.get_card_synergies(card_name, min_cooccurrence=2)
            for synergy in synergies:
                if synergy['card_name'] not in used_cards:
                    synergy_suggestions.append(synergy)
        
        # Sort by cooccurrence and add top suggestions
        synergy_suggestions.sort(key=lambda x: x['cooccurrence'], reverse=True)
        
        for suggestion in synergy_suggestions:
            if deck['total'] >= 60:
                break
            
            card_name = suggestion['card_name']
            quantity = min(4, int(suggestion['avg_quantity']), 60 - deck['total'])
            
            if quantity > 0 and card_name not in used_cards:
                deck['cards'].append({
                    'card_name': card_name,
                    'card_code': suggestion.get('card_code', ''),
                    'quantity': quantity
                })
                deck['total'] += quantity
                used_cards.add(card_name)
        
        # Fill remaining with staple cards if needed
        if deck['total'] < 60:
            staples = self.get_staple_cards()
            for staple in staples:
                if deck['total'] >= 60:
                    break
                
                card_name = staple['card_name']
                if card_name not in used_cards:
                    quantity = min(4, int(staple['avg_quantity']), 60 - deck['total'])
                    if quantity > 0:
                        deck['cards'].append({
                            'card_name': card_name,
                            'card_code': staple.get('card_code', ''),
                            'quantity': quantity
                        })
                        deck['total'] += quantity
                        used_cards.add(card_name)
        
        return deck
    
    def get_staple_cards(self) -> List[Dict]:
        """Get staple cards that appear in many decks."""
        return self.card_db.get_card_usage_stats(min_usage=5)
    
    def suggest_card_replacements(self, deck_id: str, card_name: str) -> List[Dict]:
        """Suggest alternative cards to replace a specific card in a deck."""
        # Get the deck
        deck = self.card_db.get_deck_by_id(deck_id)
        if not deck:
            return []
        
        # Find synergies with other cards in the deck
        other_cards = [card['card_name'] for card in deck['cards'] if card['card_name'] != card_name]
        
        # Collect synergy suggestions from all other cards
        suggestions = []
        suggestion_scores = defaultdict(int)
        
        for other_card in other_cards:
            synergies = self.card_db.get_card_synergies(other_card, min_cooccurrence=2)
            for synergy in synergies:
                if synergy['card_name'] != card_name and synergy['card_name'] not in other_cards:
                    suggestion_scores[synergy['card_name']] += synergy['cooccurrence']
                    if synergy['card_name'] not in [s['card_name'] for s in suggestions]:
                        suggestions.append(synergy)
        
        # Sort by accumulated score
        suggestions.sort(key=lambda x: suggestion_scores[x['card_name']], reverse=True)
        
        return suggestions[:10]
    
    def optimize_deck(self, deck_id: str) -> Dict:
        """Analyze deck and suggest optimizations based on tournament data."""
        analysis = self.analyzer.analyze_deck(deck_id)
        
        if 'error' in analysis:
            return analysis
        
        suggestions = {
            'warnings': [],
            'recommendations': [],
            'composition_analysis': analysis['composition']
        }
        
        # Check deck validity
        if not analysis['is_valid']:
            suggestions['warnings'].append(f"Deck has {analysis['total_cards']} cards (should be 60)")
        
        if not analysis['has_basic_pokemon']:
            suggestions['warnings'].append("Deck has no Pokemon cards")
        
        if not analysis['has_energy']:
            suggestions['warnings'].append("Deck has no Energy cards")
        
        # Composition recommendations
        pokemon_count = analysis['composition']['pokemon']['count']
        trainer_count = analysis['composition']['trainers']['count']
        energy_count = analysis['composition']['energy']['count']
        
        if pokemon_count < 10:
            suggestions['recommendations'].append("Consider adding more Pokemon (currently {})".format(pokemon_count))
        
        if trainer_count < 15:
            suggestions['recommendations'].append("Consider adding more Trainer cards for consistency")
        
        if energy_count < 8:
            suggestions['recommendations'].append("Consider adding more Energy cards")
        elif energy_count > 20:
            suggestions['recommendations'].append("Consider reducing Energy cards (currently {})".format(energy_count))
        
        return suggestions


def main():
    """Example usage of the AI deck builder."""
    print("=== Pokemon TCG AI Deck Builder ===\n")
    
    # Initialize database
    card_db = CardDatabase()
    card_db.connect()
    
    try:
        # Show card statistics
        print("📊 Card Usage Statistics:")
        top_cards = card_db.get_card_usage_stats(min_usage=1)[:10]
        for i, card in enumerate(top_cards, 1):
            print(f"  {i}. {card['card_name']} - Used in {card['deck_count']} decks")
        
        print("\n🏆 Winning Decks:")
        winning_decks = card_db.get_winning_decks(limit=5)
        for deck in winning_decks:
            print(f"  • {deck['player_name']} - {deck['event_title']}")
        
        # Analyze a deck
        print("\n🔍 Deck Analysis:")
        analyzer = DeckAnalyzer(card_db)
        
        decks = card_db.get_winning_decks(limit=1)
        if decks:
            deck_id = decks[0]['deck_id']
            analysis = analyzer.analyze_deck(deck_id)
            print(f"\nAnalyzing deck: {deck_id}")
            print(f"  Total cards: {analysis['total_cards']}")
            print(f"  Pokemon: {analysis['composition']['pokemon']['count']} ({analysis['composition']['pokemon']['unique']} unique)")
            print(f"  Trainers: {analysis['composition']['trainers']['count']} ({analysis['composition']['trainers']['unique']} unique)")
            print(f"  Energy: {analysis['composition']['energy']['count']} ({analysis['composition']['energy']['unique']} unique)")
            print(f"  Valid: {'✓' if analysis['is_valid'] else '✗'}")
        
        # Build a new deck
        print("\n🎴 Deck Builder Example:")
        builder = DeckBuilder(card_db)
        
        # Try to build a deck with sample core cards
        print("\nAttempting to build a deck...")
        print("  Core cards: ピカチュウex (2 copies)")
        
        new_deck = builder.build_deck_from_archetype(
            "Lightning Deck",
            [("ピカチュウex", 2)]
        )
        
        print(f"\n  Built deck with {new_deck['total']} cards:")
        for card in new_deck['cards'][:10]:  # Show first 10
            print(f"    • {card['card_name']} x{card['quantity']}")
        
        if len(new_deck['cards']) > 10:
            print(f"    ... and {len(new_deck['cards']) - 10} more cards")
        
        print("\n✓ AI Deck Builder initialized successfully!")
        
    finally:
        card_db.close()


if __name__ == '__main__':
    main()
