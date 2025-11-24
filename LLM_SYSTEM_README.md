# Pokemon TCG LLM Training System

Complete system for training local Large Language Models (LLMs) to understand Pokemon Trading Card Game, build competitive decks, and simulate gameplay for tournament preparation.

## 🎯 Overview

This system bridges tournament data with LLM technology to create an AI that can:
- **Understand Cards**: Learn all Pokemon TCG cards from tournament usage
- **Know Rules**: Master complete Pokemon TCG ruleset
- **Build Decks**: Create competitive 60-card decks based on tournament patterns
- **Simulate Gameplay**: Test deck performance and suggest strategic improvements

## 🚀 Quick Start

### 1. Generate Training Data

```bash
python llm_training_data_generator.py
```

**Output:**
- `llm_training_data/ptcg_training_data_*.json` - Training dataset
- `llm_training_data/training_data_summary.txt` - Statistics

**Generated Examples:**
- 8+ card knowledge examples (from tournament database)
- 7 game rule examples (deck construction, turn structure, etc.)
- Deck strategy examples (from winning decks)

### 2. Test LLM Integration (Mock Mode)

```bash
# Test card analysis
python llm_model_wrapper.py

# Test deck simulation
python enhanced_deck_simulator.py
```

### 3. Train Your LLM

See [LLM_TRAINING_GUIDE.md](LLM_TRAINING_GUIDE.md) for complete training instructions.

**Supported Models:**
- Llama 2/3 (7B-70B)
- Mistral (7B)
- GPT-J (6B)
- Falcon (7B)

### 4. Integrate with AI System

```python
from llm_model_wrapper import PTCGLLMWrapper
from ai_deck_builder import DeckBuilder

# Load trained model
llm = PTCGLLMWrapper(model_path='./ptcg_llm_final', use_mock=False)

# Use for deck building
analysis = llm.analyze_card("ハイパーボール")
print(analysis['analysis'])

# Build deck with LLM
deck = llm.build_deck_from_archetype("Lightning", ["ピカチュウex"])
print(deck['decklist'])
```

## 📁 System Architecture

```
┌─────────────────────────────────────────────────────────┐
│              PTCG LLM Training Pipeline                 │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  1. Data Extraction (llm_training_data_generator.py)   │
│     ┌──────────────────────────────────────────┐       │
│     │ Tournament DB (ptcg_events.db)           │       │
│     │  • 427 tournaments                        │       │
│     │  • 5,640 decks                           │       │
│     │  • 2,700+ cards                          │       │
│     └──────────────┬───────────────────────────┘       │
│                    ↓                                     │
│     ┌──────────────────────────────────────────┐       │
│     │ Training Data Generation                 │       │
│     │  • Card descriptions + usage stats       │       │
│     │  • Game rules + examples                 │       │
│     │  • Deck strategies from winners          │       │
│     └──────────────┬───────────────────────────┘       │
│                    ↓                                     │
│     ┌──────────────────────────────────────────┐       │
│     │ JSON Dataset (instruction format)        │       │
│     │  {instruction, input, output, metadata}  │       │
│     └──────────────┬───────────────────────────┘       │
│                    ↓                                     │
│                                                          │
│  2. Model Training (External: HuggingFace, etc.)       │
│     ┌──────────────────────────────────────────┐       │
│     │ Base Model (Llama 2, Mistral, etc.)      │       │
│     └──────────────┬───────────────────────────┘       │
│                    ↓                                     │
│     ┌──────────────────────────────────────────┐       │
│     │ Fine-Tuning Process                      │       │
│     │  • 3-5 epochs                            │       │
│     │  • Learning rate: 2e-5                   │       │
│     │  • Batch size: 4-8                       │       │
│     └──────────────┬───────────────────────────┘       │
│                    ↓                                     │
│     ┌──────────────────────────────────────────┐       │
│     │ Trained PTCG Model                       │       │
│     └──────────────┬───────────────────────────┘       │
│                    ↓                                     │
│                                                          │
│  3. Integration (llm_model_wrapper.py)                 │
│     ┌──────────────────────────────────────────┐       │
│     │ PTCGLLMWrapper                           │       │
│     │  • analyze_card()                        │       │
│     │  • build_deck_from_archetype()           │       │
│     │  • suggest_deck_improvements()           │       │
│     │  • answer_rules_question()               │       │
│     └──────────────┬───────────────────────────┘       │
│                    ↓                                     │
│                                                          │
│  4. Application (enhanced_deck_simulator.py)           │
│     ┌──────────────────────────────────────────┐       │
│     │ EnhancedDeckSimulator                    │       │
│     │  • Deck evaluation                       │       │
│     │  • Matchup simulation                    │       │
│     │  • LLM-powered optimization              │       │
│     │  • Tournament analysis                   │       │
│     └──────────────────────────────────────────┘       │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

## 🎴 Training Data Format

### Example 1: Card Knowledge

```json
{
  "instruction": "Describe the Pokemon TCG card: ハイパーボール",
  "input": "Card Code: SV8a 150/187\nCategory: Item",
  "output": "ハイパーボール (Hyper Ball) is an Item card from Pokemon TCG. It appears in 142+ tournament decks. Players typically run 4 copies for maximum consistency. This card commonly appears with: Nest Ball, Boss's Orders, Professor's Research...",
  "metadata": {
    "card_name": "ハイパーボール",
    "category": "Item",
    "deck_usage": 142
  }
}
```

### Example 2: Game Rules

```json
{
  "instruction": "Explain the Pokemon TCG rule: Deck Construction",
  "input": "",
  "output": "A Pokemon TCG deck must contain exactly 60 cards. You can have up to 4 copies of any card with the same name, except for Basic Energy cards.\n\nExamples:\n- Valid: 4x Pikachu ex, 4x Hyper Ball, 15x Basic Lightning Energy\n- Invalid: 5x Pikachu ex (exceeds 4-copy limit)",
  "metadata": {
    "topic": "Deck Construction",
    "type": "game_rule"
  }
}
```

### Example 3: Deck Strategy

```json
{
  "instruction": "Analyze this Pokemon TCG tournament deck and explain its strategy",
  "input": "Tournament: City Championship\nPlayer: TestPlayer\nRank: 1位\n\nPokemon:\n  2x ピカチュウex\n  2x ライチュウ\n...",
  "output": "This deck's primary attacker is ピカチュウex, featuring 2 copies for consistency. The deck runs 15 Pokemon cards, providing good consistency. It uses 2 different search cards (ハイパーボール, ネストボール) to find Pokemon quickly...",
  "metadata": {
    "deck_id": "deck_001",
    "player": "TestPlayer",
    "event": "City Championship"
  }
}
```

## 🔧 Module Reference

### llm_training_data_generator.py

Generates training data from tournament database.

**Classes:**
- `PTCGCardDataExtractor` - Extracts card data with usage statistics
- `PTCGRuleExtractor` - Formats game rules for training
- `PTCGDeckStrategyExtractor` - Analyzes winning deck strategies
- `LLMTrainingDataGenerator` - Main generator class

**Key Methods:**
```python
generator = LLMTrainingDataGenerator()
dataset = generator.generate_full_dataset()
# Creates JSON training file
```

### llm_model_wrapper.py

Wrapper for trained LLM models.

**Classes:**
- `PTCGLLMWrapper` - Main LLM interface
- `LLMDeckOptimizer` - Deck optimization utilities

**Key Methods:**
```python
llm = PTCGLLMWrapper(model_path='./ptcg_llm_final', use_mock=False)

