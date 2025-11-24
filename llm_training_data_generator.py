"""
LLM Training Data Generator for Pokemon TCG

This module generates training data for a local LLM to learn Pokemon TCG:
- Card descriptions and abilities
- Game rules and mechanics
- Deck building strategies
- Tournament-proven deck patterns
"""

import sqlite3
import json
import os
from pathlib import Path
from typing import List, Dict, Optional
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class PTCGCardDataExtractor:
    """Extract card data from the event database for LLM training."""
    
    def __init__(self, event_db='ptcg_events.db'):
        """Initialize the card data extractor."""
        self.event_db_path = event_db
        self.conn = None
        
    def connect(self):
        """Connect to the event database."""
        self.conn = sqlite3.connect(self.event_db_path)
        self.conn.row_factory = sqlite3.Row
        logger.info(f"Connected to database: {self.event_db_path}")
    
    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()
            logger.info("Database connection closed")
    
    def get_all_unique_cards(self) -> List[Dict]:
        """Get all unique cards with their statistics."""
        query = """
            SELECT 
                card_name,
                card_code,
                COUNT(DISTINCT deck_id) as deck_count,
                AVG(quantity) as avg_quantity,
                SUM(quantity) as total_copies,
                MIN(quantity) as min_quantity,
                MAX(quantity) as max_quantity
            FROM deck_cards
            WHERE card_name IS NOT NULL
            GROUP BY card_id
            ORDER BY deck_count DESC, card_name
        """
        cursor = self.conn.execute(query)
        cards = [dict(row) for row in cursor.fetchall()]
        logger.info(f"Extracted {len(cards)} unique cards")
        return cards
    
    def get_card_context(self, card_name: str) -> Dict:
        """Get contextual information about a card from tournament usage."""
        # Get synergies
        synergy_query = """
            SELECT 
                dc2.card_name,
                COUNT(DISTINCT dc1.deck_id) as cooccurrence
            FROM deck_cards dc1
            JOIN deck_cards dc2 ON dc1.deck_id = dc2.deck_id
            WHERE dc1.card_name = ?
            AND dc2.card_name != ?
            AND dc2.card_name IS NOT NULL
            GROUP BY dc2.card_id
            ORDER BY cooccurrence DESC
            LIMIT 10
        """
        cursor = self.conn.execute(synergy_query, (card_name, card_name))
        synergies = [dict(row) for row in cursor.fetchall()]
        
        # Get deck archetypes using this card
        archetype_query = """
            SELECT DISTINCT d.deck_id, e.event_title, e.event_date, p.player_name
            FROM deck_cards dc
            JOIN decks d ON dc.deck_id = d.deck_id
            JOIN events e ON d.event_id = e.event_id
            JOIN players p ON d.player_id = p.player_id
            WHERE dc.card_name = ?
            ORDER BY e.event_date DESC
            LIMIT 5
        """
        cursor = self.conn.execute(archetype_query, (card_name,))
        usage_examples = [dict(row) for row in cursor.fetchall()]
        
        return {
            'synergies': synergies,
            'usage_examples': usage_examples
        }
    
    def categorize_card(self, card_name: str, card_code: str) -> str:
        """Categorize a card based on its name and code."""
        name_lower = card_name.lower()
        
        # Energy cards
        if 'エネルギー' in card_name:
            if '基本' in card_name:
                return 'Basic Energy'
            return 'Special Energy'
        
        # Trainer cards
        if any(keyword in card_name for keyword in ['博士', 'サポート', 'ボス', 'ナンジャモ', 'マリィ', 'シロナ']):
            return 'Supporter'
        if any(keyword in card_name for keyword in ['スタジアム', 'タウン', 'パーク']):
            return 'Stadium'
        if any(keyword in card_name for keyword in ['ボール', 'いれかえ', 'グッズ', 'レスキュー']):
            return 'Item'
        
        # Pokemon cards
        if 'ex' in card_name.lower() or 'EX' in card_name:
            return 'Pokemon ex'
        if 'v' in card_name.lower() and ('VMAX' in card_name or 'VSTAR' in card_name):
            return 'Pokemon VMAX/VSTAR'
        if 'GX' in card_name:
            return 'Pokemon GX'
        
        # Default to basic Pokemon if not categorized
        return 'Pokemon'
    
    def generate_card_training_examples(self) -> List[Dict]:
        """Generate training examples for each card."""
        cards = self.get_all_unique_cards()
        training_examples = []
        
        for card in cards:
            card_name = card['card_name']
            context = self.get_card_context(card_name)
            category = self.categorize_card(card_name, card['card_code'])
            
            # Create training example
            example = {
                'instruction': f"Describe the Pokemon TCG card: {card_name}",
                'input': f"Card Code: {card['card_code']}\nCategory: {category}",
                'output': self._generate_card_description(card, context, category),
                'metadata': {
                    'card_name': card_name,
                    'card_code': card['card_code'],
                    'category': category,
                    'deck_usage': card['deck_count'],
                    'avg_quantity': float(card['avg_quantity'])
                }
            }
            training_examples.append(example)
        
        logger.info(f"Generated {len(training_examples)} card training examples")
        return training_examples
    
    def _generate_card_description(self, card: Dict, context: Dict, category: str) -> str:
        """Generate a descriptive text about a card for training."""
        desc_parts = []
        
        # Basic info
        desc_parts.append(f"{card['card_name']} is a {category} card from the Pokemon Trading Card Game.")
        
        if card['card_code']:
            desc_parts.append(f"Card code: {card['card_code']}.")
        
        # Usage statistics
        desc_parts.append(f"This card appears in {card['deck_count']} tournament decks.")
        desc_parts.append(f"Players typically run {card['avg_quantity']:.1f} copies on average (range: {card['min_quantity']}-{card['max_quantity']}).")
        
        # Synergies
        if context['synergies']:
            synergy_names = [s['card_name'] for s in context['synergies'][:5]]
            desc_parts.append(f"This card commonly appears with: {', '.join(synergy_names)}.")
        
        # Usage examples
        if context['usage_examples']:
            desc_parts.append(f"Recent tournament usage includes decks by {context['usage_examples'][0]['player_name']}.")
        
        # Strategic notes based on category
        if category == 'Supporter':
            desc_parts.append("As a Supporter card, you can only play one per turn.")
        elif category == 'Item':
            desc_parts.append("As an Item card, you can play multiple per turn.")
        elif category == 'Pokemon ex':
            desc_parts.append("As a Pokemon ex, this card gives up 2 Prize cards when knocked out.")
        elif category == 'Basic Energy':
            desc_parts.append("Basic Energy cards can be attached once per turn to power up Pokemon attacks.")
        
        return ' '.join(desc_parts)


