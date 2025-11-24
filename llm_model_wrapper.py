"""
LLM Model Wrapper for Pokemon TCG AI System

This module provides integration between trained LLM models and the existing
deck building and gameplay systems.
"""

import json
from typing import Optional, Dict, List
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class PTCGLLMWrapper:
    """Wrapper for trained LLM models to integrate with PTCG AI system."""
    
    def __init__(self, model_path: Optional[str] = None, use_mock: bool = True):
        """
        Initialize the LLM wrapper.
        
        Args:
            model_path: Path to trained model (HuggingFace format)
            use_mock: Use mock responses for testing (default: True)
        """
        self.model_path = model_path
        self.use_mock = use_mock
        self.model = None
        self.tokenizer = None
        
        if not use_mock and model_path:
            self._load_model()
        elif not use_mock:
            logger.warning("No model path provided. Using mock mode.")
            self.use_mock = True
    
    def _load_model(self):
        """Load the trained LLM model."""
        try:
            from transformers import AutoModelForCausalLM, AutoTokenizer
            import torch
            
            logger.info(f"Loading model from {self.model_path}")
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_path)
            self.model = AutoModelForCausalLM.from_pretrained(
                self.model_path,
                torch_dtype=torch.float16,
                device_map="auto",
                low_cpu_mem_usage=True
            )
            logger.info("Model loaded successfully")
        except ImportError:
            logger.error("transformers library not installed. Install with: pip install transformers torch")
            logger.info("Falling back to mock mode")
            self.use_mock = True
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            logger.info("Falling back to mock mode")
            self.use_mock = True
    
    def generate(self, prompt: str, max_length: int = 500, temperature: float = 0.7) -> str:
        """
        Generate text from the LLM.
        
        Args:
            prompt: Input prompt
            max_length: Maximum tokens to generate
            temperature: Sampling temperature
            
        Returns:
            Generated text
        """
        if self.use_mock:
            return self._mock_generate(prompt)
        
        try:
            inputs = self.tokenizer(prompt, return_tensors="pt", truncation=True, max_length=512)
            inputs = {k: v.to(self.model.device) for k, v in inputs.items()}
            
            outputs = self.model.generate(
                **inputs,
                max_length=max_length,
                temperature=temperature,
                do_sample=True,
                top_p=0.9,
                pad_token_id=self.tokenizer.eos_token_id
            )
            
            response = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
            # Remove the prompt from response
            response = response[len(prompt):].strip()
            
            return response
        except Exception as e:
            logger.error(f"Error generating text: {e}")
            return self._mock_generate(prompt)
    
    def _mock_generate(self, prompt: str) -> str:
        """Generate mock responses for testing."""
        prompt_lower = prompt.lower()
        
        # Card analysis
        if "ハイパーボール" in prompt or "hyper ball" in prompt_lower:
            return ("ハイパーボール (Hyper Ball) is a staple Item card in Pokemon TCG. "
                   "It allows you to search your deck for any Pokemon by discarding 2 cards. "
                   "Most competitive decks run 4 copies for maximum consistency. "
                   "It appears in 142+ tournament decks and commonly pairs with "
                   "Ultra Ball, Nest Ball, and other search cards.")
        
        elif "ピカチュウex" in prompt or "pikachu ex" in prompt_lower:
            return ("ピカチュウex is a powerful Lightning-type Pokemon ex with high damage output. "
                   "It appears in 15 tournament decks, typically as a 2-3 copy. "
                   "Best paired with Electric Generator, Nest Ball, and Boss's Orders. "
                   "As a Pokemon ex, it gives up 2 Prize cards when knocked out.")
        
        # Rule questions
        elif "supporter" in prompt_lower and ("per turn" in prompt_lower or "one turn" in prompt_lower):
            return ("You can only play ONE Supporter card during your turn. "
                   "This is a fundamental rule of Pokemon TCG. "
                   "Choose your Supporter carefully based on your current game situation.")
        
        elif "deck" in prompt_lower and "60" in prompt_lower:
            return ("A legal Pokemon TCG deck must contain exactly 60 cards. "
                   "You can have up to 4 copies of any card with the same name, "
                   "except Basic Energy cards which have no limit.")
        
        # Deck building
        elif "build" in prompt_lower and "deck" in prompt_lower:
            if "pikachu" in prompt_lower or "ピカチュウ" in prompt:
                return """Here's a competitive Pikachu ex deck:

Pokemon (15):
  3x Pikachu ex - Primary attacker
  2x Raichu - Evolution option
  2x Dedenne - Support
  2x Zeraora - Bench sniper
  2x Crobat V - Draw support
  2x Manaphy - Bench protection
  2x Radiant Greninja - Energy acceleration

Trainer Cards (30):
  4x Hyper Ball - Pokemon search
  4x Nest Ball - Basic Pokemon search
  4x Boss's Orders - Gust effect
  3x Marnie - Disruption
  2x Professor's Research - Draw power
  2x Pokemon Catcher - Gust alternative
  2x Switch - Retreat aid
  2x Energy Switch - Energy movement
  2x Rare Candy - Evolution
  2x Electric Generator - Energy acceleration
  2x Stadium Card - Field control
  1x Hisuian Heavy Ball - Search

Energy (15):
  15x Basic Lightning Energy

Strategy: Use Pikachu ex for heavy damage, supported by search cards for consistency."""
            else:
                return """To build a competitive deck:
1. Choose 2-3 primary attackers (Pokemon ex recommended)
2. Add 10-15 total Pokemon for consistency
3. Include 25-30 Trainer cards:
   - 8-12 search cards (Hyper Ball, Nest Ball)
   - 6-8 Supporter cards (draw and disruption)
   - 8-10 utility Items
4. Add 12-15 Energy cards
5. Ensure total is exactly 60 cards
6. Test and refine based on performance"""
        
        # Strategy questions
        elif "boss" in prompt_lower and "orders" in prompt_lower:
            return ("Boss's Orders is used to force your opponent to switch their Active Pokemon. "
                   "Best used when: (1) Targeting a damaged Pokemon for a knockout, "
                   "(2) Bringing up a Pokemon with high retreat cost to stall, "
                   "(3) Disrupting your opponent's setup. "
                   "Most decks run 3-4 copies.")
        
        elif "energy" in prompt_lower and "attach" in prompt_lower:
            return ("You can attach one Energy card from your hand to one of your Pokemon each turn. "
                   "This is the basic rule. Some cards allow additional attachments: "
                   "Electric Generator (2 Lightning), Gardevoir ex (Psychic), etc. "
                   "Prioritize attaching to your main attacker first.")
        
        # Default response
        else:
            return ("I am a Pokemon TCG expert AI trained on tournament data. "
                   "I can help with: card analysis, deck building, game rules, "
                   "strategy advice, and gameplay simulation. "
                   "Please ask specific questions about Pokemon TCG.")
    
    def analyze_card(self, card_name: str) -> Dict:
        """Analyze a specific card using the LLM."""
        prompt = f"Analyze the Pokemon TCG card: {card_name}. Include its usage, synergies, and strategic value."
        response = self.generate(prompt, max_length=400)
        
        return {
            'card_name': card_name,
            'analysis': response,
            'source': 'llm' if not self.use_mock else 'mock'
        }
    
    def suggest_deck_improvements(self, deck_list: List[Dict]) -> Dict:
        """Suggest improvements for a deck using the LLM."""
        # Format deck list
        deck_str = "Current Deck:\n"
        for card in deck_list:
            deck_str += f"  {card.get('quantity', 1)}x {card.get('card_name', 'Unknown')}\n"
        
        prompt = f"{deck_str}\n\nAnalyze this deck and suggest improvements for competitive play."
        response = self.generate(prompt, max_length=600)
        
        return {
            'original_deck': deck_list,
            'suggestions': response,
            'source': 'llm' if not self.use_mock else 'mock'
        }
    
    def explain_game_state(self, game_state_description: str) -> str:
        """Get strategic advice for a game state."""
        prompt = f"Game State:\n{game_state_description}\n\nWhat is the best strategic move and why?"
        return self.generate(prompt, max_length=400)
    
    def build_deck_from_archetype(self, archetype: str, core_cards: List[str]) -> Dict:
        """Build a complete deck using LLM guidance."""
        core_str = ", ".join(core_cards)
        prompt = (f"Build a competitive Pokemon TCG deck with archetype: {archetype}\n"
                 f"Core cards: {core_str}\n"
                 f"Provide a complete 60-card decklist with quantities.")
        
        response = self.generate(prompt, max_length=800)
        
        return {
            'archetype': archetype,
            'core_cards': core_cards,
            'decklist': response,
            'source': 'llm' if not self.use_mock else 'mock'
        }
    
    def answer_rules_question(self, question: str) -> str:
        """Answer a rules question using the LLM."""
        prompt = f"Pokemon TCG Rules Question: {question}\n\nProvide a clear, accurate answer with examples."
        return self.generate(prompt, max_length=400)


