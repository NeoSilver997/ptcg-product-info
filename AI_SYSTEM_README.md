# Pokemon TCG AI System

A local AI-powered system for Pokemon Trading Card Game deck building, analysis, and gameplay simulation.

## Features

### 🎴 Deck Building AI
- **Smart Deck Construction**: Build competitive decks using tournament data patterns
- **Card Synergy Analysis**: Discover cards that work well together based on real tournament results
- **Deck Optimization**: Get AI-powered suggestions to improve existing decks
- **Archetype Recognition**: Identify and build around popular deck archetypes

### 🔍 Deck Analysis
- **Composition Analysis**: Breakdown of Pokemon, Trainer, and Energy cards
- **Validation**: Ensure decks meet tournament rules (60 cards, max 4 copies)
- **Comparison Tools**: Compare decks and find similarities/differences
- **Tournament Performance**: Analyze winning deck patterns

### 🎮 Gameplay Simulation
- **AI Opponents**: Play against AI with adjustable difficulty (easy, normal, hard)
- **Game State Management**: Full game state tracking and move validation
- **Move Evaluation**: Heuristic-based AI that evaluates and chooses optimal moves
- **Strategic Recommendations**: Get AI suggestions for in-game decisions

### 📊 Data-Driven Insights
- **Tournament Database**: Access to real tournament results and winning decks
- **Card Usage Statistics**: See which cards are most popular in competitive play
- **Meta Analysis**: Understand current competitive trends
- **Synergy Mining**: Discover card combinations from tournament data

## Installation

### Prerequisites
- Python 3.7 or higher
- SQLite3 (included with Python)

### Setup

1. Clone the repository:
```bash
git clone https://github.com/NeoSilver997/ptcg-product-info.git
cd ptcg-product-info
```

2. The AI system uses only Python standard library - no external dependencies needed!
   (Optional: Install requirements.txt for web scraping features)

3. The system works with the existing `ptcg_events.db` database that contains tournament data.

## Usage

The system provides three main interfaces:

### 1. Command-Line Interface (CLI)

The CLI provides quick access to all features:

```bash
# List most used cards
python ai_cli.py list-cards

# Analyze a specific deck
python ai_cli.py analyze-deck deck_001 --detailed

# Build a new deck
python ai_cli.py build-deck "Lightning Deck" "ピカチュウex" --quantity 2

# Find card synergies
python ai_cli.py synergies "ハイパーボール"

# Get deck optimization suggestions
python ai_cli.py optimize-deck deck_001

# Simulate games
python ai_cli.py simulate --num-games 5

# List winning tournament decks
python ai_cli.py winning-decks --limit 10

# Suggest card replacements
python ai_cli.py suggest-replacements deck_001 "ポケモンいれかえ"
```

### 2. Deck Builder API (Python)

Use the deck builder programmatically:

```python
from ai_deck_builder import CardDatabase, DeckAnalyzer, DeckBuilder

# Initialize
card_db = CardDatabase()
card_db.connect()
builder = DeckBuilder(card_db)

# Build a deck
deck = builder.build_deck_from_archetype(
    "Lightning Deck",
    [("ピカチュウex", 2)]
)

# Analyze a deck
analyzer = DeckAnalyzer(card_db)
analysis = analyzer.analyze_deck("deck_001")

# Find synergies
synergies = card_db.get_card_synergies("ハイパーボール", min_cooccurrence=5)

# Get optimization suggestions
suggestions = builder.optimize_deck("deck_001")

card_db.close()
```

### 3. Gameplay API (Python)

Simulate games and test strategies:

```python
from ai_gameplay import GameSimulator, GameAI, GameState

# Run game simulations
simulator = GameSimulator()
results = simulator.run_simulations(num_games=10)

print(f"Player 1 wins: {results['p1_wins']}")
print(f"Player 2 wins: {results['p2_wins']}")
print(f"Average turns: {results['avg_turns']:.1f}")

# Create AI players
ai_easy = GameAI(difficulty="easy")
ai_hard = GameAI(difficulty="hard")

# Play a turn
state = GameState()
state = ai_hard.play_turn(state)
```

## Architecture

### Core Components

1. **CardDatabase** (`ai_deck_builder.py`)
   - Manages tournament data and card statistics
   - Provides card usage analytics
   - Finds card synergies from tournament results

2. **DeckAnalyzer** (`ai_deck_builder.py`)
   - Analyzes deck composition
   - Validates deck legality
   - Compares decks
   - Determines deck archetypes

3. **DeckBuilder** (`ai_deck_builder.py`)
   - Builds complete 60-card decks
   - Uses tournament patterns for card selection
   - Suggests optimizations and replacements
   - Maintains deck validity constraints

4. **GameAI** (`ai_gameplay.py`)
   - Evaluates possible moves
   - Makes strategic decisions
   - Supports multiple difficulty levels
   - Learns from game patterns

5. **GameSimulator** (`ai_gameplay.py`)
   - Simulates complete games
   - Tracks game statistics
   - Tests deck performance
   - Provides win rate analysis

### Data Flow

