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
                card_id,
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
    
    def get_card_context(self, card_name: str, card_id: Optional[int] = None, fetch_top_decks: bool = True) -> Dict:
        """Get contextual information about a card from tournament usage."""
        # Skip synergy calculation for performance (expensive self-join on 159K+ rows)
        # This can be re-enabled later if needed, but for initial training it's optional
        synergies = []
        
        # Get deck archetypes using this card
        if fetch_top_decks:
            where_clause = "dc.card_id = ?" if card_id else "dc.card_name = ?"
            archetype_query = f"""
            SELECT DISTINCT d.deck_id, e.event_title, e.event_date, p.player_name
            FROM deck_cards dc
            JOIN decks d ON dc.deck_id = d.deck_id
            JOIN events e ON d.event_id = e.event_id
            JOIN players p ON d.player_id = p.player_id
            WHERE {where_clause}
            ORDER BY e.event_date DESC
            LIMIT 5
        """
            cursor = self.conn.execute(archetype_query, (card_id if card_id else card_name,))
            usage_examples = [dict(row) for row in cursor.fetchall()]
        else:
            usage_examples = []
        # Also return the deck ids and counts where this card appears (top 3)
        if fetch_top_decks:
            where_clause = "dc.card_id = ?" if card_id else "dc.card_name = ?"
            deck_count_query = f"""
            SELECT dc.deck_id, SUM(dc.quantity) as total_quantity, e.event_title, e.event_date, p.player_name
            FROM deck_cards dc
            JOIN decks d ON dc.deck_id = d.deck_id
            JOIN events e ON d.event_id = e.event_id
            JOIN players p ON d.player_id = p.player_id
            WHERE {where_clause}
            GROUP BY dc.deck_id
            ORDER BY total_quantity DESC
            LIMIT 3
        """
            cursor = self.conn.execute(deck_count_query, (card_id if card_id else card_name,))
            top_decks = [dict(row) for row in cursor.fetchall()]
        else:
            top_decks = []
        
        return {
            'synergies': synergies,
            'usage_examples': usage_examples,
            'top_decks': top_decks
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
    
    def generate_card_training_examples(self, limit: Optional[int] = 100) -> List[Dict]:
        """Generate training examples for each card."""
        cards = self.get_all_unique_cards()
        # Limit to top 100 most-used cards for faster initial training
        # These are the most relevant cards from tournament data
        if limit is None:
            logger.info(f"Processing ALL {len(cards)} cards for generation")
            process_count = len(cards)
        else:
            logger.info(f"Processing top {limit} most-used cards (out of {len(cards)} total)")
            process_count = min(limit, len(cards))
            cards = cards[:process_count]
        training_examples = []
        
        for card in cards:
            card_name = card['card_name']
            card_id = card.get('card_id')
            context = self.get_card_context(card_name, card_id=card_id, fetch_top_decks=(limit is not None))
            category = self.categorize_card(card_name, card['card_code'])
            
            # Create training example
            example = {
                'instruction': f"Describe the Pokemon TCG card: {card_name}",
                'input': f"Card Code: {card['card_code']}\nCategory: {category}",
                'output': self._generate_card_description(card, context, category),
                'metadata': {
                    'card_name': card_name,
                    'card_code': card['card_code'],
                    'hp': card.get('hp'),
                    'category': category,
                    'deck_usage': card['deck_count'],
                    'avg_quantity': float(card['avg_quantity'])
                }
            }
            # Add reference to top decks (if any)
            if context.get('top_decks'):
                example['metadata']['popular_decks'] = []
                for d in context.get('top_decks'):
                    example['metadata']['popular_decks'].append({
                        'deck_id': d.get('deck_id'),
                        'total_quantity': d.get('total_quantity'),
                        'event_title': d.get('event_title'),
                        'event_date': d.get('event_date'),
                        'player_name': d.get('player_name')
                    })

            # Create Q/A for which decks include this card and how it is used
            if context.get('usage_examples'):
                usage_text = '; '.join([f"{u['player_name']} ({u['event_title']})" for u in context['usage_examples']])
                example_decks = {
                    'instruction': f'Which tournament decks commonly use {card_name} and why?',
                    'input': f'Card: {card_name} | Recent decks: {usage_text}',
                    'output': f'Top decks using {card_name}: {usage_text}. Typically used for: {"search/attacker/tech depending on category" if category else "utility"}.',
                    'metadata': {
                        'card_name': card_name,
                        'card_code': card['card_code'],
                        'example_decks': [u for u in context['usage_examples'][:3]],
                        'type': 'card_popular_decks'
                    }
                }
                training_examples.append(example_decks)
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
        """Get comprehensive Pokemon TCG rules including advanced mechanics."""
        rules = [
            # Core Game Rules
            {
                'topic': 'Deck Construction',
                'rule': 'A Pokemon TCG deck must contain exactly 60 cards. You can have up to 4 copies of any card with the same name, except for Basic Energy cards (unlimited). Only 1 ACE SPEC card total per deck.',
                'examples': [
                    'Valid: 4x Pikachu ex, 4x Hyper Ball, 15x Basic Lightning Energy, 1x ACE SPEC',
                    'Invalid: 5x Pikachu ex (exceeds 4-copy limit)',
                    'Invalid: 2 different ACE SPEC cards (only 1 ACE SPEC total per deck)'
                ]
            },
            {
                'topic': 'Turn Structure',
                'rule': 'Each turn consists of phases: Draw (draw 1 card), Main Phase (play Pokemon, attach Energy, play Trainers), Attack Phase (attack or end turn). Pokemon Check occurs at end of turn.',
                'examples': [
                    'Turn 1: Draw → Play Pikachu to Bench → Attach Energy to Active → Play Supporter → Attack → Pokemon Check',
                    'You cannot attack on your first turn if you go first.',
                    'Cannot use Supporter cards on first player\'s first turn.'
                ]
            },
            {
                'topic': 'Energy Attachment',
                'rule': 'You can attach one Energy card from your hand to one of your Pokemon each turn. Energy remains attached after attacks. Special Energy cards provide additional effects beyond basic energy types.',
                'examples': [
                    'Attach 1 Basic Lightning Energy to Pikachu ex',
                    'You cannot attach 2 Energy cards in one turn (unless a card effect allows it)',
                    'Energy attached to a Pokemon stays on it even after using an attack'
                ]
            },
            {
                'topic': 'Supporter Cards',
                'rule': 'You can play only one Supporter card during your turn. Discard after use. Cannot use on first player\'s first turn.',
                'examples': [
                    'Play Professor Research to draw 7 cards',
                    'You cannot play Boss Orders after playing Marnie in the same turn',
                    'Going first? Cannot use any Supporter on your very first turn'
                ]
            },
            {
                'topic': 'Prize Cards',
                'rule': 'Win the game by taking all your Prize cards (usually 6). When you knock out an opponent Pokemon, take 1 Prize (2 for Pokemon ex, 3 for Pokemon VMAX). Setup: Place 6 Prize cards face-down at start.',
                'examples': [
                    'Knock out Pikachu ex → Take 2 Prize cards',
                    'First player to take all 6 Prizes wins',
                    'Knock out Charizard VMAX → Take 3 Prize cards'
                ]
            },
            {
                'topic': 'Bench Size',
                'rule': 'You can have up to 5 Pokemon on your Bench at once. Some Stadium cards can modify this limit.',
                'examples': [
                    'Valid: Active Pikachu + 5 Benched Pokemon',
                    'Invalid: Cannot play 6th Pokemon to Bench without discarding one',
                    'Zero Area stadium increases Bench to 8 if you have Tera Pokemon in play'
                ]
            },
            {
                'topic': 'Retreat Cost',
                'rule': 'To retreat your Active Pokemon, discard Energy equal to its Retreat Cost and switch it with a Benched Pokemon. Can only retreat once per turn. Pokemon with no retreat cost marker retreat for free.',
                'examples': [
                    'Pikachu ex has Retreat Cost 1: Discard 1 Energy to retreat',
                    'Free retreat: Pokemon with 0 Retreat Cost can switch for free',
                    'Cannot retreat if you have no Benched Pokemon or insufficient Energy'
                ]
            },
            
            # Pokemon Mechanics
            {
                'topic': 'Abilities',
                'rule': 'Some Pokemon have Abilities in addition to attacks. Two types: declared abilities (player chooses when to use) and automatic abilities (always active). Abilities work while Pokemon is in play unless specified otherwise.',
                'examples': [
                    'Declared: "Once during your turn, you may draw 2 cards" (you choose timing)',
                    'Automatic: "Your Pokemon take 20 less damage from attacks" (always on)',
                    'Abilities stop working if Pokemon is Knocked Out or leaves play'
                ]
            },
            {
                'topic': 'Evolution',
                'rule': 'Can evolve by placing evolution card from hand onto eligible Pokemon (Active or Bench). Cannot evolve same turn Pokemon is played or already evolved. Cannot evolve on either player\'s first turn. Evolved Pokemon keeps damage counters and attached cards, but removes special states.',
                'examples': [
                    'Turn 1: Play Charmander. Turn 2: Can evolve to Charmeleon',
                    'Invalid: Play Charmander and evolve to Charmeleon same turn',
                    'Evolution removes Poison, Paralysis, Sleep, Burn, Confusion',
                    'Damage counters and Energy stay on evolved Pokemon'
                ]
            },
            {
                'topic': 'Placing Pokemon',
                'rule': 'Can place Basic Pokemon from hand to Bench unlimited times per turn as long as Bench space available. Place one at a time.',
                'examples': [
                    'Play Pikachu, Squirtle, and Charmander to Bench in one turn',
                    'Cannot place more than 5 Pokemon on Bench total',
                    'Evolution cards cannot be placed directly - must evolve existing Pokemon'
                ]
            },
            
            # Trainer Cards
            {
                'topic': 'Item Cards',
                'rule': 'Can use unlimited Item cards per turn. Discard after use. No restrictions on timing unless card text specifies.',
                'examples': [
                    'Play Hyper Ball, then Energy Search, then Potion all in one turn',
                    'Item cards are marked "You can play any number of Item cards during your turn"'
                ]
            },
            {
                'topic': 'Stadium Cards',
                'rule': 'Place one Stadium card per turn. Remains in play until replaced by another Stadium. Cannot play if same name Stadium already in play. Both players affected by Stadium effects.',
                'examples': [
                    'Play Training Court stadium - both players can recover Energy',
                    'Opponent plays different Stadium - your Stadium is discarded',
                    'Cannot play Training Court if Training Court already in play'
                ]
            },
            
            # Damage & Combat
            {
                'topic': 'Damage Calculation Order',
                'rule': 'Damage calculation follows specific order: Base damage → +X/-X damage → Weakness/Resistance → Defender effects (damage -X) → Attacker effects (damage +X). Different notation matters.',
                'examples': [
                    '"+30 damage" is calculated in base damage step',
                    '"Damage +30" is applied after weakness/resistance calculation',
                    'Attack 50 damage vs Weakness ×2 → 100 damage before modifiers'
                ]
            },
            {
                'topic': 'Knocked Out (KO)',
                'rule': 'Pokemon with damage ≥ HP is KO\'d. Attacking player takes Prize cards. KO\'d Pokemon and all attached cards go to discard. Replace Active Pokemon from Bench immediately.',
                'examples': [
                    'Pikachu has 100 HP, takes 100 damage → Knocked Out',
                    'KO opponent\'s Active → Take Prize(s) → Opponent promotes Benched Pokemon',
                    'If no Benched Pokemon available when Active is KO\'d → You lose'
                ]
            },
            {
                'topic': 'Pokemon Check',
                'rule': 'Occurs at end of each turn. Check all Pokemon for special conditions in order: Poison → Burn → Sleep → Paralysis. Also check Abilities and Trainer effects that trigger during Pokemon Check.',
                'examples': [
                    'Poisoned Pokemon takes 10 damage (or modified amount)',
                    'Burned Pokemon: Flip coin, heads = no effect, tails = 20 damage',
                    'Sleeping Pokemon: Flip coin, heads = wake up',
                    'Paralyzed Pokemon: Remove Paralysis status'
                ]
            },
            
            # Win Conditions
            {
                'topic': 'Win/Loss Conditions',
                'rule': 'Win by: Taking all 6 Prize cards. Lose by: No Pokemon left on field, or cannot draw card at turn start due to empty deck.',
                'examples': [
                    'Take your 6th Prize card → You win',
                    'Your Active Pokemon is KO\'d and Bench is empty → You lose',
                    'Turn starts, deck is empty, cannot draw → You lose',
                    'Opponent cannot draw at turn start → You win'
                ]
            },
            
            # Advanced Mechanics
            {
                'topic': 'Card Text Precedence',
                'rule': 'Card text takes precedence over rulebook. "Cannot do X" effects override "does X" effects. If conflict, "cannot" wins.',
                'examples': [
                    'Card says "This Pokemon cannot retreat" → Cannot retreat even with Switch card',
                    'Ability says "Cannot be damaged" beats attack that says "Does 100 damage"',
                    'Stadium says "Players cannot play Item cards" → No Items even if card allows it'
                ]
            },
            {
                'topic': 'Effect Duration',
                'rule': 'Effects with timing: "During opponent\'s next turn" lasts until that turn ends. "During your next turn" lasts until your next turn ends. "Until end of turn" expires at turn end.',
                'examples': [
                    '"During opponent\'s next turn, this Pokemon takes -30 damage" → Lasts one opponent turn',
                    '"Until end of your next turn" → Lasts through your next full turn',
                    '"At end of turn" → Triggers after attack, before Pokemon Check'
                ]
            },
            {
                'topic': 'Searching Deck',
                'rule': 'When instructed to select from deck: Look at specified cards, choose required number. Must shuffle deck afterward unless specified otherwise. "Look at X" means view face-down cards then return them face-down.',
                'examples': [
                    '"Search your deck for a Pokemon" → Look through deck, take Pokemon, shuffle',
                    '"Look at top 7 cards" → View them, return face-down unless taking any',
                    'Some cards like Pokegear specify no shuffle required'
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

    def get_all_deck_ids(self, limit: Optional[int] = None) -> List[str]:
        """Return a list of deck ids (optionally limited)."""
        query = """
            SELECT d.deck_id
            FROM decks d
            ORDER BY d.event_id DESC
        """
        if limit:
            cursor = self.conn.execute(query + " LIMIT ?", (limit,))
        else:
            cursor = self.conn.execute(query)
        return [row['deck_id'] for row in cursor.fetchall()]

    def get_deck_metadata(self, deck_id: str) -> Dict:
        """Return deck metadata including player, event, rank and date."""
        query = """
            SELECT d.deck_id, p.player_name, e.event_title, e.event_date, d.rank
            FROM decks d
            JOIN events e ON d.event_id = e.event_id
            JOIN players p ON d.player_id = p.player_id
            WHERE d.deck_id = ?
            LIMIT 1
        """
        cursor = self.conn.execute(query, (deck_id,))
        row = cursor.fetchone()
        if not row:
            return {'deck_id': deck_id}
        return dict(row)
    
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

    def generate_all_deck_examples(self, limit: Optional[int] = 1000) -> List[Dict]:
        """Generate deck-level examples for all decks (optionally limited).

        Includes deck list examples, and Q/A focusing on deck construction and techs.
        """
        deck_ids = self.get_all_deck_ids(limit=limit)
        training_examples = []

        for deck_id in deck_ids:
            deck_meta = self.get_deck_metadata(deck_id)
            composition = self.get_deck_composition(deck_id)

            # Deck list example
            example_list = {
                'instruction': 'Provide a tournament deck list with counts and categories',
                'input': self._format_deck_list(composition, deck_meta),
                'output': self._format_deck_list(composition, deck_meta),
                'metadata': {
                    'deck_id': deck_id,
                    'player': deck_meta.get('player_name'),
                    'event': deck_meta.get('event_title'),
                    'date': deck_meta.get('event_date'),
                    'type': 'deck_list'
                }
            }
            training_examples.append(example_list)

            # Deck strategy analyze example
            example_strategy = {
                'instruction': 'Analyze this Pokemon TCG tournament deck and explain its strategy',
                'input': self._format_deck_list(composition, deck_meta),
                'output': self._analyze_deck_strategy(composition, deck_meta),
                'metadata': {
                    'deck_id': deck_id,
                    'player': deck_meta.get('player_name'),
                    'event': deck_meta.get('event_title'),
                    'date': deck_meta.get('event_date'),
                    'type': 'deck_strategy'
                }
            }
            training_examples.append(example_strategy)

            # Card role Q/A - pick up to 5 cards to generate role-style prompts
            seen = 0
            for section in ['pokemon', 'trainers', 'energy']:
                for card in composition.get(section, []):
                    if seen >= 5:
                        break
                    prompt = {
                        'instruction': f'What role does "{card["card_name"]}" play in this deck? (e.g., win condition, search, tech, consistency)',
                        'input': f"Deck: {deck_meta.get('event_title')} | Player: {deck_meta.get('player_name')}\nCard: {card['card_name']} | Qty: {card['quantity']}",
                        'output': f"Role: {self._guess_card_role(card, composition)}",
                        'metadata': {
                            'deck_id': deck_id,
                            'player': deck_meta.get('player_name'),
                            'event': deck_meta.get('event_title'),
                            'card_name': card['card_name'],
                            'card_qty': card['quantity'],
                            'type': 'deck_card_role'
                        }
                    }
                    training_examples.append(prompt)
                    seen += 1
                if seen >= 5:
                    break

                # Matchup-specific Q/A: use common archetype labels to generate Q/A
            matchups = ['Aggro', 'Control', 'Item-based']
            for opp in matchups:
                matchup_input = f"Deck: {deck_meta.get('event_title')} by {deck_meta.get('player_name')} | Opponent archetype: {opp}"
                example_matchup = {
                    'instruction': 'How does this deck match up against the specified opponent archetype and what adjustments should be made?',
                    'input': matchup_input,
                    'output': f"Against {opp}, this deck is strong in X and weak in Y. Key techs: A, B. Play priority: mulligan, early attach, etc.",
                    'metadata': {
                        'type': 'deck_matchup',
                        'deck_id': deck_id,
                        'opponent_archetype': opp,
                        'player': deck_meta.get('player_name'),
                        'event': deck_meta.get('event_title')
                    }
                }
                training_examples.append(example_matchup)

                # Sideboarding / tech cards suggestions
            for opp in matchups:
                sideboard_example = {
                    'instruction': 'What tech cards or sideboard choices should this deck include against the specified opponent archetype?',
                    'input': f"Deck: {deck_meta.get('event_title')} | Opponent archetype: {opp}",
                    'output': f"Use tech cards like X, Y, Z to address {opp}. Consider swapping A for B in certain matchups.",
                    'metadata': {
                        'type': 'deck_sideboard',
                        'deck_id': deck_id,
                        'opponent_archetype': opp,
                        'player': deck_meta.get('player_name')
                    }
                }
                training_examples.append(sideboard_example)

                # Piloting advice: mulligan, first turn plays, when to use Boss's Orders
            pilot_example = {
                'instruction': 'How should I pilot this deck during a match? Include mulligan policy, first turn plays, and mid-late game win conditions.',
                'input': self._format_deck_list(composition, deck_meta),
                'output': 'Mulligan if you do not have a Basic attacker or enough search cards. On first turn: attach energy to your main attacker if possible and use search cards to establish board. Save Boss\'s Orders for forced KO or to target a bench swap. In mid-game, focus on prize trading and energy efficiency.',
                'metadata': {
                    'type': 'deck_pilot',
                    'deck_id': deck_id,
                    'player': deck_meta.get('player_name'),
                    'event': deck_meta.get('event_title')
                }
            }
            training_examples.append(pilot_example)

        logger.info(f"Generated {len(training_examples)} deck examples (limit {limit})")
        return training_examples

    def _guess_card_role(self, card: Dict, composition: Dict) -> str:
        """Heuristic guess for card role in a deck."""
        name = card.get('card_name', '').lower()
        if any(kw in name for kw in ['エネルギー','energy']):
            return 'Energy; powers attacks and charges key Pokemon.'
        if 'ボール' in name or 'ball' in name.lower() or 'nest' in name.lower():
            return 'Search; provides consistency and fetches key Pokemon.'
        if '博士' in name or 'research' in name.lower() or 'draw' in name.lower():
            return 'Draw engine; increases card access and consistency.'
        if 'ボス' in name or "boss" in name.lower() or 'orders' in name.lower():
            return 'Disruption / targeted KO; forces opponent to switch Active Pokemon.'
        return 'Core/attacker or tech; role varies by deck build.'
    
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
    
    def __init__(self, event_db='ptcg_events.db', output_dir='llm_training_data', include_all_decks: bool = False, deck_limit: Optional[int] = 100, include_all_cards: bool = False, card_limit: Optional[int] = 100):
        """Initialize the training data generator."""
        self.event_db = event_db
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        self.card_extractor = PTCGCardDataExtractor(event_db)
        self.rule_extractor = PTCGRuleExtractor()
        self.strategy_extractor = PTCGDeckStrategyExtractor(event_db)
        self.include_all_decks = include_all_decks
        self.deck_limit = deck_limit
        self.include_all_cards = include_all_cards
        self.card_limit = card_limit
    
    def generate_full_dataset(self) -> Dict:
        """Generate complete training dataset."""
        logger.info("Generating full LLM training dataset...")
        
        # Connect to databases
        self.card_extractor.connect()
        self.strategy_extractor.connect()
        
        try:
            # Generate all training examples
            # Decide whether to include all cards or limit the number processed
            if self.include_all_cards:
                # Allow card_limit to override; if card_limit is 0 or None, treat as unlimited
                if self.card_limit and int(self.card_limit) > 0:
                    limit_val = int(self.card_limit)
                else:
                    limit_val = None
                card_examples = self.card_extractor.generate_card_training_examples(limit=limit_val)
            else:
                card_examples = self.card_extractor.generate_card_training_examples(limit=self.card_limit)
            rule_examples = self.rule_extractor.get_basic_rules()
            strategy_examples = self.strategy_extractor.generate_deck_strategy_examples()
            deck_examples = []
            if self.include_all_decks:
                deck_examples = self.strategy_extractor.generate_all_deck_examples(limit=self.deck_limit)
            
            # Combine all examples
            all_examples = card_examples + rule_examples + strategy_examples + deck_examples
            
            # Create dataset metadata
            dataset = {
                'metadata': {
                    'generated_at': datetime.now().isoformat(),
                    'total_examples': len(all_examples),
                    'card_examples': len(card_examples),
                    'rule_examples': len(rule_examples),
                    'strategy_examples': len(strategy_examples),
                    'deck_examples': len(deck_examples),
                    'source_database': self.event_db
                },
                'examples': all_examples
            }
            
            # Save to file
            prefix = 'ptcg_training_data_full' if (self.include_all_decks or len(deck_examples) > 0) else 'ptcg_training_data'
            output_file = self.output_dir / f'{prefix}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
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
    
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--include-all-decks', action='store_true', help='Include examples generated for all (or many) tournament decks')
    parser.add_argument('--deck-limit', type=int, default=100, help='Limit the number of decks when using --include-all-decks')
    parser.add_argument('--include-all-cards', action='store_true', help='Include examples for all cards in the database (may be large)')
    parser.add_argument('--card-limit', type=int, default=100, help='Limit the number of cards processed when not using --include-all-cards')
    args = parser.parse_args()

    generator = LLMTrainingDataGenerator(include_all_decks=args.include_all_decks, deck_limit=args.deck_limit, include_all_cards=args.include_all_cards, card_limit=args.card_limit)
    
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
