"""
AI-powered Pokemon TCG gameplay engine.

This module provides AI capabilities for:
- Game state representation
- Move evaluation and decision making
- Basic gameplay simulation
- Strategic play recommendations
"""

import random
from typing import List, Dict, Optional, Tuple
from enum import Enum
from dataclasses import dataclass, field
from collections import defaultdict
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class CardType(Enum):
    """Pokemon TCG card types."""
    POKEMON = "pokemon"
    TRAINER = "trainer"
    ENERGY = "energy"
    SUPPORTER = "supporter"
    ITEM = "item"
    STADIUM = "stadium"


class GamePhase(Enum):
    """Game phases in Pokemon TCG."""
    SETUP = "setup"
    DRAW = "draw"
    MAIN = "main"
    ATTACK = "attack"
    END = "end"


@dataclass
class Card:
    """Represents a Pokemon TCG card."""
    name: str
    card_type: CardType
    hp: int = 0
    attack_cost: List[str] = field(default_factory=list)
    attack_damage: int = 0
    retreat_cost: int = 0
    is_basic: bool = True
    is_ex: bool = False
    
    def __repr__(self):
        return f"Card({self.name}, {self.card_type.value})"


@dataclass
class GameState:
    """Represents the current state of a Pokemon TCG game."""
    # Player 1 state
    p1_active: Optional[Card] = None
    p1_bench: List[Card] = field(default_factory=list)
    p1_hand: List[Card] = field(default_factory=list)
    p1_deck: List[Card] = field(default_factory=list)
    p1_discard: List[Card] = field(default_factory=list)
    p1_prizes: int = 6
    
    # Player 2 state
    p2_active: Optional[Card] = None
    p2_bench: List[Card] = field(default_factory=list)
    p2_hand: List[Card] = field(default_factory=list)
    p2_deck: List[Card] = field(default_factory=list)
    p2_discard: List[Card] = field(default_factory=list)
    p2_prizes: int = 6
    
    # Game state
    current_player: int = 1
    phase: GamePhase = GamePhase.SETUP
    turn_number: int = 0
    stadium_card: Optional[Card] = None
    
    # Action tracking
    actions_taken: List[str] = field(default_factory=list)
    supporter_played: bool = False
    attached_energy: bool = False
    
    def __repr__(self):
        return f"GameState(Turn {self.turn_number}, {self.phase.value}, P{self.current_player})"


class Move:
    """Represents a possible move in the game."""
    
    def __init__(self, move_type: str, card: Optional[Card] = None, 
                 target: Optional[str] = None, description: str = ""):
        self.move_type = move_type
        self.card = card
        self.target = target
        self.description = description
    
    def __repr__(self):
        return f"Move({self.move_type}: {self.description})"


