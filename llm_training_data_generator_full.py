"""
Enhanced LLM Training Data Generator - With Full Card Database Integration

This expanded version combines:
1. All cards from pokemon_cards.db (Chinese database with 4,858 cards)
2. Tournament usage data from ptcg_events.db
3. Card abilities, attacks, and detailed descriptions
4. Bilingual card mappings via japanese_card_links
"""

import sqlite3
import json
from pathlib import Path
from typing import List, Dict, Optional
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class EnhancedPTCGCardDataExtractor:
    """Extract card data from both Chinese DB and tournament DB."""
    
    def __init__(self, chinese_db='pokemon_cards.db', event_db='ptcg_events.db'):
        """Initialize the enhanced card data extractor."""
        self.chinese_db_path = chinese_db
        self.event_db_path = event_db
        self.chinese_conn = None
        self.event_conn = None
        
    def connect(self):
        """Connect to both databases."""
        self.chinese_conn = sqlite3.connect(self.chinese_db_path)
        self.chinese_conn.row_factory = sqlite3.Row
        logger.info(f"Connected to Chinese DB: {self.chinese_db_path}")
        
        self.event_conn = sqlite3.connect(self.event_db_path)
        self.event_conn.row_factory = sqlite3.Row
        logger.info(f"Connected to Event DB: {self.event_db_path}")
    
    def close(self):
        """Close database connections."""
        if self.chinese_conn:
            self.chinese_conn.close()
        if self.event_conn:
            self.event_conn.close()
        logger.info("Database connections closed")
    
    def get_all_cards_with_details(self, limit=None) -> List[Dict]:
        """Get all cards from Chinese DB with full details."""
        query = """
            SELECT 
                c.id,
                c.name,
                c.card_type,
                c.hp,
                c.attribute,
                c.weakness,
                c.resistance,
                c.retreat_cost,
                c.collector_number,
                c.rarity,
                c.evolution_stage,
                e.name as expansion_name,
                e.code as expansion_code,
                i.name as illustrator,
                jcl.japanese_name,
                jcl.japanese_card_code,
                jcl.tournament_usage_decks,
                jcl.tournament_usage_copies
            FROM cards c
            LEFT JOIN expansions e ON c.expansion_id = e.id
            LEFT JOIN illustrators i ON c.illustrator_id = i.id
            LEFT JOIN japanese_card_links jcl ON c.id = jcl.card_id
            WHERE c.name IS NOT NULL
            ORDER BY jcl.tournament_usage_decks DESC, c.name
        """
        
        if limit:
            query += f" LIMIT {limit}"
        
        cursor = self.chinese_conn.execute(query)
        cards = [dict(row) for row in cursor.fetchall()]
        logger.info(f"Extracted {len(cards)} cards from Chinese database")
        return cards
    
    def get_card_abilities(self, card_id: int) -> List[Dict]:
        """Get abilities for a card."""
        query = "SELECT name, description FROM abilities WHERE card_id = ?"
        cursor = self.chinese_conn.execute(query, (card_id,))
        return [dict(row) for row in cursor.fetchall()]
    
    def get_card_attacks(self, card_id: int) -> List[Dict]:
        """Get attacks/skills for a card."""
        query = """
            SELECT name, cost, damage, description 
            FROM skills 
            WHERE card_id = ? 
            ORDER BY skill_number
        """
        cursor = self.chinese_conn.execute(query, (card_id,))
        return [dict(row) for row in cursor.fetchall()]

    def _attack_prevents_items(self, attack_desc: Optional[str]) -> bool:
        """Detect if this attack/ability prevents the opponent from playing Item/Trainer-Item cards.

        This uses simple keyword checks; we can extend it with regex/PT translations later.
        """
        if not attack_desc:
            return False
        s = (attack_desc or '').lower()
        # English keywords
        for kw in ['prevent', 'prevents', 'cannot play', 'cannot use', "can't play", 'unable to play', 'stop opponent', 'prevent opponent']:
            if kw in s:
                if 'item' in s or 'item card' in s or 'trainer - item' in s:
                    return True
        # Chinese keywords
        for kw in ['阻止', '禁止', '無法', '不能', '不可以', '禁止從手牌']:
            if kw in attack_desc:
                if '道具' in attack_desc or '物品' in attack_desc or ' 道具卡' in attack_desc:
                    return True
        return False
    
    def get_card_subtypes(self, card_id: int) -> List[str]:
        """Get subtypes for a card (ex, VMAX, etc.)."""
        query = "SELECT subtype FROM subtypes WHERE card_id = ?"
        cursor = self.chinese_conn.execute(query, (card_id,))
        return [row['subtype'] for row in cursor.fetchall()]
    
    def categorize_card(self, card: Dict) -> str:
        """Categorize a card based on its properties."""
        card_type = card.get('card_type', '')
        subtypes = self.get_card_subtypes(card['id'])
        
        # Check for special subtypes first
        if 'ex' in subtypes or 'EX' in subtypes:
            return 'Pokemon ex'
        if 'VMAX' in subtypes:
            return 'Pokemon VMAX'
        if 'VSTAR' in subtypes:
            return 'Pokemon VSTAR'
        if 'V' in subtypes:
            return 'Pokemon V'
        if 'GX' in subtypes:
            return 'Pokemon GX'
        
        # Check card type
        if card_type == '寶可夢':  # Pokemon
            return 'Pokemon'
        elif card_type == '訓練家':  # Trainer
            name = card.get('name', '')
            if '博士' in name or '教授' in name or '支援' in name:
                return 'Supporter'
            elif '體育場' in name or '道館' in name:
                return 'Stadium'
            else:
                return 'Item'
        elif card_type == '能量':  # Energy
            name = card.get('name', '')
            if '基本' in name:
                return 'Basic Energy'
            return 'Special Energy'
        
        return 'Other'
    
    def generate_card_training_examples(self, limit=None) -> List[Dict]:
        """Generate training examples for cards with full details."""
        cards = self.get_all_cards_with_details(limit=limit)
        training_examples = []
        
        logger.info(f"Generating training examples for {len(cards)} cards...")
        
        for i, card in enumerate(cards, 1):
            if i % 100 == 0:
                logger.info(f"  Processed {i}/{len(cards)} cards...")
            
            category = self.categorize_card(card)
            abilities = self.get_card_abilities(card['id'])
            attacks = self.get_card_attacks(card['id'])
            
            # Create training example
            example = {
                'instruction': f"Describe the Pokemon TCG card: {card['name']}",
                'input': self._format_card_input(card, category),
                'output': self._generate_card_description(card, category, abilities, attacks),
                'metadata': {
                    'card_id': card['id'],
                    'card_name': card['name'],
                    'hp': card.get('hp'),
                    'category': category,
                    'expansion': card.get('expansion_name'),
                    'rarity': card.get('rarity'),
                    'tournament_usage': card.get('tournament_usage_decks', 0),
                    'japanese_name': card.get('japanese_name'),
                    'has_abilities': len(abilities) > 0,
                    'has_attacks': len(attacks) > 0
                }
            }
            training_examples.append(example)

            # Create per-attack examples and specific Q/A examples (English + Chinese)
            for attack in attacks:
                # create an attack-level example
                attack_name = attack.get('name') or ''
                attack_desc = attack.get('description') or ''
                attack_damage = attack.get('damage') or ''
                attack_cost = attack.get('cost') or ''

                attack_input = f"Card: {card['name']} | Set: {card.get('expansion_code') or card.get('expansion_name')} | Collector: {card.get('collector_number')}"
                attack_output = f"{attack_name}"
                if attack_cost:
                    attack_output += f" (Cost: {attack_cost})"
                if attack_damage:
                    attack_output += f" - {attack_damage} damage"
                if attack_desc:
                    attack_output += f". Effect: {attack_desc}"

                attack_example = {
                    'instruction': f"Describe the Pokemon TCG attack: {attack_name} ({card['name']})",
                    'input': attack_input,
                    'output': attack_output,
                    'metadata': {
                        'card_id': card['id'],
                        'card_name': card['name'],
                        'hp': card.get('hp'),
                        'attack_name': attack_name,
                        'attack_damage': attack_damage,
                        'attack_cost': attack_cost,
                        'attack_effect': attack_desc,
                        'expansion': card.get('expansion_name'),
                        'collector_number': card.get('collector_number'),
                        'japanese_name': card.get('japanese_name')
                    }
                }
                training_examples.append(attack_example)

                # Create Q/A examples if attack appears to prevent Items or includes 'prevent' keywords
                if self._attack_prevents_items(attack_desc):
                    # English Q/A
                    qa_en = {
                        'instruction': f"Does {card['name']} ({attack_name}) prevent Item cards next turn?",
                        'input': attack_input,
                        'output': f"Yes. {card['name']}'s attack {attack_name} prevents the opponent from playing Item cards from their hand on their next turn.",
                        'metadata': {
                            'card_id': card['id'],
                            'card_name': card['name'],
                            'attack_name': attack_name,
                            'attack_effect': attack_desc,
                            'expansion': card.get('expansion_name'),
                            'collector_number': card.get('collector_number')
                        }
                    }
                    training_examples.append(qa_en)

                    # Chinese Q/A
                    qa_zh = {
                        'instruction': f"{card['name']} 的 {attack_name} 在下個回合是否禁止對手使用物品卡？",
                        'input': attack_input,
                        'output': f"是的。{card['name']} 的攻擊 {attack_name} 會在下一回合阻止對手從手牌使用物品/道具卡。",
                        'metadata': {
                            'card_id': card['id'],
                            'card_name': card['name'],
                            'attack_name': attack_name,
                            'attack_effect': attack_desc,
                            'expansion': card.get('expansion_name'),
                            'collector_number': card.get('collector_number')
                        }
                    }
                    training_examples.append(qa_zh)
        
        logger.info(f"Generated {len(training_examples)} card training examples")
        return training_examples
    
    def _format_card_input(self, card: Dict, category: str) -> str:
        """Format card information as input."""
        parts = []
        
        if card.get('expansion_code'):
            parts.append(f"Expansion: {card['expansion_code']}")
        
        if card.get('collector_number'):
            parts.append(f"Number: {card['collector_number']}")
        
        parts.append(f"Category: {category}")
        
        if card.get('card_type'):
            parts.append(f"Type: {card['card_type']}")
        
        if card.get('hp'):
            parts.append(f"HP: {card['hp']}")
        
        if card.get('attribute'):
            parts.append(f"Attribute: {card['attribute']}")
        
        return "\\n".join(parts)
    
    def _generate_card_description(self, card: Dict, category: str, 
                                   abilities: List[Dict], attacks: List[Dict]) -> str:
        """Generate a detailed description of a card."""
        desc_parts = []
        
        # Basic info
        desc_parts.append(f"{card['name']} is a {category} card from the Pokemon Trading Card Game.")
        
        # Expansion info
        if card.get('expansion_name'):
            desc_parts.append(f"From expansion: {card['expansion_name']}.")
        
        # Pokemon-specific details
        if card.get('hp'):
            desc_parts.append(f"HP: {card['hp']}.")
        
        if card.get('attribute'):
            desc_parts.append(f"Type: {card['attribute']}.")
        
        if card.get('evolution_stage') and card['evolution_stage']:
            desc_parts.append(f"Evolution stage: {card['evolution_stage']}.")
        
        # Abilities
        if abilities:
            for ability in abilities:
                desc_parts.append(f"Ability '{ability['name']}': {ability['description']}")
        
        # Attacks
        if attacks:
            desc_parts.append(f"This card has {len(attacks)} attack(s):")
            for attack in attacks:
                attack_desc = f"{attack['name']}"
                if attack.get('cost'):
                    attack_desc += f" (Cost: {attack['cost']})"
                if attack.get('damage'):
                    attack_desc += f" - {attack['damage']} damage"
                if attack.get('description'):
                    attack_desc += f". Effect: {attack['description']}"
                desc_parts.append(attack_desc)
        
        # Weakness/Resistance
        if card.get('weakness'):
            desc_parts.append(f"Weakness: {card['weakness']} {card.get('weakness_type', '')}.".strip())
        
        if card.get('resistance'):
            desc_parts.append(f"Resistance: {card['resistance']} {card.get('resistance_type', '')}.".strip())
        
        if card.get('retreat_cost') is not None:
            desc_parts.append(f"Retreat cost: {card['retreat_cost']}.")
        
        # Tournament usage
        if card.get('tournament_usage_decks'):
            desc_parts.append(f"Tournament usage: appears in {card['tournament_usage_decks']} competitive decks.")
        
        # Rarity
        if card.get('rarity'):
            desc_parts.append(f"Rarity: {card['rarity']}.")
        
        # Strategic notes based on category
        if category == 'Pokemon ex':
            desc_parts.append("As a Pokemon ex, this card gives up 2 Prize cards when knocked out.")
        elif category == 'Pokemon VMAX':
            desc_parts.append("As a Pokemon VMAX, this card gives up 3 Prize cards when knocked out.")
        elif category == 'Supporter':
            desc_parts.append("As a Supporter card, you can only play one per turn.")
        elif category == 'Item':
            desc_parts.append("As an Item card, you can play multiple per turn.")
        elif category == 'Stadium':
            desc_parts.append("As a Stadium card, only one Stadium can be in play at a time.")
        
        return ' '.join(desc_parts)


