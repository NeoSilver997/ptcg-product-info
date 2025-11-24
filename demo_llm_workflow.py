#!/usr/bin/env python3
"""
Complete workflow demonstration for PTCG LLM Training System

This script demonstrates the end-to-end process of:
1. Generating training data
2. Using LLM wrapper (mock mode)
3. Simulating deck performance
4. Analyzing tournament patterns
"""

import sys
import os
from pathlib import Path

print("=" * 70)
print(" Pokemon TCG LLM Training System - Complete Workflow Demo")
print("=" * 70)
print()

# Step 1: Generate Training Data
print("STEP 1: Generating Training Data")
print("-" * 70)
print("Extracting knowledge from tournament database...")
print()

from llm_training_data_generator import LLMTrainingDataGenerator

try:
    generator = LLMTrainingDataGenerator()
    dataset = generator.generate_full_dataset()
    
    print(f"✓ Training data generated successfully!")
    print(f"  Total examples: {dataset['metadata']['total_examples']}")
    print(f"  Card examples: {dataset['metadata']['card_examples']}")
    print(f"  Rule examples: {dataset['metadata']['rule_examples']}")
    print(f"  Strategy examples: {dataset['metadata']['strategy_examples']}")
    print()
except Exception as e:
    print(f"✗ Error generating training data: {e}")
    sys.exit(1)

# Step 2: LLM Wrapper Demo
print("\nSTEP 2: LLM Model Wrapper (Mock Mode)")
print("-" * 70)
print("Testing LLM integration without trained model...")
print()

from llm_model_wrapper import PTCGLLMWrapper

try:
    llm = PTCGLLMWrapper(use_mock=True)
    
    # Test 1: Card Analysis
    print("Test 1: Card Analysis")
    analysis = llm.analyze_card("ハイパーボール")
    print(f"Card: {analysis['card_name']}")
    print(f"Analysis: {analysis['analysis'][:150]}...")
    print()
    
    # Test 2: Rules Question
    print("Test 2: Rules Question")
    answer = llm.answer_rules_question("Can I play two Supporter cards in one turn?")
    print(f"Q: Can I play two Supporter cards in one turn?")
    print(f"A: {answer[:120]}...")
    print()
    
    # Test 3: Deck Building
    print("Test 3: Deck Building")
    deck = llm.build_deck_from_archetype("Lightning", ["ピカチュウex"])
    print(f"Built deck for archetype: {deck['archetype']}")
    print(f"Core cards: {', '.join(deck['core_cards'])}")
    print()
    
    print("✓ LLM wrapper working in mock mode!")
    print()
except Exception as e:
    print(f"✗ Error in LLM wrapper: {e}")
    sys.exit(1)

# Step 3: Enhanced Deck Simulator
print("\nSTEP 3: Enhanced Deck Simulator")
print("-" * 70)
print("Analyzing tournament decks and patterns...")
print()

from enhanced_deck_simulator import EnhancedDeckSimulator, TournamentDeckAnalyzer

try:
    # Initialize simulator with LLM
    simulator = EnhancedDeckSimulator(use_llm=True)
    simulator.connect()
    
    # Get a sample deck
    cursor = simulator.conn.execute("SELECT deck_id FROM decks LIMIT 1")
    result = cursor.fetchone()
    if result:
        deck_id = result[0]
        deck = simulator.get_tournament_deck(deck_id)
        
        print(f"Analyzing deck: {deck['player_name']}")
        
        # Evaluate composition
        evaluation = simulator.evaluate_deck_composition(deck['cards'])
        print(f"  Pokemon: {evaluation['composition']['pokemon']} cards")
        print(f"  Trainers: {evaluation['composition']['trainers']} cards")
        print(f"  Energy: {evaluation['composition']['energy']} cards")
        print(f"  Balance Score: {evaluation['balance_score']}/100")
        print(f"  Legal Deck: {'Yes' if evaluation['is_legal'] else 'No (only ' + str(evaluation['composition']['total']) + ' cards)'}")
        print()
        
        # LLM Analysis
        print("LLM Deck Analysis Preview:")
        optimization = simulator.optimize_deck_with_llm(deck)
        preview = optimization['llm_suggestions'][:200]
        print(f"  {preview}...")
        print()
    
    # Analyze tournament patterns
    print("Tournament Pattern Analysis:")
    analyzer = TournamentDeckAnalyzer()
    analyzer.connect()
    
    patterns = analyzer.get_winning_deck_patterns()
    print(f"  Analyzed {patterns['total_analyzed']} winning deck(s)")
    print(f"  Average unique cards: {patterns['avg_unique_cards']:.1f}")
    print(f"  Average Pokemon ex: {patterns['avg_ex_pokemon']:.1f}")
    print(f"  Average Energy: {patterns['avg_energy_cards']:.1f}")
    print()
    
    analyzer.close()
    simulator.close()
    
    print("✓ Deck simulator analysis complete!")
    print()
except Exception as e:
    print(f"✗ Error in deck simulator: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Summary
print("\n" + "=" * 70)
print(" Workflow Complete Summary")
print("=" * 70)
print()
print("✓ Training data generated and saved")
print("✓ LLM wrapper tested (mock mode)")
print("✓ Deck simulator analyzed tournament patterns")
print()
print("Next Steps:")
print("  1. Review training data in: llm_training_data/")
print("  2. Read training guide: LLM_TRAINING_GUIDE.md")
print("  3. Choose LLM model (Llama 2, Mistral, etc.)")
print("  4. Train model using generated dataset")
print("  5. Update LLM wrapper to use trained model:")
print("     llm = PTCGLLMWrapper(model_path='./ptcg_llm_final', use_mock=False)")
print("  6. Integrate with ai_deck_builder.py for deck building")
print()
print("Resources:")
print("  • Training Guide: LLM_TRAINING_GUIDE.md")
print("  • System Overview: LLM_SYSTEM_README.md")
print("  • AI Features: AI_SYSTEM_README.md")
print()
print("For PTCG_CardDB_Tc integration:")
print("  git clone https://github.com/NeoSilver997/PTCG_CardDB_Tc.git")
print()
print("=" * 70)
print(" Ready to train your Pokemon TCG AI! ")
print("=" * 70)