class PTCGRuleExtractor:
    """Extract and format Pokemon TCG rules for LLM training."""
    
    def __init__(self):
        """Initialize the rule extractor."""
        self.rules = []
    
    def get_basic_rules(self) -> List[Dict]:
        """Get basic Pokemon TCG rules."""
        rules = [
            {
                'topic': 'Deck Construction',
                'rule': 'A Pokemon TCG deck must contain exactly 60 cards. You can have up to 4 copies of any card with the same name, except for Basic Energy cards.',
                'examples': [
                    'Valid: 4x Pikachu ex, 4x Hyper Ball, 15x Basic Lightning Energy',
                    'Invalid: 5x Pikachu ex (exceeds 4-copy limit)'
                ]
            },
            {
                'topic': 'Turn Structure',
                'rule': 'Each turn consists of phases: Draw (draw 1 card), Main Phase (play Pokemon, attach Energy, play Trainers), Attack Phase (attack or end turn).',
                'examples': [
                    'Turn 1: Draw → Play Pikachu to Bench → Attach Energy to Active → Play Supporter → Attack',
                    'You cannot attack on your first turn if you go first.'
                ]
            },
            {
                'topic': 'Energy Attachment',
                'rule': 'You can attach one Energy card from your hand to one of your Pokemon each turn.',
                'examples': [
                    'Attach 1 Basic Lightning Energy to Pikachu ex',
                    'You cannot attach 2 Energy cards in one turn (unless a card effect allows it)'
                ]
            },
            {
                'topic': 'Supporter Cards',
                'rule': 'You can play only one Supporter card during your turn.',
                'examples': [
                    'Play Professor Research to draw 7 cards',
                    'You cannot play Boss Orders after playing Marnie in the same turn'
                ]
            },
            {
                'topic': 'Prize Cards',
                'rule': 'Win the game by taking all your Prize cards (usually 6). When you knock out an opponent Pokemon, take 1 Prize (2 for Pokemon ex, 3 for Pokemon VMAX).',
                'examples': [
                    'Knock out Pikachu ex → Take 2 Prize cards',
                    'First player to take all 6 Prizes wins'
                ]
            },
            {
                'topic': 'Bench Size',
                'rule': 'You can have up to 5 Pokemon on your Bench at once.',
                'examples': [
                    'Valid: Active Pikachu + 5 Benched Pokemon',
                    'Invalid: Cannot play 6th Pokemon to Bench without discarding one'
                ]
            },
            {
                'topic': 'Retreat Cost',
                'rule': 'To retreat your Active Pokemon, discard Energy equal to its Retreat Cost and switch it with a Benched Pokemon.',
                'examples': [
                    'Pikachu ex has Retreat Cost 1: Discard 1 Energy to retreat',
                    'Free retreat: Pokemon with 0 Retreat Cost can switch for free'
                ]
            }
        ]
        
        training_examples = []
        for rule in rules:
            example = {
                'instruction': f'Explain the Pokemon TCG rule: {rule["topic"]}',
                'input': '',
                'output': f'{rule["rule"]}\n\nExamples:\n' + '\n'.join(f'- {ex}' for ex in rule['examples']),
                'metadata': {
                    'topic': rule['topic'],
                    'type': 'game_rule'
                }
            }
            training_examples.append(example)
        
        logger.info(f"Generated {len(training_examples)} rule training examples")
        return training_examples


