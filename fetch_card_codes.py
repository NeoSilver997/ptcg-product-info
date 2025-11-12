#!/usr/bin/env python3
"""
Fetch card codes for cards with missing card_code
Uses the Pokemon card search website to get card codes
"""
import os
import json
import glob
import time
import requests
from bs4 import BeautifulSoup
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Cache file to store card_id -> card_code mappings
CACHE_FILE = "card_code_cache.json"

def load_cache():
    """Load card code cache from file"""
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                cache = json.load(f)
                logger.info(f"Loaded cache with {len(cache)} card codes")
                return cache
        except Exception as e:
            logger.warning(f"Error loading cache: {e}")
            return {}
    return {}

def save_cache(cache):
    """Save card code cache to file"""
    try:
        with open(CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)
        logger.info(f"Saved cache with {len(cache)} card codes")
    except Exception as e:
        logger.error(f"Error saving cache: {e}")

def get_card_code(card_id, cache=None):
    """
    Fetch card code from Pokemon card search website
    
    Args:
        card_id: The card ID to search for
        cache: Optional cache dictionary to check first
    
    Returns:
        The card code (e.g., "SVN 023/045") or None if not found
    """
    # Check cache first
    if cache is not None and str(card_id) in cache:
        logger.info(f"Found card code for {card_id} in cache: {cache[str(card_id)]}")
        return cache[str(card_id)]
    
    url = f"https://www.pokemon-card.com/card-search/details.php/card/{card_id}/regu/all"
    
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Step 1: Get series code from img-regulation alt text
        img_regulation = soup.find('img', class_='img-regulation')
        series_code = None
        
        if img_regulation:
            series_code = img_regulation.get('alt', '').strip()
        
        if not series_code:
            logger.warning(f"No series code found for card {card_id}")
            return None
        
        # Step 2: Get card number (e.g., "023/045")
        page_text = soup.get_text()
        import re
        
        # Pattern: number / number with possible whitespace (e.g., "023 / 045")
        # Using \xa0 for non-breaking space that appears in HTML
        pattern = r'(\d{3}[\s\xa0]*/[\s\xa0]*\d{3})'
        matches = re.findall(pattern, page_text)
        
        if matches:
            # Clean up the card number (remove extra spaces)
            card_number = matches[0].replace('\xa0', ' ').replace(' / ', '/').strip()
            card_code = f"{series_code} {card_number}"
            logger.info(f"Found card code for {card_id}: {card_code}")
            return card_code
        
        logger.warning(f"No card number found for card {card_id} (series: {series_code})")
        return None
    
    except Exception as e:
        logger.error(f"Error fetching card code for {card_id}: {e}")
        return None
    
    except Exception as e:
        logger.error(f"Error fetching card code for {card_id}: {e}")
        return None

def find_cards_with_missing_codes(event_data_dir="event_data"):
    """
    Find all cards with empty or missing card_code
    
    Returns:
        Dictionary mapping card_id to card info
    """
    missing_codes = {}
    deck_files = glob.glob(f"{event_data_dir}/event_*/deck_*.json")
    
    logger.info(f"Scanning {len(deck_files)} deck files...")
    
    for deck_file in deck_files:
        try:
            with open(deck_file, 'r', encoding='utf-8') as f:
                deck_data = json.load(f)
            
            for card in deck_data.get('cards', []):
                card_id = card.get('card_id', '')
                card_code = card.get('card_code', '')
                
                if not card_code or card_code.strip() == '':
                    if card_id not in missing_codes:
                        missing_codes[card_id] = {
                            'card_name': card.get('card_name', ''),
                            'deck_files': []
                        }
                    missing_codes[card_id]['deck_files'].append(deck_file)
        
        except Exception as e:
            logger.error(f"Error reading {deck_file}: {e}")
            continue
    
    return missing_codes

