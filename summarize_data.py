#!/usr/bin/env python3
"""
Summarize deck and user data from downloaded events
"""
import os
import json
import glob
from collections import defaultdict, Counter

def load_all_events(event_data_dir="event_data"):
    """Load all event data from the event_data directory"""
    events = []
    event_folders = glob.glob(f"{event_data_dir}/event_*")
    
    for folder in event_folders:
        event_info_file = os.path.join(folder, "event_info.json")
        if os.path.exists(event_info_file):
            with open(event_info_file, 'r', encoding='utf-8') as f:
                event_data = json.load(f)
                event_data['folder'] = folder
                events.append(event_data)
    
    return events

def load_all_decks(event_data_dir="event_data"):
    """Load all deck data from all events"""
    decks = []
    deck_files = glob.glob(f"{event_data_dir}/event_*/deck_*.json")
    
    for deck_file in deck_files:
        with open(deck_file, 'r', encoding='utf-8') as f:
            deck_data = json.load(f)
            # Extract event_id from path
            folder = os.path.dirname(deck_file)
            event_id = folder.split('event_')[1].split('_')[0] if 'event_' in folder else ''
            deck_data['event_id'] = event_id
            deck_data['deck_file'] = deck_file
            decks.append(deck_data)
    
    return decks

def summarize_events(events):
    """Summarize event statistics"""
    print("=" * 80)
    print("EVENT SUMMARY")
    print("=" * 80)
    print(f"Total Events: {len(events)}")
    print()
    
    # Count by date
    dates = [e.get('event_date', 'Unknown') for e in events]
    date_counts = Counter(dates)
    print(f"Events by Date:")
    for date, count in sorted(date_counts.items(), reverse=True)[:10]:
        print(f"  {date}: {count} event(s)")
    print()
    
    # Count by host
    hosts = [e.get('event_host', 'Unknown')[:50] for e in events]
    host_counts = Counter(hosts)
    print(f"Top 10 Event Hosts:")
    for host, count in host_counts.most_common(10):
        print(f"  {host}...: {count} event(s)")
    print()
    
    # Total participants
    total_participants = sum(len(e.get('results', [])) for e in events)
    print(f"Total Participants: {total_participants}")
    print(f"Average Participants per Event: {total_participants / len(events):.1f}")
    print()

def summarize_players(events):
    """Summarize player statistics"""
    print("=" * 80)
    print("PLAYER SUMMARY")
    print("=" * 80)
    
    # Collect all players
    player_stats = defaultdict(lambda: {
        'name': '',
        'area': '',
        'events': [],
        'ranks': [],
        'deck_ids': []
    })
    
    for event in events:
        event_id = event.get('event_id', '')
        for result in event.get('results', []):
            player_id = result.get('player_id', '')
            if player_id:
                player_stats[player_id]['name'] = result.get('player_name', '')
                player_stats[player_id]['area'] = result.get('player_area', '')
                player_stats[player_id]['events'].append(event_id)
                player_stats[player_id]['ranks'].append(result.get('rank', ''))
                player_stats[player_id]['deck_ids'].append(result.get('deck_id', ''))
    
    print(f"Total Unique Players: {len(player_stats)}")
    print()
    
    # Top players by number of events
    player_event_counts = [(pid, len(pdata['events']), pdata['name'], pdata['area']) 
                           for pid, pdata in player_stats.items()]
    player_event_counts.sort(key=lambda x: x[1], reverse=True)
    
    print("Top 20 Players by Event Count:")
    print(f"{'Rank':<6} {'Player ID':<15} {'Name':<25} {'Area':<15} {'Events':<8}")
    print("-" * 80)
    for i, (pid, count, name, area) in enumerate(player_event_counts[:20], 1):
        name_display = name[:24] if len(name) > 24 else name
        area_display = area[:14] if len(area) > 14 else area
        print(f"{i:<6} {pid:<15} {name_display:<25} {area_display:<15} {count:<8}")
    print()
    
    # Players with 1st place finishes
    first_place_players = []
    for pid, pdata in player_stats.items():
        first_places = sum(1 for rank in pdata['ranks'] if rank == '1位')
        if first_places > 0:
            first_place_players.append((pid, first_places, pdata['name'], pdata['area']))
    
    first_place_players.sort(key=lambda x: x[1], reverse=True)
    
    print(f"Players with 1st Place Finishes: {len(first_place_players)}")
    print()
    print("Top 20 Players by 1st Place Count:")
    print(f"{'Rank':<6} {'Player ID':<15} {'Name':<25} {'Area':<15} {'1st Places':<12}")
    print("-" * 80)
    for i, (pid, count, name, area) in enumerate(first_place_players[:20], 1):
        name_display = name[:24] if len(name) > 24 else name
        area_display = area[:14] if len(area) > 14 else area
        print(f"{i:<6} {pid:<15} {name_display:<25} {area_display:<15} {count:<12}")
    print()

