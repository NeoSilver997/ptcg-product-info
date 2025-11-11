#!/usr/bin/env python3
"""
Test script for PTCG event scraper with mock data
Demonstrates functionality without requiring internet access
"""

import csv
from datetime import datetime
from event_scraper import export_events_to_csv, export_deck_lists_to_csv, export_detailed_decks_to_csv
import os

def generate_mock_events():
    """Generate mock event data for testing"""
    mock_events = [
        {
            'event_name': 'Champions League 2024 Fukuoka',
            'event_date': '2024-01-20',
            'event_location': 'Fukuoka, Japan',
            'event_url': 'https://players.pokemon-card.com/event/result/detail/123456',
            'event_type': 'Champions League'
        },
        {
            'event_name': 'City League Tokyo Autumn 2023',
            'event_date': '2023-11-15',
            'event_location': 'Tokyo, Japan',
            'event_url': 'https://players.pokemon-card.com/event/result/detail/123457',
            'event_type': 'City League'
        },
        {
            'event_name': 'Battle Carnival Osaka',
            'event_date': '2023-12-10',
            'event_location': 'Osaka, Japan',
            'event_url': 'https://players.pokemon-card.com/event/result/detail/123458',
            'event_type': 'Battle Carnival'
        }
    ]
    return mock_events


def generate_mock_deck_lists():
    """Generate mock deck list data for testing"""
    mock_deck_lists = [
        {
            'event_url': 'https://players.pokemon-card.com/event/result/detail/123456',
            'player_name': '山田太郎',
            'player_rank': '1st',
            'deck_type': 'Mew VMAX',
            'deck_url': 'https://players.pokemon-card.com/deck/detail/D001',
            'deck_code': 'fF5kVk-g9PzMK-VfkFkd'
        },
        {
            'event_url': 'https://players.pokemon-card.com/event/result/detail/123456',
            'player_name': '佐藤花子',
            'player_rank': '2nd',
            'deck_type': 'Lugia VSTAR',
            'deck_url': 'https://players.pokemon-card.com/deck/detail/D002',
            'deck_code': 'kkFfV5-QniLHn-vFfFkF'
        },
        {
            'event_url': 'https://players.pokemon-card.com/event/result/detail/123457',
            'player_name': '鈴木一郎',
            'player_rank': '1st',
            'deck_type': 'Arceus VSTAR / Giratina VSTAR',
            'deck_url': 'https://players.pokemon-card.com/deck/detail/D003',
            'deck_code': 'ppyXyy-gZgGHn-yyXyyM'
        }
    ]
    return mock_deck_lists


def generate_mock_detailed_decks():
    """Generate mock detailed deck card data for testing"""
    mock_detailed_decks = [
        {
            'deck_url': 'https://players.pokemon-card.com/deck/detail/D001',
            'cards': [
                {'card_name': 'Mew VMAX', 'card_count': '3', 'card_number': '114/172', 'set_name': 'Fusion Arts'},
                {'card_name': 'Mew V', 'card_count': '3', 'card_number': '113/172', 'set_name': 'Fusion Arts'},
                {'card_name': 'Genesect V', 'card_count': '3', 'card_number': '185/172', 'set_name': 'Fusion Arts'},
                {'card_name': 'Quick Ball', 'card_count': '4', 'card_number': '179/190', 'set_name': 'Sword & Shield'},
                {'card_name': 'Ultra Ball', 'card_count': '4', 'card_number': '186/195', 'set_name': 'Sword & Shield'},
                {'card_name': 'Professor\'s Research', 'card_count': '4', 'card_number': '178/190', 'set_name': 'Sword & Shield'},
                {'card_name': 'Boss\'s Orders', 'card_count': '2', 'card_number': '154/172', 'set_name': 'Brilliant Stars'},
                {'card_name': 'Elesa\'s Sparkle', 'card_count': '2', 'card_number': '147/172', 'set_name': 'Fusion Arts'},
                {'card_name': 'Psychic Energy', 'card_count': '8', 'card_number': '232/190', 'set_name': 'Sword & Shield'}
            ]
        },
        {
            'deck_url': 'https://players.pokemon-card.com/deck/detail/D002',
            'cards': [
                {'card_name': 'Lugia VSTAR', 'card_count': '2', 'card_number': '139/195', 'set_name': 'Silver Tempest'},
                {'card_name': 'Lugia V', 'card_count': '2', 'card_number': '138/195', 'set_name': 'Silver Tempest'},
                {'card_name': 'Archeops', 'card_count': '2', 'card_number': '147/195', 'set_name': 'Silver Tempest'},
                {'card_name': 'Quick Ball', 'card_count': '4', 'card_number': '179/190', 'set_name': 'Sword & Shield'},
                {'card_name': 'Ultra Ball', 'card_count': '4', 'card_number': '186/195', 'set_name': 'Sword & Shield'},
                {'card_name': 'Rare Candy', 'card_count': '3', 'card_number': '180/195', 'set_name': 'Silver Tempest'},
                {'card_name': 'Professor\'s Research', 'card_count': '3', 'card_number': '178/190', 'set_name': 'Sword & Shield'},
                {'card_name': 'Colorless Energy', 'card_count': '4', 'card_number': '233/190', 'set_name': 'Sword & Shield'},
                {'card_name': 'Aurora Energy', 'card_count': '4', 'card_number': '186/195', 'set_name': 'Silver Tempest'}
            ]
        }
    ]
    return mock_detailed_decks