class PTCGDeckStrategyExtractor:
    """Extract deck building strategies from tournament data."""
    
    def __init__(self, event_db='ptcg_events.db'):
        """Initialize the strategy extractor."""
        self.event_db_path = event_db
        self.conn = None
    
    def connect(self):
        """Connect to the event database."""
        self.conn = sqlite3.connect(self.event_db_path)
        self.conn.row_factory = sqlite3.Row
        logger.info(f"Connected to database: {self.event_db_path}")
    
    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()
    
    def get_winning_decks(self, limit=20) -> List[Dict]:
        """Get winning decks from tournaments."""
        query = """
            SELECT 
                d.deck_id,
                p.player_name,
                e.event_title,
                e.event_date,
                d.rank
            FROM decks d
            JOIN events e ON d.event_id = e.event_id
            JOIN players p ON d.player_id = p.player_id
            ORDER BY e.event_date DESC
            LIMIT ?
        """
        cursor = self.conn.execute(query, (limit,))
        decks = [dict(row) for row in cursor.fetchall()]
        logger.info(f"Found {len(decks)} winning decks")
        return decks
    
    def get_deck_composition(self, deck_id: str) -> Dict:
        """Get the full composition of a deck."""
        query = """
            SELECT card_name, card_code, quantity
            FROM deck_cards
            WHERE deck_id = ?
            ORDER BY 
                CASE 
                    WHEN card_name LIKE '%ex%' THEN 1
                    WHEN card_name LIKE '%VMAX%' THEN 1
                    WHEN card_name LIKE '%エネルギー%' THEN 3
                    ELSE 2
                END,
                card_name
        """
        cursor = self.conn.execute(query, (deck_id,))
        cards = [dict(row) for row in cursor.fetchall()]
        
        # Categorize
        pokemon = []
        trainers = []
        energy = []
        
        for card in cards:
            if 'エネルギー' in card['card_name']:
                energy.append(card)
            elif any(kw in card['card_name'] for kw in ['博士', 'サポート', 'ボス', 'スタジアム', 'ボール', 'いれかえ', 'グッズ']):
                trainers.append(card)
            else:
                pokemon.append(card)
        
        return {
            'pokemon': pokemon,
            'trainers': trainers,
            'energy': energy,
            'total': len(cards)
        }
    
    def generate_deck_strategy_examples(self) -> List[Dict]:
        """Generate training examples for deck building strategies."""
        winning_decks = self.get_winning_decks(limit=10)
        training_examples = []
        
        for deck_info in winning_decks:
            composition = self.get_deck_composition(deck_info['deck_id'])
            
            # Generate strategy description
            strategy = self._analyze_deck_strategy(composition, deck_info)
            
            example = {
                'instruction': 'Analyze this Pokemon TCG tournament deck and explain its strategy',
                'input': self._format_deck_list(composition, deck_info),
                'output': strategy,
                'metadata': {
                    'deck_id': deck_info['deck_id'],
                    'player': deck_info['player_name'],
                    'event': deck_info['event_title'],
                    'date': deck_info['event_date']
                }
            }
            training_examples.append(example)
        
        logger.info(f"Generated {len(training_examples)} deck strategy examples")
        return training_examples
    
    def _format_deck_list(self, composition: Dict, deck_info: Dict) -> str:
        """Format a deck list for training input."""
        parts = []
        parts.append(f"Tournament: {deck_info['event_title']}")
        parts.append(f"Player: {deck_info['player_name']}")
        parts.append(f"Rank: {deck_info.get('rank', 'Unknown')}\n")
        
        parts.append("Pokemon:")
        for card in composition['pokemon']:
            parts.append(f"  {card['quantity']}x {card['card_name']}")
        
        parts.append("\nTrainer Cards:")
        for card in composition['trainers']:
            parts.append(f"  {card['quantity']}x {card['card_name']}")
        
        parts.append("\nEnergy:")
        for card in composition['energy']:
            parts.append(f"  {card['quantity']}x {card['card_name']}")
        
        return '\n'.join(parts)
    
    def _analyze_deck_strategy(self, composition: Dict, deck_info: Dict) -> str:
        """Analyze and describe deck strategy."""
        parts = []
        
        # Identify key Pokemon
        key_pokemon = [p for p in composition['pokemon'] if 'ex' in p['card_name'].lower() or 'VMAX' in p['card_name']]
        if key_pokemon:
            parts.append(f"This deck's primary attacker is {key_pokemon[0]['card_name']}, featuring {key_pokemon[0]['quantity']} copies for consistency.")
        
        # Analyze Pokemon count
        total_pokemon = sum(p['quantity'] for p in composition['pokemon'])
        parts.append(f"The deck runs {total_pokemon} Pokemon cards, providing {'good' if 12 <= total_pokemon <= 18 else 'unusual'} consistency.")
        
        # Analyze Trainer strategy
        total_trainers = sum(t['quantity'] for t in composition['trainers'])
        search_cards = [t for t in composition['trainers'] if 'ボール' in t['card_name']]
        if search_cards:
            parts.append(f"It uses {len(search_cards)} different search cards ({', '.join(s['card_name'] for s in search_cards)}) to find Pokemon quickly.")
        
        # Analyze Energy
        total_energy = sum(e['quantity'] for e in composition['energy'])
        parts.append(f"With {total_energy} Energy cards, the deck ensures consistent energy attachment.")
        
        # Tournament success
        parts.append(f"This deck performed well at {deck_info['event_title']}, demonstrating its competitive viability.")
        
        return ' '.join(parts)