```
Tournament Data (ptcg_events.db)
        ↓
CardDatabase (loads card stats & synergies)
        ↓
DeckBuilder (builds & optimizes decks)
        ↓
GameAI (plays games with built decks)
        ↓
GameSimulator (evaluates performance)
```

## AI Methodology

### Deck Building AI

The deck building AI uses a **data-driven heuristic approach**:

1. **Core Card Selection**: User specifies key cards for the deck archetype
2. **Synergy Discovery**: AI finds cards that frequently appear with core cards in tournament data
3. **Staple Cards**: AI adds commonly used support cards (e.g., search cards, draw support)
4. **Validation**: Ensures deck meets all rules (60 cards, max 4 copies)

**Algorithm**:
```
1. Start with core cards (e.g., 2x Pikachu ex)
2. Query database for cards that appear in decks with core cards
3. Sort candidates by co-occurrence frequency
4. Add high-scoring cards up to 60 total
5. Fill remaining slots with meta staples
6. Validate final deck composition
```

### Gameplay AI

The gameplay AI uses **heuristic evaluation** with configurable difficulty:

**Move Evaluation Weights**:
- Damage potential: 1.0
- Board presence: 0.8
- Card advantage: 0.7
- Energy efficiency: 0.6
- Prize trade: 1.5

**Decision Making**:
```
For each possible move:
  1. Calculate move score based on weights
  2. Consider game state context
  3. Prioritize winning moves
  4. Select highest scoring move (with randomness for lower difficulties)
```

**Difficulty Levels**:
- **Easy**: Random move selection
- **Normal**: 80% optimal moves, 20% random
- **Hard**: Always optimal moves

## Database Schema

The system uses tournament data from `ptcg_events.db`:

### Key Tables
- **events**: Tournament information
- **players**: Player profiles
- **decks**: Complete deck lists
- **deck_cards**: Individual cards in each deck (60 per deck)
- **card_mappings**: Japanese ⇄ Chinese card translations

### Example Queries

```sql
-- Find most used cards
SELECT card_name, COUNT(DISTINCT deck_id) as usage
FROM deck_cards
GROUP BY card_id
ORDER BY usage DESC
LIMIT 20;

-- Find card synergies
SELECT dc2.card_name, COUNT(*) as cooccurrence
FROM deck_cards dc1
JOIN deck_cards dc2 ON dc1.deck_id = dc2.deck_id
WHERE dc1.card_name = 'ハイパーボール'
AND dc2.card_name != 'ハイパーボール'
GROUP BY dc2.card_name
ORDER BY cooccurrence DESC;
```

## Performance

- **Database Queries**: Sub-second for most operations
- **Deck Building**: 1-2 seconds for complete 60-card deck
- **Game Simulation**: ~0.5 seconds per game
- **Card Analysis**: Instant for cached results

## Limitations

### Current Implementation
- **Simplified Game Rules**: Basic game mechanics only (no complex effects)
- **No Real-Time Play**: Not connected to official Pokemon TCG Online
- **Local Data Only**: Uses tournament data in database (no web scraping during use)
- **Japanese Card Names**: Primary support for Japanese cards (Chinese translations available)

### Future Enhancements
- Machine learning models for move prediction
- Advanced game state evaluation
- Real-time meta tracking
- Web-based interface
- Deck export to PTCG Online format
- More sophisticated AI strategies

## Examples

### Example 1: Build a Competitive Deck

```bash
# Build a Lightning-type deck
python ai_cli.py build-deck "Lightning" "ピカチュウex" --quantity 2 --save lightning_deck.json

# Analyze the built deck
python ai_cli.py analyze-deck <deck_id> --detailed

# Test it in simulations
python ai_cli.py simulate --num-games 10
```

### Example 2: Optimize Existing Deck

```bash
# Get optimization suggestions
python ai_cli.py optimize-deck deck_001

# Find better alternatives for a card
python ai_cli.py suggest-replacements deck_001 "ポケモンいれかえ"

# Check synergies
python ai_cli.py synergies "ピカチュウex"
```

### Example 3: Meta Analysis

```bash
# See what's winning
python ai_cli.py winning-decks --limit 20 --show-id

# Check popular cards
python ai_cli.py list-cards --min-usage 5 --limit 30

# Analyze a winning deck
python ai_cli.py analyze-deck <winning_deck_id> --detailed
```

## Testing

Run the test suite:

```bash
# Test deck builder
python ai_deck_builder.py

# Test gameplay engine
python ai_gameplay.py

# Test CLI
python ai_cli.py --help
python ai_cli.py list-cards
python ai_cli.py simulate --num-games 3
```

## Contributing

This is an AI-powered system for Pokemon TCG analysis. Contributions welcome for:
- Improved AI algorithms
- Additional game mechanics
- Performance optimizations
- Documentation improvements

## Credits

- **Data Source**: Official Pokemon TCG tournament results from Japan
- **Database**: SQLite with tournament and deck data
- **AI Framework**: Custom heuristic-based system with tournament data mining

## License

MIT License - See LICENSE file for details

---

**Note**: This is an analysis and simulation tool. It is not affiliated with or endorsed by The Pokemon Company, Nintendo, or Creatures Inc. All Pokemon TCG card names and trademarks are property of their respective owners.