# Card analysis
analysis = llm.analyze_card("ピカチュウex")

# Deck building
deck = llm.build_deck_from_archetype("Lightning", ["ピカチュウex"])

# Rules Q&A
answer = llm.answer_rules_question("Can I play two Supporters?")

# Deck improvements
suggestions = llm.suggest_deck_improvements(deck_list)
```

### enhanced_deck_simulator.py

Advanced deck testing with LLM integration.

**Classes:**
- `EnhancedDeckSimulator` - Main simulator
- `TournamentDeckAnalyzer` - Pattern analysis

**Key Methods:**
```python
simulator = EnhancedDeckSimulator(use_llm=True)
simulator.connect()

# Load tournament deck
deck = simulator.get_tournament_deck("deck_001")

# Evaluate composition
evaluation = simulator.evaluate_deck_composition(deck['cards'])

# Get LLM analysis
analysis = simulator.get_llm_deck_analysis(deck)

# Optimize with LLM
optimization = simulator.optimize_deck_with_llm(deck)
```

## 📊 Dataset Statistics

**Current Training Data (from ptcg_events.db):**
- Total Examples: 16
- Card Examples: 8 (from 8 unique cards)
- Rule Examples: 7 (covering major game rules)
- Strategy Examples: 1 (from tournament data)

**Card Categories:**
- Item cards: 3 examples (ハイパーボール, ネストボール, ポケモンいれかえ)
- Supporter cards: 2 examples (ボスの指令, ナンジャモ)
- Pokemon ex: 1 example (ピカチュウex)
- Basic Energy: 1 example (基本雷エネルギー)
- Pokemon: 1 example (ライチュウ)

**To Expand Dataset:**
1. Add more tournament data to ptcg_events.db
2. Integrate PTCG_CardDB_Tc database for card descriptions
3. Re-run `llm_training_data_generator.py`

## 🔗 PTCG_CardDB_Tc Integration

To use full card database with descriptions:

```bash
# Clone card database
git clone https://github.com/NeoSilver997/PTCG_CardDB_Tc.git

# Update configuration (future enhancement)
export PTCG_CARDDB_PATH="./PTCG_CardDB_Tc/pokemon_cards.db"

