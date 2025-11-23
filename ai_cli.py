"""
Command-line interface for Pokemon TCG AI system.

Provides interactive tools for:
- Deck building and analysis
- Card recommendations
- Gameplay simulation
- Tournament data exploration
"""

import sys
import argparse
from typing import Optional
import json

from ai_deck_builder import CardDatabase, DeckAnalyzer, DeckBuilder
from ai_gameplay import GameSimulator, GameAI, GameState


class PTCGAI_CLI:
    """Command-line interface for PTCG AI system."""
    
    def __init__(self, db_path='ptcg_events.db'):
        """Initialize CLI with database."""
        self.db_path = db_path
        self.card_db = None
        self.analyzer = None
        self.builder = None
    
    def connect(self):
        """Connect to database and initialize components."""
        self.card_db = CardDatabase(self.db_path)
        self.card_db.connect()
        self.analyzer = DeckAnalyzer(self.card_db)
        self.builder = DeckBuilder(self.card_db)
        print(f"✓ Connected to database: {self.db_path}\n")
    
    def close(self):
        """Close database connection."""
        if self.card_db:
            self.card_db.close()
    
    def cmd_list_cards(self, args):
        """List all cards with usage statistics."""
        print("📊 Card Usage Statistics\n")
        
        min_usage = args.min_usage if hasattr(args, 'min_usage') else 1
        limit = args.limit if hasattr(args, 'limit') else 20
        
        cards = self.card_db.get_card_usage_stats(min_usage=min_usage)[:limit]
        
        if not cards:
            print("No cards found in database.")
            return
        
        print(f"{'Rank':<6} {'Card Name':<40} {'Decks':<10} {'Avg Qty':<10}")
        print("-" * 70)
        
        for i, card in enumerate(cards, 1):
            print(f"{i:<6} {card['card_name']:<40} {card['deck_count']:<10} {card['avg_quantity']:<10.1f}")
        
        print(f"\nShowing {len(cards)} cards (min usage: {min_usage} decks)")
    
    def cmd_analyze_deck(self, args):
        """Analyze a specific deck."""
        deck_id = args.deck_id
        
        print(f"🔍 Analyzing Deck: {deck_id}\n")
        
        analysis = self.analyzer.analyze_deck(deck_id)
        
        if 'error' in analysis:
            print(f"Error: {analysis['error']}")
            return
        
        info = analysis['deck_info']
        comp = analysis['composition']
        
        print(f"Event: {info.get('event_title', 'N/A')}")
        print(f"Player: {info.get('player_name', 'N/A')}")
        print(f"Rank: {info.get('rank', 'N/A')}")
        print(f"Date: {info.get('event_date', 'N/A')}\n")
        
        print(f"Total Cards: {analysis['total_cards']}/60")
        print(f"Valid Deck: {'✓' if analysis['is_valid'] else '✗'}\n")
        
        print("Composition:")
        print(f"  Pokemon:  {comp['pokemon']['count']:>3} cards ({comp['pokemon']['unique']} unique)")
        print(f"  Trainers: {comp['trainers']['count']:>3} cards ({comp['trainers']['unique']} unique)")
        print(f"  Energy:   {comp['energy']['count']:>3} cards ({comp['energy']['unique']} unique)\n")
        
        if args.detailed:
            print("Pokemon Cards:")
            for card in comp['pokemon']['cards']:
                print(f"  • {card['card_name']} x{card['quantity']}")
            
            print("\nTrainer Cards:")
            for card in comp['trainers']['cards']:
                print(f"  • {card['card_name']} x{card['quantity']}")
            
            print("\nEnergy Cards:")
            for card in comp['energy']['cards']:
                print(f"  • {card['card_name']} x{card['quantity']}")
    
    def cmd_optimize_deck(self, args):
        """Get optimization suggestions for a deck."""
        deck_id = args.deck_id
        
        print(f"⚙️  Optimizing Deck: {deck_id}\n")
        
        suggestions = self.builder.optimize_deck(deck_id)
        
        if 'error' in suggestions:
            print(f"Error: {suggestions['error']}")
            return
        
        if suggestions['warnings']:
            print("⚠️  Warnings:")
            for warning in suggestions['warnings']:
                print(f"  • {warning}")
            print()
        
        if suggestions['recommendations']:
            print("💡 Recommendations:")
            for rec in suggestions['recommendations']:
                print(f"  • {rec}")
            print()
        
        comp = suggestions['composition_analysis']
        print("Composition Analysis:")
        print(f"  Pokemon:  {comp['pokemon']['count']} cards ({comp['pokemon']['unique']} unique)")
        print(f"  Trainers: {comp['trainers']['count']} cards ({comp['trainers']['unique']} unique)")
        print(f"  Energy:   {comp['energy']['count']} cards ({comp['energy']['unique']} unique)")
    
    def cmd_build_deck(self, args):
        """Build a new deck with AI assistance."""
        print("🎴 Building New Deck\n")
        
        archetype = args.archetype
        core_card = args.core_card
        quantity = args.quantity
        
        print(f"Archetype: {archetype}")
        print(f"Core Card: {core_card} x{quantity}\n")
        
        deck = self.builder.build_deck_from_archetype(
            archetype,
            [(core_card, quantity)]
        )
        
        print(f"✓ Built deck with {deck['total']} cards:\n")
        
        for card in deck['cards']:
            print(f"  • {card['card_name']} x{card['quantity']}")
        
        if args.save:
            filename = args.save
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(deck, f, ensure_ascii=False, indent=2)
            print(f"\n✓ Deck saved to: {filename}")
    
    def cmd_find_synergies(self, args):
        """Find cards that synergize well with a given card."""
        card_name = args.card_name
        
        print(f"🔗 Finding synergies for: {card_name}\n")
        
        synergies = self.card_db.get_card_synergies(card_name, min_cooccurrence=args.min_usage)
        
        if not synergies:
            print(f"No synergies found for '{card_name}'")
            return
        
        print(f"{'Card Name':<40} {'Co-occurrence':<15} {'Avg Quantity':<15}")
        print("-" * 70)
        
        for synergy in synergies:
            print(f"{synergy['card_name']:<40} {synergy['cooccurrence']:<15} {synergy['avg_quantity']:<15.1f}")
    
    def cmd_winning_decks(self, args):
        """List winning tournament decks."""
        print("🏆 Tournament Winning Decks\n")
        
        limit = args.limit if hasattr(args, 'limit') else 10
        decks = self.card_db.get_winning_decks(limit=limit)
        
        if not decks:
            print("No winning decks found.")
            return
        
        print(f"{'Date':<12} {'Player':<20} {'Event':<40}")
        print("-" * 75)
        
        for deck in decks:
            date = deck.get('event_date', 'N/A')
            player = deck.get('player_name', 'N/A')[:20]
            event = deck.get('event_title', 'N/A')[:40]
            print(f"{date:<12} {player:<20} {event:<40}")
            
            if args.show_id:
                print(f"  Deck ID: {deck['deck_id']}")
    
    def cmd_simulate_game(self, args):
        """Simulate Pokemon TCG games."""
        print("🎮 Simulating Pokemon TCG Games\n")
        
        num_games = args.num_games if hasattr(args, 'num_games') else 3
        
        simulator = GameSimulator()
        results = simulator.run_simulations(num_games=num_games)
        
        print("\n📊 Simulation Results:")
        print(f"  Games played: {results['games_played']}")
        print(f"  Player 1 wins: {results['p1_wins']} ({results['p1_wins']/results['games_played']*100:.1f}%)")
        print(f"  Player 2 wins: {results['p2_wins']} ({results['p2_wins']/results['games_played']*100:.1f}%)")
        print(f"  Draws: {results['draws']}")
        print(f"  Average turns: {results['avg_turns']:.1f}")
    
    def cmd_suggest_replacements(self, args):
        """Suggest card replacements for a deck."""
        deck_id = args.deck_id
        card_name = args.card_name
        
        print(f"🔄 Suggesting replacements for '{card_name}' in deck {deck_id}\n")
        
        suggestions = self.builder.suggest_card_replacements(deck_id, card_name)
        
        if not suggestions:
            print("No replacement suggestions found.")
            return
        
        print(f"{'Card Name':<40} {'Co-occurrence':<15} {'Avg Quantity':<15}")
        print("-" * 70)
        
        for suggestion in suggestions:
            print(f"{suggestion['card_name']:<40} {suggestion['cooccurrence']:<15} {suggestion['avg_quantity']:<15.1f}")


