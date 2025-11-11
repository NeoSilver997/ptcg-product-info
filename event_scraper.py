#!/usr/bin/env python3
"""
PTCG Event Deck List Scraper
Scrapes deck list information from Pokemon TCG Japan event results
"""

import csv
import logging
from datetime import datetime
from typing import List, Dict
import requests
from bs4 import BeautifulSoup
import time
import re

# Import configuration
try:
    from config import (
        OUTPUT_ENCODING, REQUEST_TIMEOUT, 
        DELAY_BETWEEN_REQUESTS, USER_AGENT, LOG_LEVEL
    )
except ImportError:
    # Default configuration if config.py doesn't exist
    OUTPUT_ENCODING = "utf-8"
    REQUEST_TIMEOUT = 30
    DELAY_BETWEEN_REQUESTS = 2
    USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    LOG_LEVEL = "INFO"

# Configure logging
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class JapanEventDeckListScraper:
    """Scraper for https://players.pokemon-card.com/event/result/list"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': USER_AGENT
        })
        self.timeout = REQUEST_TIMEOUT
        self.base_url = "https://players.pokemon-card.com"
        self.events_url = f"{self.base_url}/event/result/list"
    
    def scrape_event_list(self) -> List[Dict]:
        """Scrape the list of events"""
        logger.info(f"Scraping event list from {self.events_url}")
        events = []
        
        try:
            response = self.session.get(self.events_url, timeout=self.timeout)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Find event items
            # The structure will vary, looking for common patterns
            event_items = soup.find_all(['div', 'li', 'article'], class_=lambda x: x and ('event' in str(x).lower() or 'result' in str(x).lower()))
            
            if not event_items:
                # Try alternative selectors
                event_items = soup.find_all('a', href=lambda x: x and '/event/result/' in str(x))
            
            logger.info(f"Found {len(event_items)} potential event items")
            
            for item in event_items:
                try:
                    event_data = self._parse_event_item(item)
                    if event_data:
                        events.append(event_data)
                except Exception as e:
                    logger.warning(f"Error parsing event item: {e}")
                    continue
            
        except Exception as e:
            logger.error(f"Error scraping event list: {e}")
        
        return events
    
    def _parse_event_item(self, item) -> Dict:
        """Parse a single event item"""
        event = {
            'event_name': '',
            'event_date': '',
            'event_location': '',
            'event_url': '',
            'event_type': ''
        }
        
        # Try to find event name
        name_elem = item.find(['h2', 'h3', 'h4', 'span', 'div'], class_=lambda x: x and ('title' in str(x).lower() or 'name' in str(x).lower()))
        if not name_elem:
            name_elem = item if item.name in ['a', 'span'] else item.find('a')
        if name_elem:
            event['event_name'] = name_elem.get_text(strip=True)
        
        # Try to find link
        link_elem = item if item.name == 'a' else item.find('a', href=True)
        if link_elem and link_elem.has_attr('href'):
            href = link_elem['href']
            if href.startswith('http'):
                event['event_url'] = href
            else:
                event['event_url'] = self.base_url + href
        
        # Try to find date
        date_elem = item.find(['span', 'div', 'p', 'time'], class_=lambda x: x and 'date' in str(x).lower())
        if not date_elem:
            date_elem = item.find('time')
        if date_elem:
            event['event_date'] = date_elem.get_text(strip=True)
        
        # Try to find location
        location_elem = item.find(['span', 'div', 'p'], class_=lambda x: x and 'location' in str(x).lower())
        if location_elem:
            event['event_location'] = location_elem.get_text(strip=True)
        
        return event if event['event_name'] or event['event_url'] else None
    
    def scrape_deck_list_from_event(self, event_url: str) -> List[Dict]:
        """Scrape deck lists from a specific event page"""
        logger.info(f"Scraping deck lists from {event_url}")
        deck_lists = []
        
        try:
            response = self.session.get(event_url, timeout=self.timeout)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Find deck list items
            deck_items = soup.find_all(['div', 'li', 'article'], class_=lambda x: x and ('deck' in str(x).lower() or 'player' in str(x).lower()))
            
            logger.info(f"Found {len(deck_items)} potential deck items")
            
            for item in deck_items:
                try:
                    deck_data = self._parse_deck_item(item, event_url)
                    if deck_data:
                        deck_lists.append(deck_data)
                except Exception as e:
                    logger.warning(f"Error parsing deck item: {e}")
                    continue
            
        except Exception as e:
            logger.error(f"Error scraping deck lists from {event_url}: {e}")
        
        return deck_lists
    
    def _parse_deck_item(self, item, event_url: str) -> Dict:
        """Parse a single deck item"""
        deck = {
            'event_url': event_url,
            'player_name': '',
            'player_rank': '',
            'deck_type': '',
            'deck_url': '',
            'deck_code': ''
        }
        
        # Try to find player name
        player_elem = item.find(['span', 'div', 'p', 'h3', 'h4'], class_=lambda x: x and ('player' in str(x).lower() or 'name' in str(x).lower()))
        if player_elem:
            deck['player_name'] = player_elem.get_text(strip=True)
        
        # Try to find rank/position
        rank_elem = item.find(['span', 'div', 'p'], class_=lambda x: x and ('rank' in str(x).lower() or 'position' in str(x).lower()))
        if rank_elem:
            deck['player_rank'] = rank_elem.get_text(strip=True)
        
        # Try to find deck type
        type_elem = item.find(['span', 'div', 'p'], class_=lambda x: x and ('deck' in str(x).lower() or 'type' in str(x).lower()))
        if type_elem:
            deck['deck_type'] = type_elem.get_text(strip=True)
        
        # Try to find deck URL
        link_elem = item.find('a', href=lambda x: x and ('deck' in str(x).lower() or 'detail' in str(x).lower()))
        if link_elem and link_elem.has_attr('href'):
            href = link_elem['href']
            if href.startswith('http'):
                deck['deck_url'] = href
            else:
                deck['deck_url'] = self.base_url + href
        
        return deck if deck['player_name'] or deck['deck_url'] else None
    
    def scrape_detailed_deck_list(self, deck_url: str) -> Dict:
        """Scrape detailed card list from a deck page"""
        logger.info(f"Scraping detailed deck from {deck_url}")
        deck_details = {
            'deck_url': deck_url,
            'cards': []
        }
        
        try:
            response = self.session.get(deck_url, timeout=self.timeout)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Find card items
            card_items = soup.find_all(['div', 'li', 'tr'], class_=lambda x: x and 'card' in str(x).lower())
            
            for item in card_items:
                try:
                    card_data = self._parse_card_item(item)
                    if card_data:
                        deck_details['cards'].append(card_data)
                except Exception as e:
                    logger.warning(f"Error parsing card item: {e}")
                    continue
            
        except Exception as e:
            logger.error(f"Error scraping detailed deck from {deck_url}: {e}")
        
        return deck_details
    
    def _parse_card_item(self, item) -> Dict:
        """Parse a single card item"""
        card = {
            'card_name': '',
            'card_count': '1',
            'card_number': '',
            'set_name': ''
        }
        
        # Try to find card name
        name_elem = item.find(['span', 'div', 'p', 'td'], class_=lambda x: x and ('name' in str(x).lower() or 'title' in str(x).lower()))
        if not name_elem:
            name_elem = item.find(['span', 'div', 'p', 'td'])
        if name_elem:
            card['card_name'] = name_elem.get_text(strip=True)
        
        # Try to find card count
        count_elem = item.find(['span', 'div', 'p', 'td'], class_=lambda x: x and ('count' in str(x).lower() or 'quantity' in str(x).lower()))
        if count_elem:
            count_text = count_elem.get_text(strip=True)
            # Extract number from text
            count_match = re.search(r'\d+', count_text)
            if count_match:
                card['card_count'] = count_match.group()
        
        # Try to find card number
        number_elem = item.find(['span', 'div', 'p', 'td'], class_=lambda x: x and ('number' in str(x).lower() or 'no' in str(x).lower()))
        if number_elem:
            card['card_number'] = number_elem.get_text(strip=True)
        
        # Try to find set name
        set_elem = item.find(['span', 'div', 'p', 'td'], class_=lambda x: x and ('set' in str(x).lower() or 'expansion' in str(x).lower()))
        if set_elem:
            card['set_name'] = set_elem.get_text(strip=True)
        
        return card if card['card_name'] else None


def export_events_to_csv(events: List[Dict], filename: str = None):
    """Export events to CSV file"""
    if not filename:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"ptcg_events_{timestamp}.csv"
    
    if not events:
        logger.warning("No events to export")
        return
    
    fieldnames = ['event_name', 'event_date', 'event_location', 'event_url', 'event_type']
    
    try:
        with open(filename, 'w', newline='', encoding=OUTPUT_ENCODING) as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(events)
        
        logger.info(f"Successfully exported {len(events)} events to {filename}")
    except Exception as e:
        logger.error(f"Error exporting events to CSV: {e}")


def export_deck_lists_to_csv(deck_lists: List[Dict], filename: str = None):
    """Export deck lists to CSV file"""
    if not filename:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"ptcg_deck_lists_{timestamp}.csv"
    
    if not deck_lists:
        logger.warning("No deck lists to export")
        return
    
    fieldnames = ['event_url', 'player_name', 'player_rank', 'deck_type', 'deck_url', 'deck_code']
    
    try:
        with open(filename, 'w', newline='', encoding=OUTPUT_ENCODING) as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(deck_lists)
        
        logger.info(f"Successfully exported {len(deck_lists)} deck lists to {filename}")
    except Exception as e:
        logger.error(f"Error exporting deck lists to CSV: {e}")


def export_detailed_decks_to_csv(detailed_decks: List[Dict], filename: str = None):
    """Export detailed deck card lists to CSV file"""
    if not filename:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"ptcg_deck_cards_{timestamp}.csv"
    
    if not detailed_decks:
        logger.warning("No detailed decks to export")
        return
    
    # Flatten the nested structure
    flat_data = []
    for deck in detailed_decks:
        for card in deck.get('cards', []):
            flat_data.append({
                'deck_url': deck['deck_url'],
                'card_name': card['card_name'],
                'card_count': card['card_count'],
                'card_number': card['card_number'],
                'set_name': card['set_name']
            })
    
    if not flat_data:
        logger.warning("No cards to export")
        return
    
    fieldnames = ['deck_url', 'card_name', 'card_count', 'card_number', 'set_name']
    
    try:
        with open(filename, 'w', newline='', encoding=OUTPUT_ENCODING) as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(flat_data)
        
        logger.info(f"Successfully exported {len(flat_data)} cards from {len(detailed_decks)} decks to {filename}")
    except Exception as e:
        logger.error(f"Error exporting detailed decks to CSV: {e}")


def main():
    """Main function to orchestrate event and deck list scraping"""
    logger.info("Starting PTCG Event Deck List Scraper")
    
    scraper = JapanEventDeckListScraper()
    
    # Step 1: Scrape event list
    events = scraper.scrape_event_list()
    logger.info(f"Scraped {len(events)} events")
    
    if events:
        export_events_to_csv(events)
        
        # Step 2: Scrape deck lists from each event (limited to first 5 for testing)
        all_deck_lists = []
        for i, event in enumerate(events[:5]):
            if event.get('event_url'):
                logger.info(f"Processing event {i+1}/{min(5, len(events))}: {event['event_name']}")
                deck_lists = scraper.scrape_deck_list_from_event(event['event_url'])
                all_deck_lists.extend(deck_lists)
                time.sleep(DELAY_BETWEEN_REQUESTS)
        
        logger.info(f"Scraped {len(all_deck_lists)} deck lists")
        
        if all_deck_lists:
            export_deck_lists_to_csv(all_deck_lists)
            
            # Step 3: Optionally scrape detailed deck lists (limited to first 3 for testing)
            detailed_decks = []
            for i, deck in enumerate(all_deck_lists[:3]):
                if deck.get('deck_url'):
                    logger.info(f"Processing deck {i+1}/{min(3, len(all_deck_lists))}")
                    detailed_deck = scraper.scrape_detailed_deck_list(deck['deck_url'])
                    detailed_decks.append(detailed_deck)
                    time.sleep(DELAY_BETWEEN_REQUESTS)
            
            if detailed_decks:
                export_detailed_decks_to_csv(detailed_decks)
    
    logger.info("Event deck list scraping completed!")


if __name__ == "__main__":
    main()