# Import other classes from original generator
from llm_training_data_generator import PTCGRuleExtractor, PTCGDeckStrategyExtractor


class EnhancedLLMTrainingDataGenerator:
    """Main class to generate complete LLM training dataset with full card database."""
    
    def __init__(self, chinese_db='pokemon_cards.db', event_db='ptcg_events.db', 
                 output_dir='llm_training_data', card_limit=None):
        """Initialize the enhanced training data generator."""
        self.chinese_db = chinese_db
        self.event_db = event_db
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.card_limit = card_limit
        
        self.card_extractor = EnhancedPTCGCardDataExtractor(chinese_db, event_db)
        self.rule_extractor = PTCGRuleExtractor()
        self.strategy_extractor = PTCGDeckStrategyExtractor(event_db)
    
    def generate_full_dataset(self) -> Dict:
        """Generate complete training dataset with all cards."""
        logger.info("Generating enhanced LLM training dataset with full card database...")
        
        # Connect to databases
        self.card_extractor.connect()
        self.strategy_extractor.connect()
        
        try:
            # Generate all training examples
            card_examples = self.card_extractor.generate_card_training_examples(limit=self.card_limit)
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
                    'source_databases': {
                        'chinese_db': self.chinese_db,
                        'event_db': self.event_db
                    },
                    'card_limit': self.card_limit or 'all'
                },
                'examples': all_examples
            }
            
            # Save to file
            output_file = self.output_dir / f'ptcg_training_data_full_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(dataset, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Saved enhanced training dataset to: {output_file}")
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
        summary_file = self.output_dir / 'training_data_full_summary.txt'
        
        with open(summary_file, 'w', encoding='utf-8') as f:
            f.write("Pokemon TCG LLM Training Data Summary (Full Database)\n")
            f.write("=" * 70 + "\\n\\n")
            
            f.write(f"Generated: {dataset['metadata']['generated_at']}\\n")
            f.write(f"Output File: {output_file}\\n\\n")
            
            f.write("Dataset Statistics:\\n")
            f.write(f"  Total Examples: {dataset['metadata']['total_examples']}\\n")
            f.write(f"  Card Examples: {dataset['metadata']['card_examples']}\\n")
            f.write(f"  Rule Examples: {dataset['metadata']['rule_examples']}\\n")
            f.write(f"  Strategy Examples: {dataset['metadata']['strategy_examples']}\\n\\n")
            
            f.write("Source Databases:\\n")
            f.write(f"  Chinese DB: {dataset['metadata']['source_databases']['chinese_db']}\\n")
            f.write(f"  Event DB: {dataset['metadata']['source_databases']['event_db']}\\n")
            f.write(f"  Card Limit: {dataset['metadata']['card_limit']}\\n\\n")
            
            f.write("Example Categories:\\n")
            categories = {}
            cards_with_abilities = 0
            cards_with_attacks = 0
            tournament_cards = 0
            
            for example in dataset['examples']:
                cat = example['metadata'].get('type', example['metadata'].get('category', 'other'))
                categories[cat] = categories.get(cat, 0) + 1
                
                if example['metadata'].get('has_abilities'):
                    cards_with_abilities += 1
                if example['metadata'].get('has_attacks'):
                    cards_with_attacks += 1
                tournament_usage = example['metadata'].get('tournament_usage', 0)
                if tournament_usage and tournament_usage > 0:
                    tournament_cards += 1
            
            for cat, count in sorted(categories.items(), key=lambda x: x[1], reverse=True):
                f.write(f"  {cat}: {count}\\n")
            
            f.write(f"\\nCards with Abilities: {cards_with_abilities}\\n")
            f.write(f"Cards with Attacks: {cards_with_attacks}\\n")
            f.write(f"Cards with Tournament Usage: {tournament_cards}\\n")
            
            f.write("\\n" + "=" * 70 + "\\n")
            f.write("This dataset includes full card descriptions with:\\n")
            f.write("  - Card abilities and effects\\n")
            f.write("  - Attack names, costs, damage, and effects\\n")
            f.write("  - HP, type, weakness, resistance\\n")
            f.write("  - Tournament usage statistics\\n")
            f.write("  - Evolution stages and subtypes\\n")
            f.write("  - Expansion and rarity information\\n")
        
        logger.info(f"Generated summary report: {summary_file}")