# Re-generate with card descriptions
python llm_training_data_generator.py --use-carddb
```

This will add:
- Card attack descriptions
- Ability texts
- HP, types, weakness/resistance
- Card images (optional)

## 💡 Use Cases

### 1. Tournament Deck Building

```python
llm = PTCGLLMWrapper(model_path='./ptcg_llm_final')

# Ask LLM to build competitive deck
deck = llm.build_deck_from_archetype(
    archetype="Lightning",
    core_cards=["ピカチュウex", "電磁レーダー"]
)
print(deck['decklist'])
```

### 2. Deck Optimization

```python
simulator = EnhancedDeckSimulator(use_llm=True)
simulator.connect()

# Load your deck
my_deck = simulator.get_tournament_deck("deck_001")

# Get optimization suggestions
optimization = simulator.optimize_deck_with_llm(my_deck)
print(optimization['llm_suggestions'])
```

### 3. Card Analysis

```python
llm = PTCGLLMWrapper(model_path='./ptcg_llm_final')

# Understand card usage
analysis = llm.analyze_card("ハイパーボール")
print(analysis['analysis'])
# Output: Usage stats, synergies, strategic value
```

### 4. Rules Q&A

```python
llm = PTCGLLMWrapper(model_path='./ptcg_llm_final')

# Ask rules questions
answer = llm.answer_rules_question(
    "Can I attach energy to benched Pokemon?"
)
print(answer)
```

## 🧪 Testing

### Mock Mode (No Trained Model Required)

```bash
# All modules work in mock mode for testing
python llm_model_wrapper.py
python enhanced_deck_simulator.py
```

### With Trained Model

```python
from llm_model_wrapper import PTCGLLMWrapper

# Load your trained model
llm = PTCGLLMWrapper(
    model_path='./ptcg_llm_final',
    use_mock=False  # Use real model
)

# Test inference
response = llm.generate("Build a Lightning deck")
print(response)
```

## 📚 Documentation

- **[LLM_TRAINING_GUIDE.md](LLM_TRAINING_GUIDE.md)** - Complete training tutorial
- **[AI_SYSTEM_README.md](AI_SYSTEM_README.md)** - AI system overview
- **[FEATURES.md](FEATURES.md)** - Feature demonstrations
- **[PROJECT_README.md](PROJECT_README.md)** - Project documentation

## 🎮 Integration with Existing AI

The LLM system integrates with:

### Existing Modules:
- `ai_deck_builder.py` - Can use LLM for card selection
- `ai_gameplay.py` - Can use LLM for strategic decisions
- `ai_cli.py` - Can add LLM commands

### Example Integration:

```python
from ai_deck_builder import DeckBuilder, CardDatabase
from llm_model_wrapper import PTCGLLMWrapper

# Initialize both systems
card_db = CardDatabase()
card_db.connect()

llm = PTCGLLMWrapper(model_path='./ptcg_llm_final')

# Build deck using both tournament data and LLM
builder = DeckBuilder(card_db)
core_cards = [("ピカチュウex", 2)]
deck = builder.build_deck_from_archetype("Lightning", core_cards)

# Get LLM optimization
optimization = llm.suggest_deck_improvements(deck)
print(optimization['suggestions'])
```

## 🚀 Performance

### Training Time (Estimated):
- 7B model: 4-6 hours (16GB VRAM)
- 13B model: 8-12 hours (24GB VRAM)
- 70B model: 24-48 hours (80GB VRAM)

### Inference Speed:
- CPU: 1-5 seconds per response
- GPU (RTX 3090): 0.1-0.5 seconds per response
- Quantized (4-bit): 0.5-2 seconds per response

### Resource Requirements:
- **Minimum**: 16GB RAM, 8GB VRAM
- **Recommended**: 32GB RAM, 16GB VRAM
- **Optimal**: 64GB RAM, 24GB+ VRAM

## 🔮 Future Enhancements

- [ ] Integrate full PTCG_CardDB_Tc for card descriptions
- [ ] Add card image analysis (vision models)
- [ ] Multi-language support (Japanese ↔ English ↔ Chinese)
- [ ] Real-time meta tracking
- [ ] Web interface for LLM interaction
- [ ] Tournament result prediction
- [ ] Deck matchup analysis
- [ ] Card price integration

## 📝 License

MIT License - See LICENSE file for details

---

**Note**: This system requires a trained LLM model. The training data generator creates the dataset, but you must train a model using tools like HuggingFace Transformers, LLaMA.cpp, or Ollama.

## 🤝 Contributing

Contributions welcome! Areas for improvement:
- More training data extraction strategies
- Additional LLM integration patterns
- Performance optimizations
- Documentation improvements

## 📧 Support

- GitHub Issues: Report bugs and request features
- Documentation: See linked guides above
- Examples: Check `llm_model_wrapper.py` and `enhanced_deck_simulator.py`

---

**Built with ❤️ for the Pokemon TCG competitive community**
