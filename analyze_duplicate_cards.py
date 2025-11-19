#!/usr/bin/env python3
"""
Analyze cards with same Japanese name but different Chinese names or codes
"""
import os
import json
import glob
from collections import defaultdict

def analyze_duplicate_card_names(event_data_dir="event_data"):
    """Find cards with same name but different codes or details"""
    
    # Dictionary to group cards by their Japanese name
    card_groups = defaultdict(list)
    
    # Load all deck files
    deck_files = glob.glob(f"{event_data_dir}/event_*/deck_*.json")
    print(f"Analyzing {len(deck_files)} deck files...")
    
    for deck_file in deck_files:
        try:
            with open(deck_file, 'r', encoding='utf-8') as f:
                deck_data = json.load(f)
            
            for card in deck_data.get('cards', []):
                card_name = card.get('card_name', '').strip()
                if not card_name:
                    continue
                    
                # Create a card entry with all available information
                card_entry = {
                    'name': card_name,
                    'card_id': card.get('card_id', ''),
                    'card_code': card.get('card_code', ''),
                    'quantity': card.get('quantity', 0),
                    'image_url': card.get('image_url', ''),
                    'deck_file': deck_file
                }
                
                # Group by Japanese card name
                card_groups[card_name].append(card_entry)
        
        except Exception as e:
            print(f"Error reading {deck_file}: {e}")
            continue
    
    # Find cards with multiple different codes/IDs
    duplicate_cards = {}
    
    for card_name, card_list in card_groups.items():
        # Get unique card_ids and card_codes for this name
        unique_ids = set(card.get('card_id', '') for card in card_list if card.get('card_id', ''))
        unique_codes = set(card.get('card_code', '') for card in card_list if card.get('card_code', ''))
        
        # If there are multiple IDs or codes for the same name, it's a duplicate case
        if len(unique_ids) > 1 or len(unique_codes) > 1:
            duplicate_cards[card_name] = {
                'unique_ids': list(unique_ids),
                'unique_codes': list(unique_codes),
                'total_instances': len(card_list),
                'sample_cards': card_list[:5]  # Keep first 5 examples
            }
    
    return duplicate_cards

def analyze_rare_candy_specifically():
    """Specifically look for ふしぎなアメ (Rare Candy) variations"""
    print("\n" + "=" * 80)
    print("RARE CANDY (ふしぎなアメ) ANALYSIS")
    print("=" * 80)
    
    rare_candy_variations = []
    deck_files = glob.glob("event_data/event_*/deck_*.json")
    
    for deck_file in deck_files:
        try:
            with open(deck_file, 'r', encoding='utf-8') as f:
                deck_data = json.load(f)
            
            for card in deck_data.get('cards', []):
                card_name = card.get('card_name', '').strip()
                
                # Look for cards that contain "アメ" or variations
                if 'アメ' in card_name or 'ふしぎ' in card_name or 'Rare Candy' in card_name:
                    rare_candy_variations.append({
                        'name': card_name,
                        'card_id': card.get('card_id', ''),
                        'card_code': card.get('card_code', ''),
                        'deck_file': deck_file
                    })
        
        except Exception as e:
            continue
    
    # Group by name
    candy_groups = defaultdict(list)
    for card in rare_candy_variations:
        candy_groups[card['name']].append(card)
    
    print(f"Found {len(candy_groups)} different Rare Candy name variations:")
    for name, cards in candy_groups.items():
        unique_ids = set(c['card_id'] for c in cards if c['card_id'])
        unique_codes = set(c['card_code'] for c in cards if c['card_code'])
        
        print(f"\nCard Name: {name}")
        print(f"  Instances: {len(cards)}")
        print(f"  Unique IDs: {list(unique_ids)}")
        print(f"  Unique Codes: {list(unique_codes)}")
        
        if len(unique_ids) > 1 or len(unique_codes) > 1:
            print(f"  ⚠️  DUPLICATE DETECTED!")

def main():
    print("=" * 80)
    print("DUPLICATE CARD NAME ANALYSIS")
    print("=" * 80)
    
    # Analyze all duplicate cards
    duplicate_cards = analyze_duplicate_card_names()
    
    if not duplicate_cards:
        print("No duplicate card names found!")
        return
    
    print(f"Found {len(duplicate_cards)} cards with duplicate names:")
    print()
    
    # Sort by number of variations (most problematic first)
    sorted_duplicates = sorted(
        duplicate_cards.items(), 
        key=lambda x: len(x[1]['unique_ids']) + len(x[1]['unique_codes']), 
        reverse=True
    )
    
    for i, (card_name, info) in enumerate(sorted_duplicates[:20], 1):
        print(f"{i}. {card_name}")
        print(f"   Total instances: {info['total_instances']}")
        print(f"   Unique IDs ({len(info['unique_ids'])}): {info['unique_ids']}")
        print(f"   Unique Codes ({len(info['unique_codes'])}): {info['unique_codes']}")
        
        # Show sample variations
        print(f"   Sample variations:")
        for j, sample in enumerate(info['sample_cards'][:3], 1):
            id_part = f"ID:{sample['card_id']}" if sample['card_id'] else "No ID"
            code_part = f"Code:{sample['card_code']}" if sample['card_code'] else "No Code"
            print(f"     {j}. {id_part}, {code_part}")
        print()
    
    # Specific analysis for Rare Candy
    analyze_rare_candy_specifically()
    
    print("\n" + "=" * 80)
    print("RECOMMENDATIONS")
    print("=" * 80)
    print("1. Cards with multiple IDs likely have different Chinese/English names")
    print("2. Cards with multiple codes are from different sets/reprints")  
    print("3. Consider creating a card normalization mapping")
    print("4. Cache lookup should consider card name + set for uniqueness")

if __name__ == "__main__":
    main()