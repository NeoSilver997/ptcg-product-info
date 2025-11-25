# Pokemon TCG Local LLM Training Guide

This guide explains how to train a local Large Language Model (LLM) to understand Pokemon Trading Card Game rules, cards, and deck building strategies using tournament data.

## Overview

The LLM training system extracts knowledge from:
1. **Card Database**: 2,000+ unique cards from tournament decks
2. **Tournament Data**: 427 tournaments, 5,640 complete decks
3. **Game Rules**: Complete Pokemon TCG ruleset
4. **Winning Strategies**: Analysis of championship-winning decks

## Quick Start

### 1. Generate Training Data

```bash
# Generate a smaller sample for development
python llm_training_data_generator.py --card-limit 100 --deck-limit 10

# Generate a full dataset including all cards and decks (may be large)
python llm_training_data_generator.py --include-all-cards --card-limit 0 --include-all-decks --deck-limit 0

# Generate a full dataset for all cards but limited number of decks (faster)
python llm_training_data_generator.py --include-all-cards --card-limit 0 --include-all-decks --deck-limit 50
```

This creates:
- `llm_training_data/ptcg_training_data_YYYYMMDD_HHMMSS.json` - Full dataset
- `llm_training_data/training_data_summary.txt` - Summary report

You can also include deck-level examples for many or all decks using the `--include-all-decks` flag. Use `--deck-limit` to limit the number of decks processed to avoid very large datasets:

```bash
python llm_training_data_generator.py --include-all-decks --deck-limit 200
```

### 2. Training Data Format

The generated data uses instruction-following format:

```json
{
  "instruction": "Describe the Pokemon TCG card: ピカチュウex",
  "input": "Card Code: SV8a 001/187\nCategory: Pokemon ex",
  "output": "ピカチュウex is a Pokemon ex card... [detailed description]",
  "metadata": {
    "card_name": "ピカチュウex",
    "category": "Pokemon ex",
    "deck_usage": 15
  }
}
```

Deck-level examples include these additional metadata fields:

```json
{
    "type": "deck_strategy" | "deck_list" | "deck_card_role",
    "deck_id": "<deck_id>",
    "player": "player_name",
    "event": "event_title",
    "date": "YYYY-MM-DD",
    "card_name": "card_name",
    "card_qty": 3
}
```

### 3. Choose Your LLM

Recommended local LLMs:

| Model | Size | VRAM | Training Time | Use Case |
|-------|------|------|---------------|----------|
| **Llama 2 7B** | 7B params | 16GB | 4-6 hours | General purpose, good balance |
| **Mistral 7B** | 7B params | 16GB | 3-5 hours | Fast inference, efficient |
| **Llama 3 8B** | 8B params | 20GB | 5-7 hours | Latest, best quality |
| **GPT-J 6B** | 6B params | 12GB | 3-4 hours | Lighter option |
| **Falcon 7B** | 7B params | 16GB | 4-6 hours | Good instruction following |

### 4. Training Setup

#### Option A: Using Hugging Face Transformers

```python
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    TrainingArguments,
    Trainer
)
from datasets import load_dataset
import torch

# Load model and tokenizer
model_name = "meta-llama/Llama-2-7b-hf"  # or your chosen model
model = AutoModelForCausalLM.from_pretrained(
    model_name,
    torch_dtype=torch.float16,
    device_map="auto"
)
tokenizer = AutoTokenizer.from_pretrained(model_name)

# Load training data
dataset = load_dataset('json', data_files='llm_training_data/ptcg_training_data_*.json')

# Training arguments
training_args = TrainingArguments(
    output_dir="./ptcg_llm_model",
    num_train_epochs=3,
    per_device_train_batch_size=4,
    gradient_accumulation_steps=4,
    learning_rate=2e-5,
    fp16=True,
    logging_steps=10,
    save_steps=100,
    save_total_limit=3
)

# Create trainer
trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=dataset['train'],
    tokenizer=tokenizer
)

# Train
trainer.train()
trainer.save_model("./ptcg_llm_final")
```

#### Option B: Using LLaMA.cpp (CPU-friendly)

```bash
# Convert training data to LLaMA.cpp format
python convert_to_llama_format.py

# Fine-tune using LLaMA.cpp
./llama-cli --model models/llama-2-7b.gguf \
           --train llm_training_data/ptcg_training.txt \
           --epochs 3 \
           --batch-size 8 \
           --learning-rate 0.00002
```

#### Option C: Using Ollama (Easiest)

```bash
# Create Modelfile
cat > Modelfile <<EOF
FROM llama2

# Set parameters
PARAMETER temperature 0.7
PARAMETER top_p 0.9

# Load fine-tuning data
SYSTEM You are a Pokemon TCG expert trained on tournament data.
EOF

# Train with Ollama
ollama create ptcg-expert -f Modelfile
```

### 5. Training Parameters

**Recommended Settings**:
- **Learning Rate**: 2e-5 (lower for larger models)
- **Epochs**: 3-5
- **Batch Size**: 4-8 (depends on GPU memory)
- **Max Length**: 512 tokens
- **Warmup Steps**: 100
- **Weight Decay**: 0.01

**Hardware Requirements**:
- **Minimum**: 16GB RAM, 8GB VRAM
- **Recommended**: 32GB RAM, 16GB VRAM
- **Optimal**: 64GB RAM, 24GB VRAM

### 6. Using the Trained Model

#### Deck Building Query

