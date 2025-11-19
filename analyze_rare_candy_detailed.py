#!/usr/bin/env python3
"""
Detailed analysis of ふしぎなアメ (Rare Candy) variations
"""
import os
import json
import glob
from collections import defaultdict

def analyze_rare_candy_details():
    """Analyze ふしぎなアメ cards in detail to understand the variations"""
    
    rare_candy_cards = []
    deck_files = glob.glob("event_data/event_*/deck_*.json")
    
    print(f"Searching through {len(deck_files)} deck files...")
    
    for deck_file in deck_files:
        try:
            with open(deck_file, 'r', encoding='utf-8') as f:
                deck_data = json.load(f)
            
            for card in deck_data.get('cards', []):
                card_name = card.get('card_name', '').strip()
                
                if card_name == 'ふしぎなアメ':
                    rare_candy_cards.append({
                        'name': card_name,
                        'card_id': card.get('card_id', ''),
                        'card_code': card.get('card_code', ''),
                        'quantity': card.get('quantity', 0),
                        'image_url': card.get('image_url', ''),
                        'deck_file': deck_file
                    })
        
        except Exception as e:
            continue
    
    print(f"\nFound {len(rare_candy_cards)} ふしぎなアメ cards total")
    
    # Group by card_id to see the variations
    id_groups = defaultdict(list)
    code_groups = defaultdict(list)
    
    for card in rare_candy_cards:
        if card['card_id']:
            id_groups[card['card_id']].append(card)
        if card['card_code']:
            code_groups[card['card_code']].append(card)
    
    print(f"\nUnique card IDs: {len(id_groups)}")
    print(f"Unique card codes: {len(code_groups)}")
    
    # Show some examples of the variations
    print("\nCard ID examples (first 10):")
    for i, (card_id, cards) in enumerate(list(id_groups.items())[:10], 1):
        sample = cards[0]
        print(f"{i:2}. ID: {card_id}")
        print(f"    Code: {sample['card_code'] or 'No code'}")
        print(f"    Image: {sample['image_url'][:50]}..." if sample['image_url'] else "    Image: No image")
        print(f"    Count: {len(cards)} decks")
    
    print("\nCard Code examples (first 10):")
    for i, (card_code, cards) in enumerate(list(code_groups.items())[:10], 1):
        sample = cards[0]
        print(f"{i:2}. Code: {card_code}")
        print(f"    ID: {sample['card_id'] or 'No ID'}")
        print(f"    Image: {sample['image_url'][:50]}..." if sample['image_url'] else "    Image: No image")
        print(f"    Count: {len(cards)} decks")
    
    # Look for patterns in the codes
    print("\n" + "="*80)
    print("CODE ANALYSIS")
    print("="*80)
    
    # Group codes by series
    series_codes = defaultdict(list)
    for code in code_groups.keys():
        if code:
            # Extract series prefix (everything before space)
            parts = code.split(' ')
            if len(parts) >= 2:
                series = parts[0]
                series_codes[series].append(code)
    
    print(f"Card appears in {len(series_codes)} different series:")
    for series, codes in sorted(series_codes.items()):
        print(f"  {series}: {len(codes)} variations")
        for code in sorted(codes)[:3]:  # Show first 3 codes
            count = len(code_groups[code])
            print(f"    - {code} ({count} decks)")
        if len(codes) > 3:
            print(f"    ... and {len(codes) - 3} more")
    
    return rare_candy_cards, id_groups, code_groups

def check_cache_issue():
    """Check how this affects the card code cache"""
    cache_file = "card_code_cache.json"
    
    if not os.path.exists(cache_file):
        print(f"\n{cache_file} not found")
        return
    
    with open(cache_file, 'r', encoding='utf-8') as f:
        cache = json.load(f)
    
    print(f"\n" + "="*80)
    print("CACHE ANALYSIS")
    print("="*80)
    
    # Look for ふしぎなアメ related entries
    rare_candy_cache = {}
    
    for card_id, card_code in cache.items():
        # We need to check the actual card names in deck files to see which IDs are ふしぎなアメ
        # For now, let's just show the cache structure
        pass
    
    print(f"Total cache entries: {len(cache)}")
    print(f"Entries with codes: {sum(1 for v in cache.values() if v)}")
    print(f"Entries marked as not found: {sum(1 for v in cache.values() if v is None)}")

def main():
    print("="*80)
    print("DETAILED ふしぎなアメ (RARE CANDY) ANALYSIS")
    print("="*80)
    
    cards, id_groups, code_groups = analyze_rare_candy_details()
    
    print(f"\n" + "="*80)
    print("FINDINGS")
    print("="*80)
    
    print(f"1. Same card name 'ふしぎなアメ' has {len(id_groups)} different card IDs")
    print(f"2. These IDs map to {len(code_groups)} different card codes")
    print(f"3. This means the same Japanese name refers to different cards:")
    print(f"   - Different sets/expansions")
    print(f"   - Different artwork/versions") 
    print(f"   - Possibly different Chinese/English names")
    
    print(f"\n" + "="*80)
    print("CACHE IMPLICATIONS")
    print("="*80)
    
    print("Current cache system uses card_id as key:")
    print("- Each card_id should map to one unique card_code")
    print("- Multiple card_ids for same Japanese name is expected")
    print("- Problem: cache lookup only by Japanese name would be ambiguous")
    
    print(f"\nRECOMMENDATION:")
    print("- Keep current card_id based caching (correct approach)")
    print("- When fetching codes, use card_id not card_name")
    print("- Multiple IDs for same Japanese name is normal for TCG reprints")
    
    check_cache_issue()

if __name__ == "__main__":
    main()