class GameRules:
    """Implements basic Pokemon TCG game rules."""
    
    MAX_BENCH_SIZE = 5
    MAX_HAND_SIZE = None  # No hand limit unless specified
    STARTING_HAND_SIZE = 7
    
    @staticmethod
    def is_valid_move(state: GameState, move: Move) -> bool:
        """Check if a move is valid in the current game state."""
        current_hand = state.p1_hand if state.current_player == 1 else state.p2_hand
        current_bench = state.p1_bench if state.current_player == 1 else state.p2_bench
        
        if move.move_type == "play_pokemon":
            if move.card not in current_hand:
                return False
            if len(current_bench) >= GameRules.MAX_BENCH_SIZE:
                return False
            return True
        
        elif move.move_type == "play_supporter":
            if move.card not in current_hand:
                return False
            if state.supporter_played:
                return False
            return True
        
        elif move.move_type == "attach_energy":
            if move.card not in current_hand:
                return False
            if state.attached_energy:
                return False
            return True
        
        elif move.move_type == "attack":
            if state.phase != GamePhase.MAIN:
                return False
            active = state.p1_active if state.current_player == 1 else state.p2_active
            if not active:
                return False
            return True
        
        return True
    
    @staticmethod
    def apply_move(state: GameState, move: Move) -> GameState:
        """Apply a move to the game state and return the new state."""
        # This is a simplified implementation
        state.actions_taken.append(move.description)
        
        if move.move_type == "play_pokemon":
            if state.current_player == 1:
                state.p1_hand.remove(move.card)
                state.p1_bench.append(move.card)
            else:
                state.p2_hand.remove(move.card)
                state.p2_bench.append(move.card)
        
        elif move.move_type == "attach_energy":
            state.attached_energy = True
            if state.current_player == 1:
                state.p1_hand.remove(move.card)
            else:
                state.p2_hand.remove(move.card)
        
        elif move.move_type == "play_supporter":
            state.supporter_played = True
            if state.current_player == 1:
                state.p1_hand.remove(move.card)
                state.p1_discard.append(move.card)
            else:
                state.p2_hand.remove(move.card)
                state.p2_discard.append(move.card)
        
        elif move.move_type == "end_turn":
            state.current_player = 2 if state.current_player == 1 else 1
            state.turn_number += 1
            state.supporter_played = False
            state.attached_energy = False
            state.actions_taken = []
        
        return state
    
    @staticmethod
    def check_win_condition(state: GameState) -> Optional[int]:
        """Check if game has been won. Returns winner (1 or 2) or None."""
        if state.p1_prizes <= 0:
            return 1
        if state.p2_prizes <= 0:
            return 2
        
        # Check for deck out
        if len(state.p1_deck) == 0 and state.current_player == 1:
            return 2
        if len(state.p2_deck) == 0 and state.current_player == 2:
            return 1
        
        return None


class MoveEvaluator:
    """Evaluates and scores possible moves using heuristics."""
    
    def __init__(self):
        """Initialize the move evaluator."""
        self.weights = {
            'damage': 1.0,
            'board_presence': 0.8,
            'card_advantage': 0.7,
            'energy_efficiency': 0.6,
            'prize_trade': 1.5
        }
    
    def evaluate_move(self, state: GameState, move: Move) -> float:
        """
        Evaluate a move and return a score.
        Higher scores indicate better moves.
        """
        score = 0.0
        
        if move.move_type == "attack":
            # Prioritize attacking when possible
            score += 10.0 * self.weights['damage']
            
            # Bonus for potentially knocking out opponent
            opponent_active = state.p2_active if state.current_player == 1 else state.p1_active
            if opponent_active and opponent_active.hp <= 120:  # Assume attack does ~100 damage
                score += 20.0 * self.weights['prize_trade']
        
        elif move.move_type == "play_pokemon":
            # Playing Pokemon increases board presence
            current_bench = state.p1_bench if state.current_player == 1 else state.p2_bench
            if len(current_bench) < 3:
                score += 5.0 * self.weights['board_presence']
            else:
                score += 2.0 * self.weights['board_presence']
        
        elif move.move_type == "attach_energy":
            # Energy attachment is crucial
            if not state.attached_energy:
                score += 8.0 * self.weights['energy_efficiency']
        
        elif move.move_type == "play_supporter":
            # Supporters provide card advantage
            if not state.supporter_played:
                score += 7.0 * self.weights['card_advantage']
        
        elif move.move_type == "end_turn":
            # Ending turn is the default lowest priority
            score += 1.0
        
        return score
    
    def get_best_move(self, state: GameState, possible_moves: List[Move]) -> Move:
        """Select the best move from possible moves."""
        if not possible_moves:
            return Move("end_turn", description="No valid moves available")
        
        # Evaluate all moves
        move_scores = [(move, self.evaluate_move(state, move)) for move in possible_moves]
        
        # Sort by score
        move_scores.sort(key=lambda x: x[1], reverse=True)
        
        logger.debug(f"Move evaluation:")
        for move, score in move_scores[:3]:
            logger.debug(f"  {move.description}: {score:.2f}")
        
        return move_scores[0][0]


