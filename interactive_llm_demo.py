"""
Interactive LLM Demo - Test Pokemon TCG AI Assistant
Run this to try different queries and see mock LLM responses
"""
from llm_model_wrapper import PTCGLLMWrapper
import json

def display_banner():
    print("\n" + "=" * 70)
    print("  POKEMON TCG AI ASSISTANT - Interactive Demo")
    print("=" * 70)
    print("\n🤖 Mock Mode Active - Simulating trained LLM responses")
    print("💡 After training a real model, responses will be tournament-specific\n")

def load_training_cards():
    """Load some interesting cards from training data"""
    with open('llm_training_data/ptcg_training_data_20251125_003633.json', encoding='utf-8') as f:
        data = json.load(f)
    
    # Get diverse examples
    cards = []
    seen_categories = set()
    
    for ex in data['examples']:
        if 'card_name' in ex['metadata']:
            category = ex['metadata']['category']
            if category not in seen_categories and len(cards) < 10:
                cards.append(ex['metadata'])
                seen_categories.add(category)
    
    return cards

def demo_card_analysis(llm, cards):
    print("\n" + "=" * 70)
    print("1️⃣  CARD ANALYSIS DEMO")
    print("=" * 70)
    
    print("\n📊 Available cards from training data:")
    for i, card in enumerate(cards[:5], 1):
        print(f"  {i}. {card['card_name']} ({card['category']}) - {card['deck_usage']} decks")
    
    print("\n🔍 Analyzing top card: " + cards[0]['card_name'])
    result = llm.analyze_card(cards[0]['card_name'])
    print(f"\nCategory: {cards[0]['category']}")
    print(f"Tournament Usage: {cards[0]['deck_usage']} decks")
    print(f"Average Copies: {cards[0]['avg_quantity']:.2f}")
    print(f"\n💬 Mock LLM Analysis:")
    print(f"   {result['analysis'][:400]}")

def demo_deck_building(llm, cards):
    print("\n" + "=" * 70)
    print("2️⃣  DECK BUILDING DEMO")
    print("=" * 70)
    
    # Find a Pokemon ex
    pokemon_ex = next((c for c in cards if 'ex' in c.get('category', '')), cards[0])
    
    print(f"\n🎯 Building deck around: {pokemon_ex['card_name']}")
    print(f"   Tournament Usage: {pokemon_ex['deck_usage']} decks")
    
    deck = llm.build_deck_from_archetype("Competitive", [pokemon_ex['card_name']])
    print(f"\n💬 Mock LLM Deck List:")
    print(f"   {deck['decklist'][:500]}...")

def demo_rules_qa(llm):
    print("\n" + "=" * 70)
    print("3️⃣  RULES Q&A DEMO")
    print("=" * 70)
    
    questions = [
        "Can I play two Supporter cards in one turn?",
        "How many cards must be in a legal deck?",
        "Can I attach energy to benched Pokemon?"
    ]
    
    print("\n❓ Testing common rules questions:")
    for i, q in enumerate(questions, 1):
        print(f"\n  Q{i}: {q}")
        answer = llm.answer_rules_question(q)
        print(f"  💬 Mock LLM: {answer[:200]}...")

def demo_deck_optimization(llm):
    print("\n" + "=" * 70)
    print("4️⃣  DECK OPTIMIZATION DEMO")
    print("=" * 70)
    
    sample_deck = [
        {'card_name': 'ピカチュウex', 'quantity': 2},
        {'card_name': 'ライチュウ', 'quantity': 2},
        {'card_name': 'ハイパーボール', 'quantity': 4},
        {'card_name': 'ネストボール', 'quantity': 4},
        {'card_name': 'ボスの指令', 'quantity': 3},
        {'card_name': '基本雷エネルギー', 'quantity': 15}
    ]
    
    print("\n🔧 Sample deck to optimize:")
    total = sum(c['quantity'] for c in sample_deck)
    for card in sample_deck:
        print(f"   {card['quantity']}x {card['card_name']}")
    print(f"\n   Total: {total}/60 cards")
    
    result = llm.suggest_deck_improvements(sample_deck)
    print(f"\n💬 Mock LLM Suggestions:")
    print(f"   {result['suggestions'][:400]}...")

def demo_training_data_stats():
    print("\n" + "=" * 70)
    print("5️⃣  TRAINING DATA STATISTICS")
    print("=" * 70)
    
    with open('llm_training_data/ptcg_training_data_20251125_003633.json', encoding='utf-8') as f:
        data = json.load(f)
    
    print("\n📊 Dataset Overview:")
    print(f"   Total Examples: {data['metadata']['total_examples']}")
    print(f"   Card Examples: {data['metadata']['card_examples']}")
    print(f"   Rule Examples: {data['metadata']['rule_examples']}")
    print(f"   Strategy Examples: {data['metadata']['strategy_examples']}")
    
    # Category breakdown
    categories = {}
    for ex in data['examples']:
        if 'category' in ex['metadata']:
            cat = ex['metadata']['category']
            categories[cat] = categories.get(cat, 0) + 1
        elif 'type' in ex['metadata']:
            cat = ex['metadata']['type']
            categories[cat] = categories.get(cat, 0) + 1
    
    print("\n📋 Category Breakdown:")
    for cat, count in sorted(categories.items(), key=lambda x: x[1], reverse=True):
        print(f"   {cat}: {count} examples")
    
    # Top tournament cards
    cards_with_usage = [ex for ex in data['examples'] if 'deck_usage' in ex['metadata']]
    top_cards = sorted(cards_with_usage, key=lambda x: x['metadata']['deck_usage'], reverse=True)[:5]
    
    print("\n🏆 Top 5 Most-Used Tournament Cards:")
    for i, card in enumerate(top_cards, 1):
        print(f"   {i}. {card['metadata']['card_name']} - {card['metadata']['deck_usage']} decks")

def main():
    display_banner()
    
    # Initialize
    print("⚙️  Initializing LLM wrapper...")
    llm = PTCGLLMWrapper(use_mock=True)
    cards = load_training_cards()
    print("✅ Ready!\n")
    
    # Run all demos
    demo_card_analysis(llm, cards)
    demo_deck_building(llm, cards)
    demo_rules_qa(llm)
    demo_deck_optimization(llm)
    demo_training_data_stats()
    
    # Summary
    print("\n" + "=" * 70)
    print("✅ DEMO COMPLETE")
    print("=" * 70)
    print("\n🎯 What This Demonstrates:")
    print("   • Card analysis with tournament statistics")
    print("   • Deck building recommendations")
    print("   • Rules Q&A system")
    print("   • Deck optimization suggestions")
    print("   • Training data ready for LLM fine-tuning")
    
    print("\n🚀 Next Steps:")
    print("   1. Review training data quality")
    print("   2. Train real LLM model (see LLM_TRAINING_GUIDE.md)")
    print("   3. Replace mock mode with trained model:")
    print("      llm = PTCGLLMWrapper(model_path='./ptcg_llm_final', use_mock=False)")
    print("   4. Integrate with ai_deck_builder.py")
    
    print("\n💡 With a trained model, responses will:")
    print("   • Use actual tournament card synergies")
    print("   • Recommend optimal card quantities")
    print("   • Provide meta-specific deck building advice")
    print("   • Explain strategic decisions based on real data")
    
    print("\n" + "=" * 70 + "\n")

if __name__ == '__main__':
    main()
