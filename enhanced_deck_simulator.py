"""
Enhanced Pokemon TCG Deck Simulator with LLM Integration

This module provides advanced deck testing and simulation capabilities
using trained LLM models for strategic decision-making.
"""

import sqlite3
from typing import List, Dict, Optional
import logging
from collections import defaultdict
from ai_gameplay import GameSimulator, GameAI, GameState, GameRules
from llm_model_wrapper import PTCGLLMWrapper

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class EnhancedDeckSimulator:
    """Advanced deck simulator with tournament-based evaluation."""
    
    def __init__(self, event_db='ptcg_events.db', use_llm=False, llm_model_path=None):
        """
        Initialize the enhanced simulator.
        
        Args:
            event_db: Path to tournament database
            use_llm: Whether to use LLM for decision making
            llm_model_path: Path to trained LLM model
        """
        self.event_db_path = event_db
        self.conn = None
        self.use_llm = use_llm
        self.llm = None
        
        if use_llm:
            self.llm = PTCGLLMWrapper(model_path=llm_model_path, use_mock=(llm_model_path is None))
            logger.info("LLM integration enabled")
    
    def connect(self):
        """Connect to the database."""
        self.conn = sqlite3.connect(self.event_db_path)
        self.conn.row_factory = sqlite3.Row
        logger.info(f"Connected to database: {self.event_db_path}")
    
    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()
    
    def get_tournament_deck(self, deck_id: str) -> Dict:
        """Load a specific tournament deck."""
        # Get deck info with player name
        deck_query = """
            SELECT d.*, p.player_name
            FROM decks d
            JOIN players p ON d.player_id = p.player_id
            WHERE d.deck_id = ?
        """
        deck_cursor = self.conn.execute(deck_query, (deck_id,))
        deck_info = dict(deck_cursor.fetchone())
        
        # Get cards
        cards_query = "SELECT card_name, card_code, quantity FROM deck_cards WHERE deck_id = ?"
        cards_cursor = self.conn.execute(cards_query, (deck_id,))
        cards = [dict(row) for row in cards_cursor.fetchall()]
        
        return {
            'deck_id': deck_id,
            'player_name': deck_info['player_name'],
            'cards': cards,
            'total_cards': sum(card['quantity'] for card in cards)
        }
    
    def evaluate_deck_composition(self, cards: List[Dict]) -> Dict:
        """Evaluate deck composition and balance."""
        composition = {
            'pokemon': 0,
            'trainers': 0,
            'energy': 0,
            'supporters': 0,
            'items': 0,
            'total': 0
        }
        
        card_types = defaultdict(int)
        
        for card in cards:
            quantity = card['quantity']
            card_name = card['card_name']
            composition['total'] += quantity
            
            # Categorize
            if 'エネルギー' in card_name:
                composition['energy'] += quantity
                card_types['energy'] += 1
            elif any(kw in card_name for kw in ['博士', 'サポート', 'ボス', 'ナンジャモ', 'マリィ']):
                composition['trainers'] += quantity
                composition['supporters'] += quantity
                card_types['supporter'] += 1
            elif any(kw in card_name for kw in ['ボール', 'いれかえ', 'グッズ', 'スタジアム']):
                composition['trainers'] += quantity
                composition['items'] += quantity
                card_types['item'] += 1
            else:
                composition['pokemon'] += quantity
                card_types['pokemon'] += 1
        
        # Calculate balance score (optimal ratios)
        balance_score = 0
        if 12 <= composition['pokemon'] <= 18:
            balance_score += 30
        if 25 <= composition['trainers'] <= 32:
            balance_score += 40
        if 10 <= composition['energy'] <= 16:
            balance_score += 30
        
        return {
            'composition': composition,
            'card_types': dict(card_types),
            'balance_score': balance_score,
            'is_legal': composition['total'] == 60
        }
    
    def simulate_deck_matchup(self, deck1: Dict, deck2: Dict, num_games: int = 10) -> Dict:
        """Simulate matchup between two decks."""
        logger.info(f"Simulating {num_games} games between decks...")
        
        simulator = GameSimulator()
        results = {
            'deck1_wins': 0,
            'deck2_wins': 0,
            'draws': 0,
            'games': []
        }
        
        for i in range(num_games):
            result = simulator.simulate_game(max_turns=15)
            results['games'].append(result)
            
            if result['winner'] == 1:
                results['deck1_wins'] += 1
            elif result['winner'] == 2:
                results['deck2_wins'] += 1
            else:
                results['draws'] += 1
        
        # Calculate win rate
        total_decisive = results['deck1_wins'] + results['deck2_wins']
        results['deck1_winrate'] = (results['deck1_wins'] / total_decisive * 100) if total_decisive > 0 else 0
        
        return results
    
    def test_deck_against_meta(self, test_deck: Dict, num_opponents: int = 5, games_per_opponent: int = 10) -> Dict:
        """Test a deck against popular meta decks."""
        logger.info(f"Testing deck against {num_opponents} meta opponents...")
        
        # Get top meta decks
        meta_decks_query = """
            SELECT d.deck_id, d.player_name, COUNT(*) as usage
            FROM decks d
            JOIN deck_cards dc ON d.deck_id = dc.deck_id
            GROUP BY d.deck_id
            ORDER BY RANDOM()
            LIMIT ?
        """
        cursor = self.conn.execute(meta_decks_query, (num_opponents,))
        meta_decks = [dict(row) for row in cursor.fetchall()]
        
        overall_results = {
            'test_deck': test_deck,
            'total_games': 0,
            'total_wins': 0,
            'matchups': []
        }
        
        for meta_deck in meta_decks:
            opponent_deck = self.get_tournament_deck(meta_deck['deck_id'])
            matchup = self.simulate_deck_matchup(test_deck, opponent_deck, games_per_opponent)
            
            overall_results['total_games'] += games_per_opponent
            overall_results['total_wins'] += matchup['deck1_wins']
            overall_results['matchups'].append({
                'opponent': meta_deck['player_name'],
                'wins': matchup['deck1_wins'],
                'losses': matchup['deck2_wins'],
                'winrate': matchup['deck1_winrate']
            })
        
        # Calculate overall win rate
        overall_results['overall_winrate'] = (
            overall_results['total_wins'] / overall_results['total_games'] * 100
            if overall_results['total_games'] > 0 else 0
        )
        
        return overall_results
    
    def get_llm_deck_analysis(self, deck: Dict) -> str:
        """Get LLM analysis of a deck."""
        if not self.use_llm or not self.llm:
            return "LLM analysis not available. Enable with use_llm=True"
        
        # Format deck for LLM
        deck_str = f"Deck by {deck.get('player_name', 'Unknown')}:\n"
        for card in deck['cards'][:20]:  # First 20 cards
            deck_str += f"  {card['quantity']}x {card['card_name']}\n"
        
        analysis = self.llm.suggest_deck_improvements(deck['cards'])
        return analysis['suggestions']
    
    def optimize_deck_with_llm(self, deck: Dict) -> Dict:
        """Use LLM to suggest deck optimizations."""
        if not self.use_llm or not self.llm:
            return {
                'error': 'LLM not available',
                'original_deck': deck
            }
        
        # Get current composition
        evaluation = self.evaluate_deck_composition(deck['cards'])
        
        # Ask LLM for improvements
        prompt = f"""Analyze this Pokemon TCG deck:

Composition:
  Pokemon: {evaluation['composition']['pokemon']} cards
  Trainers: {evaluation['composition']['trainers']} cards
  Energy: {evaluation['composition']['energy']} cards
  Total: {evaluation['composition']['total']} cards

Balance Score: {evaluation['balance_score']}/100

Current cards:
"""
        for card in deck['cards'][:15]:
            prompt += f"  {card['quantity']}x {card['card_name']}\n"
        
        prompt += "\nSuggest specific improvements to make this deck more competitive."
        
        suggestions = self.llm.generate(prompt, max_length=600)
        
        return {
            'original_deck': deck,
            'evaluation': evaluation,
            'llm_suggestions': suggestions
        }
    
    def compare_decks(self, deck1: Dict, deck2: Dict) -> Dict:
        """Compare two decks and their strengths."""
        eval1 = self.evaluate_deck_composition(deck1['cards'])
        eval2 = self.evaluate_deck_composition(deck2['cards'])
        
        comparison = {
            'deck1': {
                'name': deck1.get('player_name', 'Deck 1'),
                'composition': eval1['composition'],
                'balance_score': eval1['balance_score']
            },
            'deck2': {
                'name': deck2.get('player_name', 'Deck 2'),
                'composition': eval2['composition'],
                'balance_score': eval2['balance_score']
            },
            'differences': {
                'pokemon_diff': eval1['composition']['pokemon'] - eval2['composition']['pokemon'],
                'trainer_diff': eval1['composition']['trainers'] - eval2['composition']['trainers'],
                'energy_diff': eval1['composition']['energy'] - eval2['composition']['energy']
            }
        }
        
        # LLM comparison if available
        if self.use_llm and self.llm:
            prompt = f"""Compare these two Pokemon TCG decks:

Deck 1 ({comparison['deck1']['name']}):
  Pokemon: {eval1['composition']['pokemon']}
  Trainers: {eval1['composition']['trainers']}
  Energy: {eval1['composition']['energy']}

Deck 2 ({comparison['deck2']['name']}):
  Pokemon: {eval2['composition']['pokemon']}
  Trainers: {eval2['composition']['trainers']}
  Energy: {eval2['composition']['energy']}

Which deck is better and why?"""
            
            comparison['llm_analysis'] = self.llm.generate(prompt, max_length=500)
        
        return comparison