class LLMDeckOptimizer:
    """Use LLM to optimize deck compositions."""
    
    def __init__(self, llm_wrapper: PTCGLLMWrapper):
        """Initialize with an LLM wrapper."""
        self.llm = llm_wrapper
    
    def optimize_card_ratios(self, deck_list: List[Dict]) -> Dict:
        """Optimize card quantities in a deck."""
        # Analyze current ratios
        total_cards = sum(card.get('quantity', 1) for card in deck_list)
        
        prompt = f"This deck has {total_cards} cards. Optimize the card quantities:\n"
        for card in deck_list:
            prompt += f"  {card.get('quantity', 1)}x {card.get('card_name', 'Unknown')}\n"
        prompt += "\nSuggest optimal quantities for competitive play."
        
        response = self.llm.generate(prompt, max_length=600)
        
        return {
            'original_total': total_cards,
            'optimization_suggestions': response
        }
    
    def suggest_tech_cards(self, deck_list: List[Dict], meta_context: str = "") -> Dict:
        """Suggest tech cards for current meta."""
        prompt = "Current deck core cards:\n"
        for card in deck_list[:10]:  # Show first 10 cards
            prompt += f"  {card.get('card_name', 'Unknown')}\n"
        
        if meta_context:
            prompt += f"\nMeta context: {meta_context}\n"
        
        prompt += "\nSuggest tech cards to improve this deck's matchups."
        
        response = self.llm.generate(prompt, max_length=500)
        
        return {
            'tech_suggestions': response
        }
    
    def find_card_replacements(self, card_name: str, deck_context: List[str]) -> Dict:
        """Find alternative cards for a specific card."""
        context_str = ", ".join(deck_context[:5])
        
        prompt = (f"In a deck with: {context_str}\n"
                 f"Suggest alternative cards to replace: {card_name}\n"
                 f"Consider synergies and competitive viability.")
        
        response = self.llm.generate(prompt, max_length=400)
        
        return {
            'card_to_replace': card_name,
            'alternatives': response
        }