```python
from transformers import pipeline

# Load trained model
generator = pipeline('text-generation', model='./ptcg_llm_final')

# Query for deck building
prompt = """Build a competitive Pokemon TCG deck using Pikachu ex as the primary attacker.
Include recommended trainers and energy cards."""

response = generator(prompt, max_length=500, temperature=0.7)
print(response[0]['generated_text'])
```

#### Card Analysis

```python
prompt = """Analyze the card ハイパーボール (Hyper Ball).
What decks should use it and how many copies?"""

response = generator(prompt, max_length=300)
print(response[0]['generated_text'])
```

#### Game Strategy

```python
prompt = """I have Pikachu ex as my active Pokemon with 2 Lightning Energy attached.
My opponent has a damaged Charizard ex (100 HP remaining).
What should I do?"""

response = generator(prompt, max_length=400)
print(response[0]['generated_text'])
```

## Training Data Statistics

The generated dataset includes:

### Card Knowledge (~2,700 examples)
- Card descriptions with tournament usage
- Synergy information
- Optimal quantities
- Strategic value

### Game Rules (~7 examples)
- Deck construction rules
- Turn structure
- Energy attachment
- Supporter cards
- Prize cards
- Bench mechanics
- Retreat costs

### Deck Strategies (~10 examples)
- Championship-winning decklists
- Strategic analysis
- Card ratios
- Archetype identification

## Advanced Features

### 1. PTCG_CardDB_Tc Integration

To use the full card database from https://github.com/NeoSilver997/PTCG_CardDB_Tc:

```bash
# Clone the card database
git clone https://github.com/NeoSilver997/PTCG_CardDB_Tc.git

# Update configuration to use it
export PTCG_CARDDB_PATH="./PTCG_CardDB_Tc/pokemon_cards.db"

# Re-generate training data with card descriptions
python llm_training_data_generator.py --use-carddb
```

This adds:
- Card images
- Attack descriptions
- Ability texts
- HP and type information
- Weakness/resistance data

### 2. Continuous Learning

Update the model as new tournament data arrives:

```bash
# Import new tournament data
python import_events_to_sqlite.py

# Re-generate training data
python llm_training_data_generator.py

# Continue training (fine-tune existing model)
python train_llm.py --model ./ptcg_llm_final --continue-training
```

### 3. Multi-Language Support

The system supports both Japanese and Chinese cards:

```python
# Generate bilingual training data
generator = LLMTrainingDataGenerator(include_translations=True)
dataset = generator.generate_full_dataset()
```

## Evaluation

### Test Queries

Use these queries to evaluate your trained model:

1. **Card Knowledge**: "What is ハイパーボール used for?"
2. **Rules**: "Can I play two Supporter cards in one turn?"
3. **Deck Building**: "Build a Lightning-type deck"
4. **Strategy**: "What are the best search cards in the current meta?"
5. **Gameplay**: "When should I use Boss's Orders?"

### Benchmarks

A well-trained model should:
- ✓ Correctly identify card categories
- ✓ Know card synergies from tournaments
- ✓ Follow all game rules accurately
- ✓ Build legal 60-card decks
- ✓ Suggest competitive card choices
- ✓ Explain strategic decisions

## Troubleshooting

### Out of Memory

```bash
# Reduce batch size
--per_device_train_batch_size=2

# Enable gradient checkpointing
--gradient_checkpointing=true

# Use 8-bit quantization
--load_in_8bit=true
```

### Slow Training

```bash
# Use mixed precision
--fp16=true

# Increase batch size with gradient accumulation
--gradient_accumulation_steps=8

# Use DeepSpeed
--deepspeed=ds_config.json
```

### Poor Results

- Train for more epochs (5-7)
- Lower learning rate (1e-5)
- Add more training data
- Use a larger base model

## Integration with AI System

The trained LLM integrates with existing AI components:

```python
from ai_deck_builder import DeckBuilder
from llm_model_wrapper import PTCGLLMWrapper

# Initialize
llm = PTCGLLMWrapper(model_path='./ptcg_llm_final')
deck_builder = DeckBuilder(llm_model=llm)

# LLM-powered deck building
deck = deck_builder.build_deck_with_llm(
    prompt="Build a competitive Pikachu ex deck"
)

# LLM-powered gameplay
from ai_gameplay import GameAI
ai = GameAI(llm_model=llm)
move = ai.get_llm_move_suggestion(game_state)
```

## Resources

### Documentation
- [Hugging Face Transformers](https://huggingface.co/docs/transformers)
- [LLaMA.cpp](https://github.com/ggerganov/llama.cpp)
- [Ollama](https://ollama.ai/)

### Datasets
- Tournament data: `ptcg_events.db`
- Card database: https://github.com/NeoSilver997/PTCG_CardDB_Tc

### Models
- [Llama 2](https://huggingface.co/meta-llama/Llama-2-7b-hf)
- [Mistral](https://huggingface.co/mistralai/Mistral-7B-v0.1)
- [Llama 3](https://huggingface.co/meta-llama/Meta-Llama-3-8B)

## Next Steps

1. Generate training data: `python llm_training_data_generator.py`
2. Review the data in `llm_training_data/`
3. Choose and download a base LLM model
4. Train using your preferred method
5. Test with sample queries
6. Integrate with AI deck builder and gameplay system

## License

This training data is generated from tournament results and game rules. Please ensure compliance with:
- Pokemon TCG terms of service
- Model license (Llama 2, Mistral, etc.)
- Fair use for educational/research purposes

---

**Note**: Training LLMs requires significant computational resources. Consider using cloud GPU services (Google Colab, AWS, etc.) if local hardware is insufficient.
