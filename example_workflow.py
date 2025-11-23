"""
Example: Complete workflow using Pokemon TCG AI system.

This example demonstrates:
1. Loading and analyzing tournament data
2. Building a competitive deck
3. Optimizing the deck based on AI suggestions
4. Simulating gameplay
5. Evaluating performance
"""

from ai_deck_builder import CardDatabase, DeckAnalyzer, DeckBuilder
from ai_gameplay import GameSimulator
import json


def main():
    """Run complete AI workflow example."""
    
    print("=" * 70)
    print("Pokemon TCG AI System - Complete Workflow Example")
    print("=" * 70)
    print()
    
    # Step 1: Connect to tournament database
    print("Step 1: Connecting to tournament database...")
    card_db = CardDatabase('ptcg_events.db')
    card_db.connect()
    print("✓ Connected successfully\n")
    
    # Step 2: Explore the meta - what are popular cards?
    print("Step 2: Analyzing competitive meta...")
    print("-" * 70)
    top_cards = card_db.get_card_usage_stats(min_usage=1)[:10]
    print(f"\nTop 10 Most Used Cards:")
    for i, card in enumerate(top_cards, 1):
        print(f"  {i:2}. {card['card_name']:30} - {card['deck_count']:2} decks")
    print()
    
    # Step 3: Check winning decks
    print("Step 3: Examining winning decks...")
    print("-" * 70)
    winning_decks = card_db.get_winning_decks(limit=5)
    print(f"\nRecent Tournament Winners:")
    for deck in winning_decks:
        print(f"  • {deck.get('player_name', 'Unknown'):15} - {deck.get('event_title', 'N/A')}")
        print(f"    Deck ID: {deck['deck_id']}")
    print()
    
    # Step 4: Analyze a winning deck
    if winning_decks:
        print("Step 4: Analyzing a winning deck in detail...")
        print("-" * 70)
        analyzer = DeckAnalyzer(card_db)
        deck_id = winning_decks[0]['deck_id']
        
        analysis = analyzer.analyze_deck(deck_id)
        
        print(f"\nDeck: {deck_id}")
        print(f"Total Cards: {analysis['total_cards']}/60")
        print(f"Valid: {'✓' if analysis['is_valid'] else '✗'}")
        print(f"\nComposition:")
        print(f"  Pokemon:  {analysis['composition']['pokemon']['count']:2} cards ({analysis['composition']['pokemon']['unique']} unique)")
        print(f"  Trainers: {analysis['composition']['trainers']['count']:2} cards ({analysis['composition']['trainers']['unique']} unique)")
        print(f"  Energy:   {analysis['composition']['energy']['count']:2} cards ({analysis['composition']['energy']['unique']} unique)")
        print()
    
    # Step 5: Build a new deck with AI
    print("Step 5: Building a new deck with AI assistance...")
    print("-" * 70)
    builder = DeckBuilder(card_db)
    
    # Get the first Pokemon from top cards as core
    core_card = None
    for card in top_cards:
        if 'ex' in card['card_name'] or 'エネルギー' not in card['card_name']:
            core_card = card['card_name']
            break
    
    if not core_card:
        core_card = "ピカチュウex"
    
    print(f"\nBuilding deck around: {core_card}")
    
    new_deck = builder.build_deck_from_archetype(
        f"{core_card} Deck",
        [(core_card, 2)]
    )
    
    print(f"✓ Built deck with {new_deck['total']} cards")
    print(f"\nSample cards (first 10):")
    for i, card in enumerate(new_deck['cards'][:10], 1):
        print(f"  {i:2}. {card['card_name']:30} x{card['quantity']}")
    
    if len(new_deck['cards']) > 10:
        print(f"  ... and {len(new_deck['cards']) - 10} more types")
    print()
    
    # Step 6: Get card synergies
    print("Step 6: Finding card synergies...")
    print("-" * 70)
    
    # Pick a popular trainer card
    trainer_card = None
    for card in top_cards:
        name = card['card_name']
        # Use same categorization as deck analyzer
        if any(keyword in name for keyword in ['ボール', 'ボス', 'グッズ', 'サポート']):
            trainer_card = card['card_name']
            break
    
    if trainer_card:
        print(f"\nCards that work well with: {trainer_card}")
        synergies = card_db.get_card_synergies(trainer_card, min_cooccurrence=1)[:5]
        
        for i, synergy in enumerate(synergies, 1):
            print(f"  {i}. {synergy['card_name']:30} (appears together {synergy['cooccurrence']}x)")
    print()
    
    # Step 7: Optimize an existing deck
    if winning_decks:
        print("Step 7: Getting AI optimization suggestions...")
        print("-" * 70)
        deck_id = winning_decks[0]['deck_id']
        
        suggestions = builder.optimize_deck(deck_id)
        
        if suggestions['warnings']:
            print("\n⚠️  Warnings:")
            for warning in suggestions['warnings']:
                print(f"    • {warning}")
        
        if suggestions['recommendations']:
            print("\n💡 AI Recommendations:")
            for rec in suggestions['recommendations']:
                print(f"    • {rec}")
        
        if not suggestions['warnings'] and not suggestions['recommendations']:
            print("\n✓ Deck is well-optimized! No issues found.")
        print()
    
    # Step 8: Simulate gameplay
    print("Step 8: Simulating AI vs AI gameplay...")
    print("-" * 70)
    
    simulator = GameSimulator()
    print("\nRunning 3 game simulations...")
    
    results = simulator.run_simulations(num_games=3)
    
    print(f"\n📊 Results:")
    print(f"  Games Played:  {results['games_played']}")
    print(f"  Player 1 Wins: {results['p1_wins']} ({results['p1_wins']/results['games_played']*100:.0f}%)")
    print(f"  Player 2 Wins: {results['p2_wins']} ({results['p2_wins']/results['games_played']*100:.0f}%)")
    print(f"  Draws:         {results['draws']}")
    print(f"  Avg Turns:     {results['avg_turns']:.1f}")
    print()
    
    # Step 9: Save built deck to file
    print("Step 9: Saving deck to file...")
    print("-" * 70)
    
    deck_filename = "ai_built_deck.json"
    with open(deck_filename, 'w', encoding='utf-8') as f:
        json.dump(new_deck, f, ensure_ascii=False, indent=2)
    
    print(f"✓ Deck saved to: {deck_filename}")
    print()
    
    # Summary
    print("=" * 70)
    print("Workflow Complete!")
    print("=" * 70)
    print("\nThe AI system has:")
    print("  ✓ Analyzed tournament meta and winning strategies")
    print("  ✓ Built a competitive deck using data-driven insights")
    print("  ✓ Identified card synergies and optimization opportunities")
    print("  ✓ Simulated gameplay to test strategies")
    print("  ✓ Saved the deck for future use")
    print()
    print("Next steps:")
    print("  • Use 'python ai_cli.py' for interactive deck building")
    print("  • Run more simulations with different AI difficulties")
    print("  • Analyze your own decks with 'ai_cli.py analyze-deck'")
    print("  • Export decks for use in Pokemon TCG Online")
    print()
    
    # Cleanup
    card_db.close()


if __name__ == '__main__':
    main()
