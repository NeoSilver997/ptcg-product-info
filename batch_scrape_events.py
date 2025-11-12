#!/usr/bin/env python3
"""
Batch scrape multiple events
"""
import time
import re
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
from event_scraper_enhanced import EventDeckScraper
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def get_event_ids_from_list(max_events=20):
    """Get real event IDs from the event list page with pagination support"""
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    driver = webdriver.Chrome(options=chrome_options)
    
    event_ids = []
    offset = 0
    page = 1
    
    while len(event_ids) < max_events:
        url = f'https://players.pokemon-card.com/event/result/list?offset={offset}'
        print(f"Fetching event list page {page} (offset={offset})...")
        driver.get(url)
        time.sleep(2)  # Reduced from 5 to 2 seconds
        
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        
        # Find all event links
        event_links = soup.find_all('a', href=lambda x: x and '/event/detail/' in str(x))
        
        # Track how many new IDs we found on this page
        initial_count = len(event_ids)
        
        for link in event_links:
            href = link.get('href', '')
            match = re.search(r'/event/detail/(\d+)', href)
            if match:
                event_id = match.group(1)
                if event_id not in event_ids:
                    event_ids.append(event_id)
                    if len(event_ids) >= max_events:
                        break
        
        # If no new events found, we've reached the end
        if len(event_ids) == initial_count:
            print(f"No more events found. Total: {len(event_ids)} events")
            break
        
        print(f"  → Found {len(event_ids) - initial_count} new events (total: {len(event_ids)})")
        
        # Stop if we have enough events
        if len(event_ids) >= max_events:
            break
        
        # Move to next page (20 events per page)
        offset += 20
        page += 1
        time.sleep(1)  # Reduced from 2 to 1 second
    
    driver.quit()
    print(f"Total event IDs collected: {len(event_ids)}")
    return event_ids

def main():
    scraper = EventDeckScraper(output_dir="event_data")
    
    # Get real event IDs from the list page (fetch 100 to get next 50 after first 50)
    events_to_scrape = get_event_ids_from_list(max_events=100)  # Fetch 100 event IDs
    
    successful_events = []
    
    print("=" * 80)
    print("BATCH EVENT SCRAPING")
    print("=" * 80)
    print(f"Found {len(events_to_scrape)} event IDs from list page")
    print(f"Will scrape up to 50 NEW events (skipping already downloaded)")
    print()
    
    for idx, event_id in enumerate(events_to_scrape, 1):
        event_url = f"https://players.pokemon-card.com/event/detail/{event_id}/result"
        
        try:
            print(f"\n[{idx}/{len(events_to_scrape)}] Checking event {event_id}...")
            
            # Check if event already exists
            import os
            import glob
            existing_folders = glob.glob(f"{scraper.output_dir}/event_{event_id}_*")
            
            if existing_folders:
                event_folder = existing_folders[0]
                
                # Check if decks are already downloaded
                deck_files = glob.glob(f"{event_folder}/deck_*.json")
                event_info_file = os.path.join(event_folder, "event_info.json")
                
                # If event info exists, check if we need to download decks
                if os.path.exists(event_info_file):
                    import json
                    with open(event_info_file, 'r', encoding='utf-8') as f:
                        event_data = json.load(f)
                    
                    expected_decks = len(event_data.get('results', []))
                    actual_decks = len(deck_files)
                    
                    if actual_decks >= expected_decks and actual_decks > 0:
                        print(f"⊙ Event {event_id}: Already downloaded with {actual_decks} decks, skipping...")
                        # Don't count already downloaded events toward the 50 target
                        continue
                    else:
                        print(f"⊙ Event {event_id}: Found but missing decks ({actual_decks}/{expected_decks}), re-downloading decks...")
                        # Will download decks below
                else:
                    print(f"  → Event {event_id}: Folder exists but no event_info.json, re-scraping...")
            else:
                print(f"  → Scraping event {event_id}...")
                event_data = scraper.scrape_event(event_url)
                
                # Check if event has results
                if not event_data['results']:
                    print(f"✗ Event {event_id}: No results found (might not exist)")
                    continue
                
                print(f"✓ Event {event_id}: {len(event_data['results'])} results")
                print(f"  Date: {event_data['event_date']}")
                print(f"  Host: {event_data['event_host'][:50]}..." if len(event_data['event_host']) > 50 else f"  Host: {event_data['event_host']}")
                
                # Save event data
                event_folder = scraper.save_event_data(event_data)
            
            # Load event data if not already loaded
            if 'event_data' not in locals() or not event_data:
                event_info_file = os.path.join(event_folder, "event_info.json")
                with open(event_info_file, 'r', encoding='utf-8') as f:
                    event_data = json.load(f)
            
            # Scrape decks with ranking in filename
            print(f"  → Scraping {len(event_data['results'])} decks...")
            for result in event_data['results']:
                deck_id = result.get('deck_id')
                if not deck_id:
                    continue
                
                # Format rank for filename (1位 -> 1st, 2位 -> 2nd, etc.)
                rank = result.get('rank', '').replace('位', '')
                rank_suffix = 'st' if rank == '1' else 'nd' if rank == '2' else 'rd' if rank == '3' else 'th'
                rank_name = f"{rank}{rank_suffix}"
                
                # Check if this deck already exists
                deck_filename = f"deck_{rank_name}_{deck_id}.json"
                deck_path = os.path.join(event_folder, deck_filename)
                
                if os.path.exists(deck_path):
                    print(f"    ⊙ {rank_name}: {deck_id} (already exists)")
                    continue
                
                try:
                    deck_data = scraper.scrape_deck_by_id(deck_id)
                    
                    # Save with ranking in filename
                    with open(deck_path, 'w', encoding='utf-8') as f:
                        json.dump(deck_data, f, ensure_ascii=False, indent=2)
                    
                    print(f"    ✓ {rank_name}: {deck_id} ({len(deck_data['cards'])} cards)")
                    
                    # Small delay between decks
                    time.sleep(2)
                except Exception as e:
                    print(f"    ✗ {rank_name}: {deck_id} - Error: {e}")
                    continue
            
            successful_events.append(event_id)
            print(f"✓ Downloaded event {event_id} ({len(successful_events)}/50 new events)")
            
            # Stop after 50 NEW successful events
            if len(successful_events) >= 50:
                print(f"\n✓ Reached target of 50 NEW events!")
                break
            
            # Be respectful to server
            time.sleep(2)
            
        except Exception as e:
            print(f"✗ Event {event_id}: Error - {e}")
            continue
    
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Successfully scraped {len(successful_events)} events:")
    for event_id in successful_events:
        print(f"  - Event {event_id}")
    print()

if __name__ == "__main__":
    main()
