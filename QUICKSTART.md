# Quick Start Guide - Pokemon TCG AI System

Get started with the AI-powered Pokemon TCG deck builder and gameplay simulator in 5 minutes!

## Installation (30 seconds)

```bash
# 1. Clone the repository
git clone https://github.com/NeoSilver997/ptcg-product-info.git
cd ptcg-product-info

# 2. No external dependencies needed! AI system uses Python standard library.
#    (Optional: Install requirements.txt for web scraping features)

# 3. Verify installation
python ai_cli.py --help
```

## Your First Commands (2 minutes)

### 1. See Popular Cards
```bash
python ai_cli.py list-cards --limit 10
```
Shows the most used cards in competitive tournaments.

### 2. Analyze a Winning Deck
```bash
# First, get a deck ID
python ai_cli.py winning-decks --limit 5 --show-id

# Then analyze it (use actual deck ID from above)
python ai_cli.py analyze-deck deck_001 --detailed
```

### 3. Build Your First AI Deck
```bash
python ai_cli.py build-deck "Lightning" "ピカチュウex" --quantity 2
```
The AI will build a complete 60-card deck around your core card!

### 4. Find Card Synergies
```bash
python ai_cli.py synergies "ハイパーボール"
```
Discover cards that work well together.

### 5. Simulate Games
```bash
python ai_cli.py simulate --num-games 5
```
Watch AI vs AI gameplay and see statistics.

## Complete Workflow Example (3 minutes)

Run the comprehensive example that demonstrates all features:

```bash
python example_workflow.py
```

This will:
- ✅ Analyze tournament meta
- ✅ Build a competitive deck
- ✅ Find card synergies
- ✅ Optimize deck composition
- ✅ Simulate gameplay
- ✅ Save deck to file

## All Available Commands

```bash
# Card Analysis
python ai_cli.py list-cards [--min-usage N] [--limit N]
python ai_cli.py synergies "CardName" [--min-usage N]

# Deck Management
python ai_cli.py analyze-deck <deck_id> [--detailed]
python ai_cli.py optimize-deck <deck_id>
python ai_cli.py build-deck "Archetype" "CoreCard" [--quantity N] [--save file.json]
python ai_cli.py suggest-replacements <deck_id> "CardName"

# Tournament Data
python ai_cli.py winning-decks [--limit N] [--show-id]

# Gameplay
python ai_cli.py simulate [--num-games N]
```

## Using the Python API

### Example 1: Build and Analyze a Deck

```python
from ai_deck_builder import CardDatabase, DeckBuilder, DeckAnalyzer

# Connect to database
db = CardDatabase()
db.connect()

# Build a deck
builder = DeckBuilder(db)
deck = builder.build_deck_from_archetype(
    "Lightning Deck",
    [("ピカチュウex", 2)]
)

print(f"Built {deck['total']} card deck")

# Analyze it
analyzer = DeckAnalyzer(db)
analysis = analyzer.analyze_deck("deck_001")
print(f"Pokemon: {analysis['composition']['pokemon']['count']}")
print(f"Trainers: {analysis['composition']['trainers']['count']}")
print(f"Energy: {analysis['composition']['energy']['count']}")

db.close()
```

### Example 2: Simulate Games

```python
from ai_gameplay import GameSimulator

# Run simulations
simulator = GameSimulator()
results = simulator.run_simulations(num_games=10)

print(f"P1 wins: {results['p1_wins']}")
print(f"P2 wins: {results['p2_wins']}")
print(f"Avg turns: {results['avg_turns']:.1f}")
```

### Example 3: Find Card Synergies

```python
from ai_deck_builder import CardDatabase

db = CardDatabase()
db.connect()

# Find cards that work well together
synergies = db.get_card_synergies("ハイパーボール", min_cooccurrence=2)

for synergy in synergies[:10]:
    print(f"{synergy['card_name']}: {synergy['cooccurrence']} decks")

db.close()
```

## Common Use Cases

### Case 1: "I want to build a competitive deck"

```bash
# 1. See what's winning
python ai_cli.py winning-decks --limit 10

# 2. Check popular cards
python ai_cli.py list-cards --min-usage 5

# 3. Build your deck with AI
python ai_cli.py build-deck "YourArchetype" "CoreCard" --quantity 2 --save my_deck.json

# 4. Test it
python ai_cli.py simulate --num-games 10
```

### Case 2: "I want to improve my existing deck"

```bash
# 1. Analyze your deck
python ai_cli.py analyze-deck your_deck_id --detailed

# 2. Get optimization suggestions
python ai_cli.py optimize-deck your_deck_id

# 3. Find better alternatives
python ai_cli.py suggest-replacements your_deck_id "CardToReplace"
```

### Case 3: "I want to understand the meta"

```bash
# 1. Most used cards
python ai_cli.py list-cards --limit 30

# 2. Winning decks
python ai_cli.py winning-decks --limit 20

# 3. Card synergies
python ai_cli.py synergies "PopularCard"
```

## Tips for Best Results

### Building Decks
- Choose strong Pokemon ex cards as your core
- The AI automatically adds synergistic trainers and energy
- Typical good deck composition: 15 Pokemon, 30 Trainers, 15 Energy

### Analyzing Decks
- Use `--detailed` flag to see full card lists
- Check the optimization suggestions for improvements
- Compare your deck to winning tournament decks

### Simulating Games
- Run at least 10 games for reliable statistics
- Higher turn counts usually indicate defensive decks
- Win rates help evaluate deck strength

## Next Steps

1. **Read Full Documentation**: See `AI_SYSTEM_README.md` for complete details
2. **Explore Examples**: Run `python example_workflow.py` for guided tour
3. **Build Your Own**: Start with `python ai_cli.py build-deck`
4. **Contribute**: Improve AI algorithms and add features!

## Troubleshooting

### "Database not found"
Make sure you're in the correct directory with `ptcg_events.db` file.

### "No cards found"
The sample database has limited data. Import real tournament data using:
```bash
python import_events_to_sqlite.py
```

### "Command not found"
Make sure Python 3.7+ is installed and you're in the correct directory.
No external dependencies required - the AI system uses Python standard library only.

## Get Help

```bash
# General help
python ai_cli.py --help

# Command-specific help
python ai_cli.py build-deck --help
python ai_cli.py simulate --help
```

## Credits

This AI system analyzes real Pokemon TCG tournament data to provide intelligent deck building and gameplay recommendations.

**Enjoy building winning decks! 🎴🏆**