def create_parser():
    """Create argument parser for CLI."""
    parser = argparse.ArgumentParser(
        description='Pokemon TCG AI - Deck Builder and Gameplay Simulator',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # List top 20 most used cards
  python ai_cli.py list-cards
  
  # Analyze a specific deck
  python ai_cli.py analyze-deck deck_001 --detailed
  
  # Build a new deck
  python ai_cli.py build-deck "Lightning" "ピカチュウex" --quantity 2
  
  # Find card synergies
  python ai_cli.py synergies "ハイパーボール"
  
  # Simulate games
  python ai_cli.py simulate --num-games 5
  
  # List winning decks
  python ai_cli.py winning-decks --limit 10
        """
    )
    
    parser.add_argument('--db', default='ptcg_events.db', help='Database path')
    
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')
    
    # list-cards command
    list_parser = subparsers.add_parser('list-cards', help='List cards with usage statistics')
    list_parser.add_argument('--min-usage', type=int, default=1, help='Minimum deck usage')
    list_parser.add_argument('--limit', type=int, default=20, help='Number of cards to show')
    
    # analyze-deck command
    analyze_parser = subparsers.add_parser('analyze-deck', help='Analyze a deck')
    analyze_parser.add_argument('deck_id', help='Deck ID to analyze')
    analyze_parser.add_argument('--detailed', action='store_true', help='Show full card list')
    
    # optimize-deck command
    optimize_parser = subparsers.add_parser('optimize-deck', help='Get deck optimization suggestions')
    optimize_parser.add_argument('deck_id', help='Deck ID to optimize')
    
    # build-deck command
    build_parser = subparsers.add_parser('build-deck', help='Build a new deck')
    build_parser.add_argument('archetype', help='Deck archetype name')
    build_parser.add_argument('core_card', help='Core card name')
    build_parser.add_argument('--quantity', type=int, default=2, help='Quantity of core card')
    build_parser.add_argument('--save', help='Save deck to JSON file')
    
    # synergies command
    synergies_parser = subparsers.add_parser('synergies', help='Find card synergies')
    synergies_parser.add_argument('card_name', help='Card name')
    synergies_parser.add_argument('--min-usage', type=int, default=2, help='Minimum co-occurrence')
    
    # winning-decks command
    winning_parser = subparsers.add_parser('winning-decks', help='List winning tournament decks')
    winning_parser.add_argument('--limit', type=int, default=10, help='Number of decks to show')
    winning_parser.add_argument('--show-id', action='store_true', help='Show deck IDs')
    
    # simulate command
    simulate_parser = subparsers.add_parser('simulate', help='Simulate Pokemon TCG games')
    simulate_parser.add_argument('--num-games', type=int, default=3, help='Number of games to simulate')
    
    # suggest-replacements command
    replace_parser = subparsers.add_parser('suggest-replacements', help='Suggest card replacements')
    replace_parser.add_argument('deck_id', help='Deck ID')
    replace_parser.add_argument('card_name', help='Card to replace')
    
    return parser


def main():
    """Main CLI entry point."""
    parser = create_parser()
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 0
    
    cli = PTCGAI_CLI(db_path=args.db)
    
    try:
        cli.connect()
        
        # Execute command
        command_map = {
            'list-cards': cli.cmd_list_cards,
            'analyze-deck': cli.cmd_analyze_deck,
            'optimize-deck': cli.cmd_optimize_deck,
            'build-deck': cli.cmd_build_deck,
            'synergies': cli.cmd_find_synergies,
            'winning-decks': cli.cmd_winning_decks,
            'simulate': cli.cmd_simulate_game,
            'suggest-replacements': cli.cmd_suggest_replacements,
        }
        
        command_func = command_map.get(args.command)
        if command_func:
            command_func(args)
        else:
            print(f"Unknown command: {args.command}")
            return 1
        
        return 0
    
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    finally:
        cli.close()


if __name__ == '__main__':
    sys.exit(main())