class GameAI:
    """AI player for Pokemon TCG."""
    
    def __init__(self, difficulty: str = "normal"):
        """
        Initialize AI player.
        
        Args:
            difficulty: AI difficulty level (easy, normal, hard)
        """
        self.difficulty = difficulty
        self.evaluator = MoveEvaluator()
        self.move_history = []
    
    def get_possible_moves(self, state: GameState) -> List[Move]:
        """Generate all possible moves for the current player."""
        moves = []
        
        current_hand = state.p1_hand if state.current_player == 1 else state.p2_hand
        
        # Check for Pokemon plays
        for card in current_hand:
            if card.card_type == CardType.POKEMON:
                move = Move(
                    "play_pokemon",
                    card=card,
                    description=f"Play {card.name} to bench"
                )
                if GameRules.is_valid_move(state, move):
                    moves.append(move)
        
        # Check for energy attachment
        if not state.attached_energy:
            for card in current_hand:
                if card.card_type == CardType.ENERGY:
                    move = Move(
                        "attach_energy",
                        card=card,
                        description=f"Attach {card.name} to active Pokemon"
                    )
                    if GameRules.is_valid_move(state, move):
                        moves.append(move)
                        break  # Only one energy per turn
        
        # Check for supporter plays
        if not state.supporter_played:
            for card in current_hand:
                if card.card_type == CardType.SUPPORTER:
                    move = Move(
                        "play_supporter",
                        card=card,
                        description=f"Play supporter: {card.name}"
                    )
                    if GameRules.is_valid_move(state, move):
                        moves.append(move)
        
        # Check for attacks
        active = state.p1_active if state.current_player == 1 else state.p2_active
        if active and state.phase == GamePhase.MAIN:
            move = Move(
                "attack",
                description=f"Attack with {active.name}"
            )
            if GameRules.is_valid_move(state, move):
                moves.append(move)
        
        # Always can end turn
        moves.append(Move("end_turn", description="End turn"))
        
        return moves
    
    def choose_move(self, state: GameState) -> Move:
        """Choose the best move for the current game state."""
        possible_moves = self.get_possible_moves(state)
        
        if self.difficulty == "easy":
            # Random moves
            return random.choice(possible_moves)
        elif self.difficulty == "hard":
            # Always choose best move
            return self.evaluator.get_best_move(state, possible_moves)
        else:
            # Normal: mostly best move with some randomness
            if random.random() < 0.8:
                return self.evaluator.get_best_move(state, possible_moves)
            else:
                return random.choice(possible_moves)
    
    def play_turn(self, state: GameState) -> GameState:
        """Play a complete turn."""
        logger.info(f"AI Turn {state.turn_number} - Player {state.current_player}")
        
        actions = 0
        max_actions = 10  # Prevent infinite loops
        
        while actions < max_actions:
            move = self.choose_move(state)
            
            if not GameRules.is_valid_move(state, move):
                logger.warning(f"Invalid move attempted: {move.description}")
                break
            
            logger.info(f"  Action: {move.description}")
            state = GameRules.apply_move(state, move)
            self.move_history.append(move)
            
            if move.move_type == "end_turn":
                break
            
            actions += 1
        
        return state