def test_event_export():
    """Test event export functionality"""
    print("Testing PTCG Event Deck List Scraper with mock data\n")
    
    # Test events export
    events = generate_mock_events()
    print(f"Generated {len(events)} mock events")
    
    test_filename = "test_ptcg_events.csv"
    export_events_to_csv(events, test_filename)
    
    if os.path.exists(test_filename):
        print(f"\n✓ CSV file '{test_filename}' created successfully")
        print(f"\nEvent CSV Contents:")
        print("-" * 80)
        with open(test_filename, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for i, row in enumerate(reader, 1):
                print(f"\nEvent {i}:")
                for key, value in row.items():
                    if value:
                        print(f"  {key}: {value}")
        
        os.remove(test_filename)
        print(f"\n✓ Test file cleaned up")
    
    # Test deck lists export
    print("\n" + "=" * 80)
    deck_lists = generate_mock_deck_lists()
    print(f"\nGenerated {len(deck_lists)} mock deck lists")
    
    test_filename = "test_ptcg_deck_lists.csv"
    export_deck_lists_to_csv(deck_lists, test_filename)
    
    if os.path.exists(test_filename):
        print(f"\n✓ CSV file '{test_filename}' created successfully")
        print(f"\nDeck List CSV Contents:")
        print("-" * 80)
        with open(test_filename, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for i, row in enumerate(reader, 1):
                print(f"\nDeck {i}:")
                for key, value in row.items():
                    if value:
                        print(f"  {key}: {value}")
        
        os.remove(test_filename)
        print(f"\n✓ Test file cleaned up")
    
    # Test detailed decks export
    print("\n" + "=" * 80)
    detailed_decks = generate_mock_detailed_decks()
    print(f"\nGenerated {len(detailed_decks)} mock detailed decks")
    
    test_filename = "test_ptcg_deck_cards.csv"
    export_detailed_decks_to_csv(detailed_decks, test_filename)
    
    if os.path.exists(test_filename):
        print(f"\n✓ CSV file '{test_filename}' created successfully")
        print(f"\nDetailed Deck Cards CSV Contents (first 10 cards):")
        print("-" * 80)
        with open(test_filename, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for i, row in enumerate(reader, 1):
                if i > 10:
                    print(f"\n... and more cards")
                    break
                print(f"\nCard {i}:")
                for key, value in row.items():
                    if value:
                        print(f"  {key}: {value}")
        
        os.remove(test_filename)
        print(f"\n✓ Test file cleaned up")
    
    print("\n" + "-" * 80)
    print(f"\n✓ All tests completed successfully!")


if __name__ == "__main__":
    test_event_export()
