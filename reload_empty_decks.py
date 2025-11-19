#!/usr/bin/env python3
"""
Find and reload empty or incomplete deck JSON files
"""
import os
import json
import glob
import time
from event_scraper_enhanced import EventDeckScraper
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def find_empty_decks(event_data_dir="event_data"):
    """Find deck files that are empty or incomplete"""
    empty_decks = []
    deck_files = glob.glob(f"{event_data_dir}/event_*/deck_*.json")
    
    logger.info(f"Scanning {len(deck_files)} deck files...")
    
    for deck_file in deck_files:
        try:
            # Check file size first (very fast)
            file_size = os.path.getsize(deck_file)
            if file_size < 100:  # Less than 100 bytes is likely empty/minimal
                empty_decks.append({
                    'file': deck_file,
                    'reason': f'File too small ({file_size} bytes)',
                    'deck_id': None
                })
                continue
            
            # Check JSON content
            with open(deck_file, 'r', encoding='utf-8') as f:
                deck_data = json.load(f)
            
            # Check if deck has cards
            cards = deck_data.get('cards', [])
            deck_id = deck_data.get('deck_id', '')
            
            if not cards or len(cards) == 0:
                empty_decks.append({
                    'file': deck_file,
                    'reason': 'No cards',
                    'deck_id': deck_id
                })
            elif len(cards) < 10:  # Suspiciously few cards (decks should have 60)
                empty_decks.append({
                    'file': deck_file,
                    'reason': f'Only {len(cards)} cards (expected ~60)',
                    'deck_id': deck_id
                })
        
        except json.JSONDecodeError:
            # Extract deck_id from filename
            deck_id = deck_file.split('deck_')[-1].replace('.json', '')
            empty_decks.append({
                'file': deck_file,
                'reason': 'Invalid JSON',
                'deck_id': deck_id
            })
        except Exception as e:
            logger.error(f"Error checking {deck_file}: {e}")
            continue
    
    return empty_decks

def reload_deck(scraper, deck_info, dry_run=False):
    """Reload a single deck"""
    deck_file = deck_info['file']
    deck_id = deck_info['deck_id']
    
    # Extract deck_id from filename if not in data
    if not deck_id:
        # Format: deck_1st_deckID.json or deck_deckID.json
        filename = os.path.basename(deck_file)
        if '_' in filename:
            # Try to extract from filename
            parts = filename.replace('deck_', '').replace('.json', '').split('_')
            if len(parts) >= 2:
                deck_id = parts[-1]  # Last part is usually the deck_id
            else:
                deck_id = parts[0]
    
    if not deck_id:
        logger.error(f"Cannot extract deck_id from {deck_file}")
        return False
    
    logger.info(f"Reloading deck {deck_id} from {deck_file}")
    logger.info(f"  Reason: {deck_info['reason']}")
    
    if dry_run:
        logger.info(f"  [DRY RUN] Would reload deck {deck_id}")
        return True
    
    try:
        # Scrape fresh data
        deck_data = scraper.scrape_deck_by_id(deck_id)
        
        if not deck_data or not deck_data.get('cards'):
            logger.warning(f"  Failed to fetch deck data for {deck_id}")
            return False
        
        # Backup old file
        backup_file = f"{deck_file}.backup"
        if os.path.exists(deck_file):
            import shutil
            shutil.copy2(deck_file, backup_file)
        
        # Save new data
        with open(deck_file, 'w', encoding='utf-8') as f:
            json.dump(deck_data, f, ensure_ascii=False, indent=2)
        
        # Remove backup if successful
        if os.path.exists(backup_file):
            os.remove(backup_file)
        
        logger.info(f"  ✓ Reloaded {len(deck_data['cards'])} cards")
        return True
    
    except Exception as e:
        logger.error(f"  ✗ Error reloading deck {deck_id}: {e}")
        # Restore backup if exists
        backup_file = f"{deck_file}.backup"
        if os.path.exists(backup_file):
            import shutil
            shutil.copy2(backup_file, deck_file)
            os.remove(backup_file)
        return False

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Find and reload empty/incomplete deck files')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be reloaded without actually reloading')
    parser.add_argument('--event-data-dir', default='event_data', help='Path to event_data directory')
    parser.add_argument('--max-reload', type=int, default=100, help='Maximum number of decks to reload')
    
    args = parser.parse_args()
    
    print("=" * 80)
    print("FIND AND RELOAD EMPTY DECKS")
    print("=" * 80)
    print()
    
    # Find empty decks
    empty_decks = find_empty_decks(args.event_data_dir)
    
    if not empty_decks:
        print("✓ All decks are complete!")
        return
    
    print(f"Found {len(empty_decks)} empty/incomplete decks:")
    for i, deck_info in enumerate(empty_decks[:20], 1):
        deck_id = deck_info['deck_id'] or 'unknown'
        print(f"  {i}. {os.path.basename(deck_info['file'])}")
        print(f"     Deck ID: {deck_id}")
        print(f"     Reason: {deck_info['reason']}")
    
    if len(empty_decks) > 20:
        print(f"  ... and {len(empty_decks) - 20} more")
    
    print()
    
    # Ask for confirmation
    if not args.dry_run:
        response = input(f"Reload up to {min(args.max_reload, len(empty_decks))} decks? (y/n): ")
        if response.lower() != 'y':
            print("Cancelled.")
            return
    
    # Reload decks
    scraper = EventDeckScraper(output_dir=args.event_data_dir)
    
    successful = 0
    failed = 0
    
    print()
    print("=" * 80)
    print("RELOADING DECKS")
    print("=" * 80)
    
    for i, deck_info in enumerate(empty_decks[:args.max_reload], 1):
        print(f"\n[{i}/{min(args.max_reload, len(empty_decks))}]")
        
        if reload_deck(scraper, deck_info, dry_run=args.dry_run):
            successful += 1
        else:
            failed += 1
        
        # Be respectful to server
        if not args.dry_run and i < min(args.max_reload, len(empty_decks)):
            time.sleep(1)
    
    print()
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Processed: {successful + failed} decks")
    print(f"Successful: {successful}")
    print(f"Failed: {failed}")
    
    if args.dry_run:
        print("\n(This was a dry run - no changes were made)")

if __name__ == "__main__":
    main()