class TournamentDeckAnalyzer:
    """Analyze patterns from tournament-winning decks."""
    
    def __init__(self, event_db='ptcg_events.db'):
        """Initialize the analyzer."""
        self.event_db_path = event_db
        self.conn = None
    
    def connect(self):
        """Connect to the database."""
        self.conn = sqlite3.connect(self.event_db_path)
        self.conn.row_factory = sqlite3.Row
    
    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()
    
    def get_winning_deck_patterns(self) -> Dict:
        """Analyze patterns in winning decks."""
        query = """
            SELECT 
                d.deck_id,
                COUNT(DISTINCT dc.card_id) as unique_cards,
                SUM(CASE WHEN dc.card_name LIKE '%ex%' THEN dc.quantity ELSE 0 END) as ex_pokemon,
                SUM(CASE WHEN dc.card_name LIKE '%エネルギー%' THEN dc.quantity ELSE 0 END) as energy_cards
            FROM decks d
            JOIN deck_cards dc ON d.deck_id = dc.deck_id
            WHERE d.rank = '1位' OR d.rank = '優勝'
            GROUP BY d.deck_id
        """
        cursor = self.conn.execute(query)
        decks = [dict(row) for row in cursor.fetchall()]
        
        # Calculate averages
        avg_unique = sum(d['unique_cards'] for d in decks) / len(decks) if decks else 0
        avg_ex = sum(d['ex_pokemon'] for d in decks) / len(decks) if decks else 0
        avg_energy = sum(d['energy_cards'] for d in decks) / len(decks) if decks else 0
        
        return {
            'total_analyzed': len(decks),
            'avg_unique_cards': avg_unique,
            'avg_ex_pokemon': avg_ex,
            'avg_energy_cards': avg_energy,
            'patterns': {
                'consistent_uniqueness': 20 <= avg_unique <= 30,
                'moderate_ex_usage': 3 <= avg_ex <= 6,
                'standard_energy': 10 <= avg_energy <= 16
            }
        }
    
    def find_winning_card_combinations(self, min_cooccurrence: int = 3) -> List[Dict]:
        """Find card combinations that appear in winning decks."""
        query = """
            SELECT 
                dc1.card_name as card1,
                dc2.card_name as card2,
                COUNT(DISTINCT dc1.deck_id) as cooccurrence
            FROM deck_cards dc1
            JOIN deck_cards dc2 ON dc1.deck_id = dc2.deck_id AND dc1.card_id < dc2.card_id
            JOIN decks d ON dc1.deck_id = d.deck_id
            WHERE (d.rank = '1位' OR d.rank = '優勝')
            AND dc1.card_name IS NOT NULL
            AND dc2.card_name IS NOT NULL
            GROUP BY dc1.card_id, dc2.card_id
            HAVING cooccurrence >= ?
            ORDER BY cooccurrence DESC
            LIMIT 20
        """
        cursor = self.conn.execute(query, (min_cooccurrence,))
        combinations = [dict(row) for row in cursor.fetchall()]
        
        logger.info(f"Found {len(combinations)} winning card combinations")
        return combinations