def update_card_codes(missing_codes, dry_run=False):
    """
    Update deck files with fetched card codes
    
    Args:
        missing_codes: Dictionary of cards with missing codes
        dry_run: If True, don't actually modify files
    """
    total_cards = len(missing_codes)
    logger.info(f"Found {total_cards} cards with missing card codes")
    
    if total_cards == 0:
        logger.info("No cards with missing card codes found!")
        return
    
    # Load cache
    cache = load_cache()
    cached_count = sum(1 for card_id in missing_codes if str(card_id) in cache)
    fetch_count = total_cards - cached_count
    
    logger.info(f"Cache status: {cached_count} cards in cache, {fetch_count} cards to fetch")
    
    # Fetch codes for each card
    card_codes = {}
    for i, (card_id, card_info) in enumerate(missing_codes.items(), 1):
        was_cached = str(card_id) in cache
        
        logger.info(f"[{i}/{total_cards}] Fetching card code for {card_id} ({card_info['card_name']})...")
        card_code = get_card_code(card_id, cache)
        
        if card_code:
            card_codes[card_id] = card_code
            # Add to cache and save immediately if it's a new card (not from cache)
            if not was_cached:
                cache[str(card_id)] = card_code
                save_cache(cache)
        
        # Be respectful to server (only delay if we actually fetched from web, not from cache)
        if not was_cached and i < total_cards:
            time.sleep(2)
    
    if dry_run:
        logger.info("\n=== DRY RUN MODE ===")
        logger.info(f"Would update {len(card_codes)} card codes:")
        for card_id, card_code in card_codes.items():
            card_name = missing_codes[card_id]['card_name']
            logger.info(f"  Card {card_id} ({card_name}): {card_code}")
        return
    
    # Update all deck files
    updated_files = set()
    for card_id, card_code in card_codes.items():
        deck_files = missing_codes[card_id]['deck_files']
        
        for deck_file in deck_files:
            try:
                with open(deck_file, 'r', encoding='utf-8') as f:
                    deck_data = json.load(f)
                
                # Update the card_code
                modified = False
                for card in deck_data.get('cards', []):
                    if card.get('card_id') == card_id:
                        if not card.get('card_code') or card.get('card_code').strip() == '':
                            card['card_code'] = card_code
                            modified = True
                
                if modified:
                    with open(deck_file, 'w', encoding='utf-8') as f:
                        json.dump(deck_data, f, ensure_ascii=False, indent=2)
                    updated_files.add(deck_file)
            
            except Exception as e:
                logger.error(f"Error updating {deck_file}: {e}")
                continue
    
    logger.info(f"\n✓ Updated {len(card_codes)} cards across {len(updated_files)} deck files")

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Fetch missing card codes from Pokemon card website')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be updated without modifying files')
    parser.add_argument('--event-data-dir', default='event_data', help='Path to event_data directory')
    
    args = parser.parse_args()
    
    print("=" * 80)
    print("FETCH CARD CODES")
    print("=" * 80)
    print()
    
    # Find cards with missing codes
    missing_codes = find_cards_with_missing_codes(args.event_data_dir)
    
    if not missing_codes:
        print("✓ All cards have card codes!")
        return
    
    print(f"\nFound {len(missing_codes)} cards with missing card codes:")
    for card_id, card_info in list(missing_codes.items())[:10]:
        try:
            print(f"  - Card {card_id}: {card_info['card_name']}")
            print(f"    Found in {len(card_info['deck_files'])} deck(s)")
        except UnicodeEncodeError:
            print(f"  - Card {card_id}: [name contains special characters]")
            print(f"    Found in {len(card_info['deck_files'])} deck(s)")
    
    if len(missing_codes) > 10:
        print(f"  ... and {len(missing_codes) - 10} more")
    
    print()
    
    # Ask for confirmation
    if not args.dry_run:
        response = input("Fetch card codes for these cards? (y/n): ")
        if response.lower() != 'y':
            print("Cancelled.")
            return
    
    # Update codes
    update_card_codes(missing_codes, dry_run=args.dry_run)
    
    print()
    print("=" * 80)
    print("DONE")
    print("=" * 80)

if __name__ == "__main__":
    main()