def main():
    """Main entry point for generating enhanced LLM training data."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Generate enhanced Pokemon TCG LLM training data')
    parser.add_argument('--limit', type=int, help='Limit number of cards (default: all)')
    parser.add_argument('--test', action='store_true', help='Generate test dataset with 100 cards')
    args = parser.parse_args()
    
    print("=" * 70)
    print("Pokemon TCG Enhanced LLM Training Data Generator")
    print("=" * 70)
    print()
    
    card_limit = args.limit
    if args.test:
        card_limit = 100
        print("TEST MODE: Generating dataset with 100 cards")
    elif card_limit:
        print(f"Generating dataset with {card_limit} cards")
    else:
        print("Generating dataset with ALL cards from database")
    
    print("This will create:")
    print("  1. Card knowledge with full descriptions, abilities, and attacks")
    print("  2. Game rule examples")
    print("  3. Deck building strategy examples")
    print("  4. Tournament usage statistics")
    print()
    
    generator = EnhancedLLMTrainingDataGenerator(card_limit=card_limit)
    
    dataset = generator.generate_full_dataset()
    
    print()
    print("✓ Enhanced training data generated successfully!")
    print(f"  Total examples: {dataset['metadata']['total_examples']}")
    print(f"  Card examples: {dataset['metadata']['card_examples']}")
    print(f"  Output directory: llm_training_data/")
    print()
    print("Features included:")
    print("  ✓ Full card descriptions with abilities and attacks")
    print("  ✓ Tournament usage statistics")
    print("  ✓ HP, type, weakness, resistance data")
    print("  ✓ Evolution stages and subtypes")
    print("  ✓ Bilingual card mappings (Japanese ↔ Chinese)")
    print()
    print("Next steps:")
    print("  1. Review the generated training data")
    print("  2. Use for LLM fine-tuning (see LLM_TRAINING_GUIDE.md)")
    print("  3. Train model with expanded dataset")
    print()


if __name__ == '__main__':
    main()