def main():
    """Example usage of the enhanced deck simulator."""
    print("=" * 60)
    print("Enhanced Pokemon TCG Deck Simulator")
    print("=" * 60)
    print()
    
    # Initialize simulator
    simulator = EnhancedDeckSimulator(use_llm=True)
    simulator.connect()
    
    print("📊 Analyzing tournament patterns...")
    analyzer = TournamentDeckAnalyzer()
    analyzer.connect()
    
    patterns = analyzer.get_winning_deck_patterns()
    print(f"\nWinning Deck Patterns (from {patterns['total_analyzed']} decks):")
    print(f"  Average unique cards: {patterns['avg_unique_cards']:.1f}")
    print(f"  Average Pokemon ex: {patterns['avg_ex_pokemon']:.1f}")
    print(f"  Average Energy cards: {patterns['avg_energy_cards']:.1f}")
    
    print("\n🔗 Top Winning Card Combinations:")
    combinations = analyzer.find_winning_card_combinations(min_cooccurrence=2)
    for i, combo in enumerate(combinations[:5], 1):
        print(f"  {i}. {combo['card1']} + {combo['card2']} ({combo['cooccurrence']} decks)")
    
    print("\n🎮 Testing deck simulation...")
    # Get a sample deck
    cursor = simulator.conn.execute("SELECT deck_id FROM decks LIMIT 1")
    deck_id = cursor.fetchone()[0]
    test_deck = simulator.get_tournament_deck(deck_id)
    
    print(f"\nEvaluating deck: {test_deck['player_name']}")
    evaluation = simulator.evaluate_deck_composition(test_deck['cards'])
    print(f"  Pokemon: {evaluation['composition']['pokemon']}")
    print(f"  Trainers: {evaluation['composition']['trainers']}")
    print(f"  Energy: {evaluation['composition']['energy']}")
    print(f"  Balance Score: {evaluation['balance_score']}/100")
    print(f"  Legal: {'✓' if evaluation['is_legal'] else '✗'}")
    
    # LLM analysis
    if simulator.use_llm:
        print("\n🤖 LLM Deck Analysis:")
        print("-" * 40)
        optimization = simulator.optimize_deck_with_llm(test_deck)
        print(optimization['llm_suggestions'][:300] + "...")
    
    analyzer.close()
    simulator.close()
    
    print("\n" + "=" * 60)
    print("✓ Enhanced Deck Simulator ready for tournament preparation!")
    print()


if __name__ == '__main__':
    main()