def summarize_decks(decks):
    """Summarize deck statistics"""
    print("=" * 80)
    print("DECK SUMMARY")
    print("=" * 80)
    print(f"Total Decks: {len(decks)}")
    print()
    
    # Analyze card usage
    card_usage = defaultdict(int)
    card_names = {}
    
    for deck in decks:
        for card in deck.get('cards', []):
            card_name = card.get('card_name', '')
            card_code = card.get('card_code', '')
            quantity = card.get('quantity', 0)
            
            if card_name:
                card_key = f"{card_name} ({card_code})" if card_code else card_name
                card_usage[card_key] += quantity
                card_names[card_key] = card_name
    
    print("Top 30 Most Used Cards:")
    print(f"{'Rank':<6} {'Card Name':<50} {'Total Copies':<12}")
    print("-" * 80)
    for i, (card_key, count) in enumerate(sorted(card_usage.items(), key=lambda x: x[1], reverse=True)[:30], 1):
        card_display = card_key[:49] if len(card_key) > 49 else card_key
        print(f"{i:<6} {card_display:<50} {count:<12}")
    print()
    
    # Deck size statistics
    deck_sizes = [len(d.get('cards', [])) for d in decks]
    avg_deck_size = sum(deck_sizes) / len(deck_sizes) if deck_sizes else 0
    print(f"Average Deck Size: {avg_deck_size:.1f} cards")
    print(f"Min Deck Size: {min(deck_sizes) if deck_sizes else 0} cards")
    print(f"Max Deck Size: {max(deck_sizes) if deck_sizes else 0} cards")
    print()
    
    # Unique cards per deck
    unique_cards_per_deck = [len(d.get('cards', [])) for d in decks]
    avg_unique = sum(unique_cards_per_deck) / len(unique_cards_per_deck) if unique_cards_per_deck else 0
    print(f"Average Unique Cards per Deck: {avg_unique:.1f}")
    print()

def summarize_deck_archetypes(decks):
    """Try to identify deck archetypes based on key cards"""
    print("=" * 80)
    print("DECK ARCHETYPE ANALYSIS")
    print("=" * 80)
    
    # Group decks by their most used Pokemon
    deck_key_cards = defaultdict(list)
    
    for deck in decks:
        # Find the most common non-energy cards
        card_counts = {}
        for card in deck.get('cards', []):
            card_name = card.get('card_name', '')
            quantity = card.get('quantity', 0)
            if card_name and 'エネルギー' not in card_name and 'Energy' not in card_name:
                card_counts[card_name] = card_counts.get(card_name, 0) + quantity
        
        # Get top 3 cards
        if card_counts:
            top_cards = sorted(card_counts.items(), key=lambda x: x[1], reverse=True)[:3]
            key_card = top_cards[0][0] if top_cards else 'Unknown'
            deck_key_cards[key_card].append(deck)
    
    print(f"Top 20 Deck Archetypes (by key card):")
    print(f"{'Rank':<6} {'Key Card':<50} {'Deck Count':<12}")
    print("-" * 80)
    for i, (key_card, deck_list) in enumerate(sorted(deck_key_cards.items(), key=lambda x: len(x[1]), reverse=True)[:20], 1):
        card_display = key_card[:49] if len(key_card) > 49 else key_card
        print(f"{i:<6} {card_display:<50} {len(deck_list):<12}")
    print()

def main():
    # Load all data
    print("Loading event data...")
    events = load_all_events()
    print(f"Loaded {len(events)} events")
    
    print("Loading deck data...")
    decks = load_all_decks()
    print(f"Loaded {len(decks)} decks")
    print()
    
    # Generate summaries
    summarize_events(events)
    summarize_players(events)
    summarize_decks(decks)
    summarize_deck_archetypes(decks)
    
    print("=" * 80)
    print("Summary complete!")
    print("=" * 80)

if __name__ == "__main__":
    main()
