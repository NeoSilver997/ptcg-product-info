"""
Pokemon TCG LLM Training with Ollama
====================================

Train a local LLM using Ollama to understand Pokemon TCG cards, rules, and strategies.
Uses the generated training data to create a specialized PTCG assistant.

Usage:
    python train_llm_ollama.py                          # Use default gemma3:12b
    python train_llm_ollama.py --model qwen2.5-coder    # Use different base model
    python train_llm_ollama.py --test                   # Test without creating model
"""

import json
import subprocess
import sys
import argparse
from pathlib import Path
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class OllamaLLMTrainer:
    """Train LLM using Ollama with PTCG training data."""
    
    def __init__(self, base_model='gemma3:12b', training_data_file=None):
        """Initialize the trainer."""
        self.base_model = base_model
        self.model_name = 'ptcg-expert'
        self.training_data_dir = Path('llm_training_data')
        self.training_data_file = training_data_file or self._find_latest_training_data()
        
    def _find_latest_training_data(self) -> Path:
        """Find the most recent training data file."""
        files = list(self.training_data_dir.glob('ptcg_training_data_full_*.json'))
        if not files:
            raise FileNotFoundError("No training data found. Run llm_training_data_generator_full.py first.")
        return max(files, key=lambda p: p.stat().st_mtime)
    
    def load_training_data(self) -> dict:
        """Load and parse training data."""
        logger.info(f"Loading training data from: {self.training_data_file}")
        with open(self.training_data_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        logger.info(f"Loaded {data['metadata']['total_examples']} training examples")
        logger.info(f"  Card examples: {data['metadata']['card_examples']}")
        logger.info(f"  Rule examples: {data['metadata']['rule_examples']}")
        logger.info(f"  Strategy examples: {data['metadata']['strategy_examples']}")
        
        return data
    
    def create_system_prompt(self, data: dict) -> str:
        """Create comprehensive system prompt for the model."""
        prompt = """You are a Pokemon Trading Card Game (PTCG) expert AI assistant with comprehensive knowledge of:

**Card Database**: Over 5,000 Pokemon, Trainer, and Energy cards from multiple expansions
- Detailed card effects, abilities, and attack descriptions
- HP, types, weaknesses, resistances, and retreat costs
- Tournament usage statistics from 427 competitive events
- Evolution chains and card synergies

**Game Rules**: Complete official Pokemon TCG ruleset including:
- Deck construction (60 cards, 4-copy limit, ACE SPEC restrictions)
- Turn structure (Draw → Main Phase → Attack → Pokemon Check)
- Combat mechanics (damage calculation order, weakness/resistance)
- Status conditions (Poison, Burn, Sleep, Paralysis)
- Evolution timing and restrictions
- Trainer card types (Item, Supporter, Stadium)
- Win/loss conditions

**Tournament Analysis**: Data from 5,640 competitive decks including:
- Winning deck compositions and strategies
- Meta-game trends and popular archetypes
- Card usage frequencies across tournament play
- Optimal card ratios and deck building patterns

**Strategic Knowledge**:
- Card synergies and combo potential
- Energy efficiency and resource management
- Bench management and board control
- Prize card trading strategies
- Counter-play and matchup analysis

When answering questions:
1. Provide accurate, detailed information from the card database
2. Reference tournament data when discussing competitive viability
3. Explain game rules clearly with examples
4. Suggest optimal deck building strategies
5. Consider meta-game context in recommendations

Always cite tournament usage statistics when relevant, and provide practical examples for complex concepts.
"""
        return prompt
    
    def prepare_training_examples(self, data: dict) -> list:
        """Prepare training examples in Ollama format."""
        examples = []
        # Prioritize specific critical examples (Budew/含羞苞, Boss's Orders/老大的指令)
        # Prioritize examples for critical cards/attacks to bias learning towards them
        prioritized_names = [
            "含羞苞",
            "Budew",
            "癢癢花粉",
            "Boss's Orders",
            "老大的指令",
            "ハイパーボール",
            "Hyper Ball",
            # Common Trainers / Items to prioritize
            "Professor's Research",
            "博士的研究",
            "Ｍａｒｎｉｅ",
            "Marnie",
            "マリィ",
            "Quick Ball",
            "クイックボール",
            "Ultra Ball",
            "ウルトラボール",
            "Nest Ball",
            "ネストボール",
            "Pokémon Catcher",
            "ポケモンキャッチャー",
            "Switch",
            "シロナ",
        ]
        # Build prioritized list and then append the rest (avoid duplicates)
        prioritized = []
        others = []
        for example in data['examples']:
            instr = (example.get('instruction') or '')
            # Also check metadata card_name and attack_name if present
            meta = example.get('metadata', {}) or {}
            card_name = meta.get('card_name', '')
            attack_name = meta.get('attack_name', '')
            attack_effect = meta.get('attack_effect', '') or ''

            combined = f"{instr} {card_name} {attack_name} {attack_effect}".lower()
            if any(pn.lower() in combined for pn in prioritized_names) or any(kw in attack_effect.lower() for kw in ['prevent', '阻止', '禁止', '無法', '不能']):
                prioritized.append(example)
            elif meta.get('type') in ('deck_strategy', 'deck_list', 'deck_card_role'):
                # Prioritize deck-level strategy and deck list examples
                prioritized.append(example)
            else:
                others.append(example)

        ordered_examples = prioritized + others

        for example in ordered_examples:  # Use all examples by default
            # Backwards-compatible: read instruction/input/output from top-level or metadata
            instruction = example.get('instruction') or example.get('metadata', {}).get('instruction')
            input_field = example.get('input') or example.get('metadata', {}).get('input')
            output_field = example.get('output') or example.get('metadata', {}).get('output')

            if not instruction:
                # If no instruction present, skip
                continue

            question = instruction
            if input_field:
                question += f"\n\n{input_field}"

            examples.append({
                'prompt': question,
                'response': output_field or ''
            })
        
        return examples
    
    def create_modelfile(self, system_prompt: str) -> str:
        """Create Ollama Modelfile."""
        # Escape the prompt properly for Modelfile format
        escaped_prompt = system_prompt.replace('"', '\\"').replace('\n', '\\n')
        
        modelfile_content = f"""FROM {self.base_model}

PARAMETER temperature 0.7
PARAMETER top_p 0.9
PARAMETER top_k 40
PARAMETER repeat_penalty 1.1
PARAMETER num_ctx 4096

SYSTEM \"\"\"{system_prompt}\"\"\"
"""
        return modelfile_content
    
    def train_model(self) -> bool:
        """Train the model using Ollama."""
        try:
            # Load training data
            data = self.load_training_data()
            
            # Create system prompt
            system_prompt = self.create_system_prompt(data)
            
            # Create Modelfile
            modelfile_content = self.create_modelfile(system_prompt)
            
            # Save Modelfile
            modelfile_path = Path('Modelfile.ptcg')
            logger.info(f"Creating Modelfile: {modelfile_path}")
            with open(modelfile_path, 'w', encoding='utf-8') as f:
                f.write(modelfile_content)
            
            # Create model with Ollama
            logger.info(f"Creating model '{self.model_name}' from {self.base_model}...")
            logger.info("This will embed PTCG knowledge into the model...")
            
            result = subprocess.run(
                ['ollama', 'create', self.model_name, '-f', str(modelfile_path)],
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace'
            )
            
            if result.returncode == 0:
                logger.info(f"✓ Successfully created model: {self.model_name}")
                logger.info(f"\nModel can be used with: ollama run {self.model_name}")
                return True
            else:
                logger.error(f"Failed to create model: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"Training failed: {e}")
            return False
    
    def test_model(self):
        """Test the trained model with sample queries."""
        logger.info(f"\nTesting model: {self.model_name}")
        
        test_queries = [
            "What is ハイパーボール (Hyper Ball) and how is it used?",
            "Can I play two Supporter cards in one turn?",
            "Build a basic Pikachu ex deck strategy",
            "Explain the Pokemon Check phase",
            "What cards have the highest tournament usage?"
        ]
        
        for i, query in enumerate(test_queries, 1):
            logger.info(f"\nTest Query {i}: {query}")
            
            try:
                result = subprocess.run(
                    ['ollama', 'run', self.model_name, query],
                    capture_output=True,
                    text=True,
                    encoding='utf-8',
                    errors='replace',
                    timeout=30
                )
                
                if result.returncode == 0:
                    logger.info(f"Response: {result.stdout[:200]}...")
                else:
                    logger.error(f"Query failed: {result.stderr}")
                    
            except subprocess.TimeoutExpired:
                logger.warning("Query timed out")
            except Exception as e:
                logger.error(f"Query error: {e}")


def main():
    """Main training function."""
    parser = argparse.ArgumentParser(description='Train Pokemon TCG LLM with Ollama')
    parser.add_argument('--model', default='gemma3:12b', help='Base Ollama model to use')
    parser.add_argument('--data', help='Path to training data JSON file')
    parser.add_argument('--test', action='store_true', help='Test the model after training')
    parser.add_argument('--test-only', action='store_true', help='Only test existing model')
    
    args = parser.parse_args()
    
    print("=" * 70)
    print("Pokemon TCG LLM Training with Ollama")
    print("=" * 70)
    print()
    
    # Initialize trainer
    trainer = OllamaLLMTrainer(base_model=args.model, training_data_file=args.data)
    
    if not args.test_only:
        # Train the model
        print(f"Base Model: {args.model}")
        print(f"Training Data: {trainer.training_data_file}")
        print(f"Output Model: {trainer.model_name}")
        print()
        
        success = trainer.train_model()
        
        if not success:
            logger.error("Training failed!")
            sys.exit(1)
    
    # Test if requested
    if args.test or args.test_only:
        trainer.test_model()
    
    print()
    print("=" * 70)
    print("Training Complete!")
    print("=" * 70)
    print()
    print(f"To use your trained model:")
    print(f"  ollama run {trainer.model_name}")
    print()
    print(f"To integrate with Python:")
    print(f"  from llm_model_wrapper import PTCGLLMWrapper")
    print(f"  llm = PTCGLLMWrapper(model_name='{trainer.model_name}')")
    print()


if __name__ == '__main__':
    main()