def main():
    """Example usage of the LLM wrapper."""
    print("=" * 60)
    print("Pokemon TCG LLM Model Wrapper")
    print("=" * 60)
    print()
    
    # Initialize LLM (mock mode for testing)
    print("Initializing LLM wrapper (mock mode)...")
    llm = PTCGLLMWrapper(use_mock=True)
    print("✓ LLM initialized\n")
    
    # Example 1: Card analysis
    print("Example 1: Card Analysis")
    print("-" * 40)
    analysis = llm.analyze_card("ハイパーボール")
    print(f"Card: {analysis['card_name']}")
    print(f"Analysis: {analysis['analysis']}\n")
    
    # Example 2: Rules question
    print("Example 2: Rules Question")
    print("-" * 40)
    answer = llm.answer_rules_question("Can I play two Supporter cards in one turn?")
    print(f"Answer: {answer}\n")
    
    # Example 3: Deck building
    print("Example 3: Deck Building")
    print("-" * 40)
    deck = llm.build_deck_from_archetype("Lightning", ["ピカチュウex"])
    print(f"Archetype: {deck['archetype']}")
    print(f"Decklist:\n{deck['decklist']}\n")
    
    # Example 4: Deck optimization
    print("Example 4: Deck Optimization")
    print("-" * 40)
    sample_deck = [
        {'card_name': 'ピカチュウex', 'quantity': 2},
        {'card_name': 'ハイパーボール', 'quantity': 4},
        {'card_name': '基本雷エネルギー', 'quantity': 15}
    ]
    suggestions = llm.suggest_deck_improvements(sample_deck)
    print(f"Suggestions:\n{suggestions['suggestions']}\n")
    
    print("=" * 60)
    print("LLM wrapper ready for integration!")
    print()
    print("To use with a real trained model:")
    print("  llm = PTCGLLMWrapper(model_path='./ptcg_llm_final', use_mock=False)")
    print()


if __name__ == '__main__':
    main()
