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
    
    def __init__(self, model_path: Optional[str] = None, use_mock: bool = True, include_deck_context: bool = True):
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
        # When transformers is unavailable or not used, prefer using Ollama CLI as a fallback if available
        self.use_ollama_cli = False
        self.include_deck_context = include_deck_context
        
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
            logger.info("Falling back to using Ollama CLI (if available), or mock mode if not")
            # prefer the ollama CLI if present; keep use_mock as the caller specified
            self.use_ollama_cli = True
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            logger.info("Falling back to using Ollama CLI (if available), or mock mode if not")
            self.use_ollama_cli = True
    
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
        # Attempt to retrieve local context and inject it into the prompt to prioritize our data
        local_ctx = self.retrieve_local_context(prompt)
        # If the query looks like Traditional Chinese text, encourage responses in Chinese
        import re
        if re.search(r"[\u4e00-\u9fff]", prompt):
            lang_hint = "請用繁體中文回答。當描述阻止效果時，請明確使用 '下一回合' 或 '下個回合'。"
            prompt = f"{lang_hint}\n\n{prompt}"
        if local_ctx:
            prompt = f"LOCAL_DATA:\n{local_ctx}\n\nUSER_QUERY:\n{prompt}"

        if self.use_mock:
            return self._mock_generate(prompt)
        # If not mock mode and a models path is provided, try using the Ollama CLI for local runs
        if not self.use_mock and (self.model_path or self.use_ollama_cli):
            try:
                import subprocess
                model_for_run = self.model_path or 'ptcg-expert'
                r = subprocess.run(
                    ['ollama', 'run', model_for_run, prompt],
                    capture_output=True,
                    text=True,
                    encoding='utf-8',
                    errors='replace',
                    timeout=120
                )
                if r.returncode == 0:
                    response = r.stdout.strip()
                    # Post-process the LLM response to correct common domain-specific hallucinations
                    response = self._sanitize_response(prompt, response)
                    return response
                else:
                    logger.error(f"ollama run failed: {r.stderr}")
            except Exception as e:
                logger.error(f"Failed to run ollama: {e}")
        
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

            # Post-process the LLM response to correct common domain-specific hallucinations
            response = self._sanitize_response(prompt, response)
            return response
        except RuntimeError as e:
            logger.error(f"Runtime error generating text: {e}")
            return self._mock_generate(prompt)
        except Exception as e:
            logger.error(f"Unexpected error generating text: {e}")
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

        elif "含羞苞" in prompt or "budew" in prompt_lower:
            return ("含羞苞 (Budew) is a Grass-type Pokemon with an effect that prevents your opponent from "
                    "playing Item cards from their hand during their next turn. This is typically used to "
                    "disrupt item-reliant decks and buys time for setup.")
        
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

    def _sanitize_response(self, prompt: str, response: str) -> str:
        """Sanitize and correct common hallucinations in the LLM response.

        Corrects known errors such as claiming a Supporter card costs Energy (it does not),
        or mislabeling Boss's Orders as an Item.
        """
        import re

        p = prompt.lower()
        r = response

        # Specific fix for Boss's Orders (support English, Japanese, Chinese prompts)
        if (('boss' in p and 'orders' in p) or 'ボスの指令' in prompt or '老大的指令' in prompt or '老闆的指令' in prompt):
            # Ensure Supporter label in English/Japanese
            r = re.sub(r"\bItem card\b", "Supporter card", r, flags=re.IGNORECASE)
            r = re.sub(r"\bItem\b", "Supporter", r, flags=re.IGNORECASE)
            # Chinese term: replace 消耗卡牌/道具 (item/consumable) with 支援者 (supporter)
            r = r.replace('消耗卡牌', '支援者卡片')
            r = r.replace('道具卡片', '支援者卡片')

            # Remove incorrect 'costs X energy' or 'requires X energy' assertions (English)
            r = re.sub(r"(?i)costs? \d+\s+energy\b", "", r)
            r = re.sub(r"(?i)requires? \d+\s+energy\b", "", r)
            r = re.sub(r"(?i)costs? \d+\s+Ener","", r)

            # Remove incorrect 'costs energy' or 'requires energy' assertions in Chinese
            r = r.replace('需要能量', '不需要能量')
            r = r.replace('消耗能量', '不需要能量')
            r = r.replace('需要消耗能量', '不需要能量')

            # Remove incorrect 'skip a turn' or '跳過回合' claims
            r = r.replace('須跳過下一個回合', '')
            r = r.replace('跳過下一個回合', '')
            r = r.replace('必須跳過下一個回合', '')

            # If response contained a wrong energy claim, add a corrective note
            if re.search(r"(?i)\b(cost|requires)\b.*\benergy\b", response) or '需要能量' in response:
                r += "\n\nNote: Boss's Orders is a Supporter Trainer card and does not require an Energy cost to play."

            # Add explicit Chinese note if prompt was Chinese and the response lacks explicit 'no energy' phrasing
            if ('老大的指令' in prompt or '老闆' in prompt) and '不需要' not in r and '不需要能量' not in r and '無需能量' not in r:
                r += "\n\n注意: 老大的指令(原 Boss's Orders)是一張支援者卡，使用時不需要支付能量。"

        return r

    def retrieve_local_context(self, query: str, top_n: int = 5) -> str:
        """Retrieve short summaries from local Pokemon Card DB matching tokens in 'query'.

        The function searches the local `pokemon_cards.db` for matching Chinese/English/Japanese
        card names and returns condensed summaries of the most relevant matches. This context
        is prepended to prompts to encourage the model to use our curated data first.
        """
        try:
            import sqlite3
            import os
            from pathlib import Path
            # Prefer the workspace DB (latest) when available; otherwise fallback to the older absolute path
            workspace_db = Path(__file__).resolve().parents[0] / 'pokemon_cards.db'
            fallback_db = Path(r"c:\AI_Server\Coding\PokemonDBByjules\PTCG_CardDB_Tc\pokemon_cards.db")
            MAIN_DB = str(workspace_db) if workspace_db.exists() else str(fallback_db)
            if not os.path.exists(MAIN_DB):
                return ""

            conn = sqlite3.connect(MAIN_DB)
            cursor = conn.cursor()
            # Connect to events DB for deck info (if present)
            events_db = Path(__file__).resolve().parents[0] / 'ptcg_events.db'
            events_conn = None
            if events_db.exists():
                try:
                    events_conn = sqlite3.connect(str(events_db))
                    events_conn.row_factory = sqlite3.Row
                except Exception:
                    events_conn = None

            tokens = []
            import re
            # If the query contains CJK characters, extract those sequences as tokens
            # Match Chinese Han characters and Japanese hiragana/katakana blocks as CJK tokens
            cjk_tokens = re.findall(r"[\u4e00-\u9fff\u3040-\u309f\u30a0-\u30ff]+", query)
            for t in cjk_tokens:
                if len(t) > 0:
                    tokens.append(t.lower())
            # Also extract ASCII tokens
            ascii_tokens = re.findall(r"[A-Za-z0-9\-']{2,}", query)
            for t in ascii_tokens:
                tokens.append(t.lower())

            if not tokens:
                conn.close()
                return ""

            # Detect if the user is asking about tournament usage; if so, include a short summary (top cards)
            include_top_usage = False
            q_low = query.lower()
            usage_keywords = ['tournament usage', 'highest tournament usage', 'tournament', 'usage', 'usage rate', '常用', '比賽', '使用率', '常見']
            for k in usage_keywords:
                if k in q_low:
                    include_top_usage = True
                    break

            results = []
            for tok in tokens:
                # Search Chinese/Japanese names and attack names/descriptions in the main DB
                cursor.execute("""
                    SELECT DISTINCT c.id, c.name, jcl.japanese_name, c.card_type, c.pokemon_info, e.code, c.collector_number, s.name as skill_name, s.description as skill_desc
                    FROM cards c
                    LEFT JOIN japanese_card_links jcl ON c.id = jcl.card_id
                    LEFT JOIN expansions e ON c.expansion_id = e.id
                    LEFT JOIN skills s ON c.id = s.card_id
                    WHERE LOWER(c.name) LIKE ? OR LOWER(jcl.japanese_name) LIKE ? OR LOWER(s.name) LIKE ? OR LOWER(s.description) LIKE ?
                    LIMIT ?
                """, (f"%{tok}%", f"%{tok}%", f"%{tok}%", f"%{tok}%", top_n))
                rows = cursor.fetchall()
                for row in rows:
                    results.append(row)

            if not results:
                # If the query asked about tournament usage and we have no per-card matches,
                # respond with a short TopUsed summary (uses events DB) even without card-level matches
                if include_top_usage:
                    top_usage_text = self._get_top_used_cards_summary(limit=10)
                    if top_usage_text:
                        conn.close()
                        return top_usage_text
                # No matching cards found in main DB - still try to find deck examples directly by token in events DB
                if self.include_deck_context and events_conn and tokens:
                    ed_cursor = events_conn.cursor()
                    deck_summaries = []
                    for tok in tokens:
                        try:
                            ed_cursor.execute("""
                                SELECT d.deck_id, p.player_name, e.event_title, e.event_date
                                FROM deck_cards dc
                                JOIN decks d ON dc.deck_id = d.deck_id
                                JOIN events e ON d.event_id = e.event_id
                                JOIN players p ON d.player_id = p.player_id
                                WHERE LOWER(dc.card_name) LIKE ?
                                GROUP BY d.deck_id
                                ORDER BY SUM(dc.quantity) DESC
                                LIMIT 3
                            """, (f"%{tok}%",))
                            for dr in ed_cursor.fetchall():
                                ed_cursor.execute("""
                                    SELECT card_name, quantity FROM deck_cards
                                    WHERE deck_id = ?
                                    ORDER BY quantity DESC, card_name
                                    LIMIT 6
                                """, (dr['deck_id'],))
                                deck_cards = ed_cursor.fetchall()
                                top_cards = ', '.join([f"{c['quantity']}x {c['card_name']}" for c in deck_cards])
                                deck_summary = f"Deck: {dr['event_title']} by {dr['player_name']} ({dr['deck_id']}) - Top cards: {top_cards}"
                                deck_summaries.append(deck_summary)
                        except Exception:
                            continue
                    if deck_summaries:
                        return '\n'.join([f"DeckExample: {s}" for s in deck_summaries])
                return ""

            # Optionally include top used cards summary if the user query mentions tournament usage
            top_usage_text = ""
            if include_top_usage:
                try:
                    top_usage_text = self._get_top_used_cards_summary(limit=10)
                except Exception:
                    top_usage_text = ""

            # Deduplicate and build context paragraph
            summaries = []
            seen = set()
            # When we have card ids, we can also fetch attacks and include them in the local context
            # Query added skill_name and skill_desc, so accept the extra fields optionally
            for row in results:
                # Unpack with optional skill fields
                if len(row) >= 9:
                    card_id, name_cn, name_jp, card_type, oracle, exp_code, collector, p_skill_name, p_skill_desc = row[:9]
                else:
                    card_id, name_cn, name_jp, card_type, oracle, exp_code, collector = row[:7]
                    p_skill_name, p_skill_desc = None, None
                key = (name_cn, name_jp)
                if key in seen:
                    continue
                seen.add(key)
                summary = f"Card: {name_cn} (JP: {name_jp}) | Type: {card_type} | Set: {exp_code} {collector}."
                if oracle:
                    # Only keep first 150 chars of effect to keep it compact
                    summary += f" Effect: {oracle[:150]}"
                # Attempt deck retrieval first (independent of attack parsing)
                try:
                    deck_rows = []
                    if self.include_deck_context and events_conn:
                        ed_cursor = events_conn.cursor()
                        if name_jp:
                            ed_cursor.execute("""
                                SELECT d.deck_id, p.player_name, e.event_title, e.event_date
                                FROM deck_cards dc
                                JOIN decks d ON dc.deck_id = d.deck_id
                                JOIN events e ON d.event_id = e.event_id
                                JOIN players p ON d.player_id = p.player_id
                                WHERE LOWER(dc.card_name) = ?
                                GROUP BY d.deck_id
                                ORDER BY SUM(dc.quantity) DESC
                                LIMIT 3
                            """, (name_jp.lower(),))
                            deck_rows = ed_cursor.fetchall()
                        if not deck_rows and name_cn:
                            ed_cursor.execute("""
                                SELECT d.deck_id, p.player_name, e.event_title, e.event_date
                                FROM deck_cards dc
                                JOIN decks d ON dc.deck_id = d.deck_id
                                JOIN events e ON d.event_id = e.event_id
                                JOIN players p ON d.player_id = p.player_id
                                WHERE LOWER(dc.card_name) = ?
                                GROUP BY d.deck_id
                                ORDER BY SUM(dc.quantity) DESC
                                LIMIT 3
                            """, (name_cn.lower(),))
                            deck_rows = ed_cursor.fetchall()
                        if not deck_rows:
                            ed_cursor.execute("""
                                SELECT d.deck_id, p.player_name, e.event_title, e.event_date
                                FROM deck_cards dc
                                JOIN decks d ON dc.deck_id = d.deck_id
                                JOIN events e ON d.event_id = e.event_id
                                JOIN players p ON d.player_id = p.player_id
                                WHERE LOWER(dc.card_name) LIKE ?
                                GROUP BY d.deck_id
                                ORDER BY SUM(dc.quantity) DESC
                                LIMIT 3
                            """, (f"%{tok}%",))
                            deck_rows = ed_cursor.fetchall()
                        if not deck_rows:
                            ed_cursor.execute("""
                                SELECT d.deck_id, p.player_name, e.event_title, e.event_date
                                FROM deck_cards dc
                                JOIN decks d ON dc.deck_id = d.deck_id
                                JOIN events e ON d.event_id = e.event_id
                                JOIN players p ON d.player_id = p.player_id
                                WHERE dc.card_id = ?
                                GROUP BY d.deck_id
                                ORDER BY SUM(dc.quantity) DESC
                                LIMIT 3
                            """, (card_id,))
                            deck_rows = ed_cursor.fetchall()
                    else:
                        deck_rows = []
                except Exception:
                    deck_rows = []

                # Pull attacks for this card and include them when present
                try:
                    a_cursor = conn.cursor()
                    a_cursor.execute("SELECT name, description, damage FROM skills WHERE card_id = ?", (card_id,))
                    attacks = a_cursor.fetchall()
                except Exception:
                    attacks = []

                attack_summaries = []
                if attacks:
                    for a_name, a_desc, a_dmg in attacks:
                        a_summary = f"{a_name}"
                        if a_dmg:
                            a_summary += f" - {a_dmg}"
                        if a_desc:
                            a_summary += f": {a_desc[:100]}"
                        # Check if attack prevents items
                        if self._attack_prevents_items(a_desc):
                            a_summary += " [Prevents opponent from playing Item cards next turn]"
                            # Also include a Chinese tag to encourage Traditional Chinese phrasing in outputs
                            a_summary += " [阻止對手使用物品卡(下一回合)]"
                        attack_summaries.append(a_summary)

                # Append deck examples if available
                for dr in (deck_rows or []):
                    try:
                        ed_cursor.execute("""
                            SELECT card_name, quantity
                            FROM deck_cards
                            WHERE deck_id = ?
                            ORDER BY quantity DESC, card_name
                            LIMIT 6
                        """, (dr['deck_id'],))
                        deck_cards = ed_cursor.fetchall()
                        top_cards = ', '.join([f"{c['quantity']}x {c['card_name']}" for c in deck_cards])
                        deck_summary = f"Deck: {dr['event_title']} by {dr['player_name']} ({dr['deck_id']}) - Top cards: {top_cards}"
                        summary += f" DeckExample: {deck_summary}"
                    except Exception:
                        continue

                if attack_summaries:
                    summary += " Attacks: " + ", ".join(attack_summaries)
                summaries.append(summary)
                if len(summaries) >= top_n:
                    break

            # If the query asked about tournament usage, include the top usage summary as well
            if 'top_usage_text' in locals() and top_usage_text:
                summaries.insert(0, top_usage_text)
            out = "\n".join(summaries)
            conn.close()
            return out
        except Exception:
            return ""

    def _attack_prevents_items(self, attack_desc: str) -> bool:
        """Detect if this attack description prevents opponent from playing Item cards.

        Uses basic keyword matching for both Chinese and English descriptions.
        """
        if not attack_desc:
            return False
        s = (attack_desc or '').lower()
        # English checks
        for kw in ['prevent', 'prevents', 'cannot play', "can't play", 'unable to play', 'stop opponent']:
            if kw in s and ('item' in s or 'item card' in s or 'trainer - item' in s or 'item cards' in s):
                return True
        # Chinese checks
        if any(kw in attack_desc for kw in ['阻止', '禁止', '無法', '不能', '不可以']):
            if '道具' in attack_desc or '物品' in attack_desc or '道具卡' in attack_desc or '物品卡' in attack_desc:
                return True
        return False

    def _get_top_used_cards_summary(self, limit: int = 10) -> str:
        """Return a short string summarizing the top-most used cards across tournament decks.

        This pulls from the `ptcg_events.db` `deck_cards` table and returns a formatted
        string like: "Top 10 cards: 1) Boss's Orders - 13653 decks; 2) Hyper Ball - 13066 decks; ..."
        """
        try:
            import sqlite3
            from pathlib import Path
            workspace = Path(__file__).resolve().parents[0]
            events_db = workspace / 'ptcg_events.db'
            if not events_db.exists():
                return ""
            conn = sqlite3.connect(str(events_db))
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            cur.execute('''
                SELECT card_name, COUNT(DISTINCT deck_id) AS deck_count
                FROM deck_cards
                GROUP BY card_name
                ORDER BY deck_count DESC
                LIMIT ?
            ''', (limit,))
            rows = cur.fetchall()
            if not rows:
                return ""
            parts = []
            i = 1
            for r in rows:
                # show top 3 items with JP name and count
                parts.append(f"{i}) {r['card_name']} - {r['deck_count']}")
                i += 1
            conn.close()
            return "Top used cards: " + "; ".join(parts)
        except Exception:
            return ""
    
    def analyze_card(self, card_name: str) -> Dict:
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