class LLMTrainingDataGenerator:
    """Main class to generate complete LLM training dataset."""
    
    def __init__(self, event_db='ptcg_events.db', output_dir='llm_training_data'):
        """Initialize the training data generator."""
        self.event_db = event_db
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        self.card_extractor = PTCGCardDataExtractor(event_db)
        self.rule_extractor = PTCGRuleExtractor()
        self.strategy_extractor = PTCGDeckStrategyExtractor(event_db)
    
    def generate_full_dataset(self) -> Dict:
        """Generate complete training dataset."""
        logger.info("Generating full LLM training dataset...")
        
        # Connect to databases
        self.card_extractor.connect()
        self.strategy_extractor.connect()
        
        try:
            # Generate all training examples
            card_examples = self.card_extractor.generate_card_training_examples()
            rule_examples = self.rule_extractor.get_basic_rules()
            strategy_examples = self.strategy_extractor.generate_deck_strategy_examples()
            
            # Combine all examples
            all_examples = card_examples + rule_examples + strategy_examples
            
            # Create dataset metadata
            dataset = {
                'metadata': {
                    'generated_at': datetime.now().isoformat(),
                    'total_examples': len(all_examples),
                    'card_examples': len(card_examples),
                    'rule_examples': len(rule_examples),
                    'strategy_examples': len(strategy_examples),
                    'source_database': self.event_db
                },
                'examples': all_examples
            }
            
            # Save to file
            output_file = self.output_dir / f'ptcg_training_data_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(dataset, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Saved training dataset to: {output_file}")
            logger.info(f"Total training examples: {len(all_examples)}")
            
            # Generate summary
            self._generate_summary(dataset, output_file)
            
            return dataset
            
        finally:
            # Close connections
            self.card_extractor.close()
            self.strategy_extractor.close()
    
    def _generate_summary(self, dataset: Dict, output_file: Path):
        """Generate a summary report of the training data."""
        summary_file = self.output_dir / 'training_data_summary.txt'
        
        with open(summary_file, 'w', encoding='utf-8') as f:
            f.write("Pokemon TCG LLM Training Data Summary\n")
            f.write("=" * 60 + "\n\n")
            
            f.write(f"Generated: {dataset['metadata']['generated_at']}\n")
            f.write(f"Output File: {output_file}\n\n")
            
            f.write("Dataset Statistics:\n")
            f.write(f"  Total Examples: {dataset['metadata']['total_examples']}\n")
            f.write(f"  Card Examples: {dataset['metadata']['card_examples']}\n")
            f.write(f"  Rule Examples: {dataset['metadata']['rule_examples']}\n")
            f.write(f"  Strategy Examples: {dataset['metadata']['strategy_examples']}\n\n")
            
            f.write("Example Categories:\n")
            categories = {}
            for example in dataset['examples']:
                cat = example['metadata'].get('type', example['metadata'].get('category', 'other'))
                categories[cat] = categories.get(cat, 0) + 1
            
            for cat, count in sorted(categories.items(), key=lambda x: x[1], reverse=True):
                f.write(f"  {cat}: {count}\n")
            
            f.write("\n" + "=" * 60 + "\n")
            f.write("This dataset can be used to fine-tune local LLMs like:\n")
            f.write("  - Llama 2/3\n")
            f.write("  - Mistral\n")
            f.write("  - GPT-J\n")
            f.write("  - Falcon\n\n")
            
            f.write("Recommended Training:\n")
            f.write("  1. Use instruction-following format\n")
            f.write("  2. Train for 3-5 epochs\n")
            f.write("  3. Use learning rate: 2e-5\n")
            f.write("  4. Batch size: 4-8\n")
        
        logger.info(f"Generated summary report: {summary_file}")


def main():
    """Main entry point for generating LLM training data."""
    print("=" * 60)
    print("Pokemon TCG LLM Training Data Generator")
    print("=" * 60)
    print()
    
    generator = LLMTrainingDataGenerator()
    
    print("Generating training data...")
    print("This will create:")
    print("  1. Card knowledge examples")
    print("  2. Game rule examples")
    print("  3. Deck building strategy examples")
    print()
    
    dataset = generator.generate_full_dataset()
    
    print()
    print("✓ Training data generated successfully!")
    print(f"  Total examples: {dataset['metadata']['total_examples']}")
    print(f"  Output directory: llm_training_data/")
    print()
    print("Next steps:")
    print("  1. Review the generated training data")
    print("  2. Choose a local LLM model (Llama, Mistral, etc.)")
    print("  3. Fine-tune using the generated dataset")
    print("  4. Use the trained model for deck building and gameplay simulation")
    print()


if __name__ == '__main__':
    main()