class GameSimulator:
    """Simulates Pokemon TCG games for testing and analysis."""
    
    def __init__(self):
        """Initialize game simulator."""
        self.games_played = 0
        self.results = defaultdict(int)
    
    def create_sample_deck(self) -> List[Card]:
        """Create a simple sample deck for testing."""
        deck = []
        
        # Add Pokemon (15 cards)
        for i in range(10):
            deck.append(Card(
                name=f"Basic Pokemon {i+1}",
                card_type=CardType.POKEMON,
                hp=60 + i * 10,
                is_basic=True
            ))
        
        for i in range(5):
            deck.append(Card(
                name=f"Pokemon ex {i+1}",
                card_type=CardType.POKEMON,
                hp=180 + i * 20,
                is_basic=True,
                is_ex=True
            ))
        
        # Add Trainers (30 cards)
        for i in range(15):
            deck.append(Card(
                name=f"Supporter {i+1}",
                card_type=CardType.SUPPORTER
            ))
        
        for i in range(15):
            deck.append(Card(
                name=f"Item {i+1}",
                card_type=CardType.ITEM
            ))
        
        # Add Energy (15 cards)
        for i in range(15):
            deck.append(Card(
                name="Basic Energy",
                card_type=CardType.ENERGY
            ))
        
        return deck
    
    def setup_game(self) -> GameState:
        """Setup a new game with starting hands."""
        state = GameState()
        
        # Create decks
        state.p1_deck = self.create_sample_deck()
        state.p2_deck = self.create_sample_deck()
        
        # Shuffle
        random.shuffle(state.p1_deck)
        random.shuffle(state.p2_deck)
        
        # Draw starting hands
        state.p1_hand = [state.p1_deck.pop() for _ in range(GameRules.STARTING_HAND_SIZE)]
        state.p2_hand = [state.p2_deck.pop() for _ in range(GameRules.STARTING_HAND_SIZE)]
        
        # Setup active Pokemon (simplified - just take first Pokemon from hand or deck)
        for card in state.p1_hand:
            if card.card_type == CardType.POKEMON and card.is_basic:
                state.p1_active = card
                state.p1_hand.remove(card)
                break
        
        for card in state.p2_hand:
            if card.card_type == CardType.POKEMON and card.is_basic:
                state.p2_active = card
                state.p2_hand.remove(card)
                break
        
        state.phase = GamePhase.MAIN
        return state
    
    def simulate_game(self, max_turns: int = 10) -> Dict:
        """
        Simulate a game between two AI players.
        
        Args:
            max_turns: Maximum number of turns before game ends
        
        Returns:
            Game result dictionary
        """
        state = self.setup_game()
        ai1 = GameAI(difficulty="normal")
        ai2 = GameAI(difficulty="normal")
        
        logger.info("=== Starting Game Simulation ===")
        logger.info(f"P1 Active: {state.p1_active}")
        logger.info(f"P2 Active: {state.p2_active}")
        
        turn_count = 0
        while turn_count < max_turns:
            turn_count += 1
            
            # Player 1 turn
            state.current_player = 1
            state = ai1.play_turn(state)
            
            # Check win condition
            winner = GameRules.check_win_condition(state)
            if winner:
                logger.info(f"Player {winner} wins!")
                return {
                    'winner': winner,
                    'turns': turn_count,
                    'reason': 'prizes'
                }
            
            # Player 2 turn
            state.current_player = 2
            state = ai2.play_turn(state)
            
            # Check win condition
            winner = GameRules.check_win_condition(state)
            if winner:
                logger.info(f"Player {winner} wins!")
                return {
                    'winner': winner,
                    'turns': turn_count,
                    'reason': 'prizes'
                }
        
        # Game ended due to turn limit
        logger.info("Game ended due to turn limit")
        return {
            'winner': None,
            'turns': turn_count,
            'reason': 'turn_limit'
        }
    
    def run_simulations(self, num_games: int = 5) -> Dict:
        """Run multiple game simulations and collect statistics."""
        results = {
            'games_played': num_games,
            'p1_wins': 0,
            'p2_wins': 0,
            'draws': 0,
            'avg_turns': 0,
            'details': []
        }
        
        total_turns = 0
        
        for i in range(num_games):
            logger.info(f"\n--- Game {i+1}/{num_games} ---")
            result = self.simulate_game(max_turns=10)
            results['details'].append(result)
            
            if result['winner'] == 1:
                results['p1_wins'] += 1
            elif result['winner'] == 2:
                results['p2_wins'] += 1
            else:
                results['draws'] += 1
            
            total_turns += result['turns']
        
        results['avg_turns'] = total_turns / num_games if num_games > 0 else 0
        
        return results


def main():
    """Example usage of the AI gameplay system."""
    print("=== Pokemon TCG AI Gameplay Engine ===\n")
    
    # Run game simulations
    simulator = GameSimulator()
    
    print("🎮 Running game simulations...\n")
    results = simulator.run_simulations(num_games=3)
    
    print("\n📊 Simulation Results:")
    print(f"  Games played: {results['games_played']}")
    print(f"  Player 1 wins: {results['p1_wins']}")
    print(f"  Player 2 wins: {results['p2_wins']}")
    print(f"  Draws: {results['draws']}")
    print(f"  Average turns: {results['avg_turns']:.1f}")
    
    print("\n✓ AI Gameplay Engine initialized successfully!")


if __name__ == '__main__':
    main()
