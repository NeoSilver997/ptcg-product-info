"""
Query and analyze Pokemon TCG event data from SQLite database.

This script provides various analysis queries for tournament results and deck compositions.
"""

import sqlite3
import json
from collections import Counter
from pathlib import Path


class EventDataAnalyzer:
    """Analyze event tournament data from SQLite database."""
    
    def __init__(self, db_path='ptcg_events.db'):
        """Initialize analyzer with database connection."""
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
    
    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()
    
    def get_top_players(self, limit=20):
        """Get players with most tournament wins."""
        query = """
            SELECT 
                p.player_id,
                p.player_name,
                p.player_area,
                COUNT(CASE WHEN er.rank = '1位' THEN 1 END) as wins,
                COUNT(CASE WHEN er.rank IN ('1位', '2位', '3位') THEN 1 END) as top3,
                COUNT(*) as total_events,
                SUM(CAST(REPLACE(er.points, 'pt', '') AS INTEGER)) as total_points
            FROM players p
            JOIN event_results er ON p.player_id = er.player_id
            GROUP BY p.player_id
            ORDER BY wins DESC, top3 DESC, total_points DESC
            LIMIT ?
        """
        cursor = self.conn.execute(query, (limit,))
        return [dict(row) for row in cursor.fetchall()]
    
    def get_most_used_cards(self, limit=50):
        """Get most frequently used cards across all decks."""
        query = """
            SELECT 
                card_name,
                card_code,
                COUNT(DISTINCT deck_id) as deck_count,
                SUM(quantity) as total_quantity,
                ROUND(AVG(quantity), 2) as avg_quantity_per_deck
            FROM deck_cards
            WHERE card_name NOT LIKE '%エネルギー%'  -- Exclude basic energy
            GROUP BY card_name, card_code
            ORDER BY deck_count DESC, total_quantity DESC
            LIMIT ?
        """
        cursor = self.conn.execute(query, (limit,))
        return [dict(row) for row in cursor.fetchall()]
    
    def get_deck_archetypes(self):
        """Analyze deck archetypes based on key Pokemon."""
        query = """
            SELECT 
                d.deck_id,
                d.rank,
                e.event_date,
                GROUP_CONCAT(dc.card_name) as cards
            FROM decks d
            JOIN deck_cards dc ON d.deck_id = dc.deck_id
            JOIN events e ON d.event_id = e.event_id
            WHERE dc.card_name LIKE '%ex%' OR dc.card_name LIKE '%V%'
            GROUP BY d.deck_id
        """
        cursor = self.conn.execute(query)
        return [dict(row) for row in cursor.fetchall()]
    
    def get_winning_decks(self, rank='1位', limit=20):
        """Get decks with specific ranking and their compositions."""
        query = """
            SELECT 
                d.deck_id,
                d.rank,
                e.event_id,
                e.event_date,
                e.event_host,
                p.player_name,
                p.player_area,
                COUNT(dc.id) as card_count
            FROM decks d
            JOIN events e ON d.event_id = e.event_id
            LEFT JOIN players p ON d.player_id = p.player_id
            LEFT JOIN deck_cards dc ON d.deck_id = dc.deck_id
            WHERE d.rank = ?
            GROUP BY d.deck_id
            ORDER BY e.event_date DESC
            LIMIT ?
        """
        cursor = self.conn.execute(query, (rank, limit))
        results = [dict(row) for row in cursor.fetchall()]
        
        # Get card details for each deck
        for result in results:
            card_query = """
                SELECT card_name, card_code, quantity
                FROM deck_cards
                WHERE deck_id = ?
                ORDER BY 
                    CASE 
                        WHEN card_name LIKE '%ex%' THEN 1
                        WHEN card_name LIKE '%V%' THEN 2
                        WHEN card_name LIKE '%エネルギー%' THEN 5
                        ELSE 3
                    END,
                    card_name
            """
            cursor = self.conn.execute(card_query, (result['deck_id'],))
            result['cards'] = [dict(row) for row in cursor.fetchall()]
        
        return results
    
    def get_event_statistics(self, event_id):
        """Get detailed statistics for a specific event."""
        # Event info
        event_query = """
            SELECT * FROM events WHERE event_id = ?
        """
        cursor = self.conn.execute(event_query, (event_id,))
        event = dict(cursor.fetchone() or {})
        
        if not event:
            return None
        
        # Results
        results_query = """
            SELECT 
                er.rank,
                p.player_name,
                p.player_area,
                er.points,
                er.deck_id
            FROM event_results er
            JOIN players p ON er.player_id = p.player_id
            WHERE er.event_id = ?
            ORDER BY 
                CASE 
                    WHEN er.rank = '1位' THEN 1
                    WHEN er.rank = '2位' THEN 2
                    WHEN er.rank = '3位' THEN 3
                    WHEN er.rank = '5位' THEN 5
                    WHEN er.rank = '9位' THEN 9
                    ELSE 99
                END
        """
        cursor = self.conn.execute(results_query, (event_id,))
        event['results'] = [dict(row) for row in cursor.fetchall()]
        
        # Card frequency analysis
        card_freq_query = """
            SELECT 
                dc.card_name,
                dc.card_code,
                COUNT(DISTINCT dc.deck_id) as deck_count
            FROM deck_cards dc
            JOIN decks d ON dc.deck_id = d.deck_id
            WHERE d.event_id = ?
            AND dc.card_name NOT LIKE '%エネルギー%'
            GROUP BY dc.card_name, dc.card_code
            ORDER BY deck_count DESC
            LIMIT 20
        """
        cursor = self.conn.execute(card_freq_query, (event_id,))
        event['top_cards'] = [dict(row) for row in cursor.fetchall()]
        
        return event
    
    def get_recent_events(self, limit=10):
        """Get most recent events with basic info."""
        query = """
            SELECT 
                e.event_id,
                e.event_date,
                e.event_host,
                e.event_location,
                COUNT(DISTINCT er.player_id) as player_count,
                COUNT(DISTINCT d.deck_id) as deck_count
            FROM events e
            LEFT JOIN event_results er ON e.event_id = er.event_id
            LEFT JOIN decks d ON e.event_id = d.event_id
            GROUP BY e.event_id
            ORDER BY e.event_date DESC
            LIMIT ?
        """
        cursor = self.conn.execute(query, (limit,))
        return [dict(row) for row in cursor.fetchall()]
    
    def search_cards_in_decks(self, card_name):
        """Search for decks containing a specific card."""
        query = """
            SELECT DISTINCT
                d.deck_id,
                d.rank,
                e.event_id,
                e.event_date,
                p.player_name,
                dc.quantity
            FROM deck_cards dc
            JOIN decks d ON dc.deck_id = d.deck_id
            JOIN events e ON d.event_id = e.event_id
            LEFT JOIN players p ON d.player_id = p.player_id
            WHERE dc.card_name LIKE ?
            ORDER BY e.event_date DESC, d.rank
        """
        cursor = self.conn.execute(query, (f'%{card_name}%',))
        return [dict(row) for row in cursor.fetchall()]
    
    def get_player_history(self, player_id):
        """Get tournament history for a specific player."""
        query = """
            SELECT 
                e.event_id,
                e.event_date,
                e.event_host,
                er.rank,
                er.points,
                er.deck_id
            FROM event_results er
            JOIN events e ON er.event_id = e.event_id
            WHERE er.player_id = ?
            ORDER BY e.event_date DESC
        """
        cursor = self.conn.execute(query, (player_id,))
        return [dict(row) for row in cursor.fetchall()]


def main():
    """Main demonstration of analysis capabilities."""
    analyzer = EventDataAnalyzer('ptcg_events.db')
    
    try:
        print("=" * 70)
        print("POKEMON TCG EVENT DATA ANALYSIS")
        print("=" * 70)
        
        # Recent events
        print("\n📅 RECENT EVENTS:")
        print("-" * 70)
        recent = analyzer.get_recent_events(5)
        for event in recent:
            print(f"{event['event_date']} - {event['event_host']}")
            print(f"  Event ID: {event['event_id']}")
            print(f"  Players: {event['player_count']}, Decks: {event['deck_count']}")
        
        # Top players
        print("\n🏆 TOP PLAYERS (by wins):")
        print("-" * 70)
        top_players = analyzer.get_top_players(10)
        for i, player in enumerate(top_players, 1):
            print(f"{i}. {player['player_name']} ({player['player_area']})")
            print(f"   Wins: {player['wins']}, Top-3: {player['top3']}, Events: {player['total_events']}")
        
        # Most used cards
        print("\n🎴 MOST USED CARDS:")
        print("-" * 70)
        popular_cards = analyzer.get_most_used_cards(15)
        for i, card in enumerate(popular_cards, 1):
            print(f"{i}. {card['card_name']} ({card['card_code']})")
            print(f"   Decks: {card['deck_count']}, Avg Quantity: {card['avg_quantity_per_deck']}")
        
        # Recent winning decks
        print("\n🥇 RECENT 1ST PLACE DECKS:")
        print("-" * 70)
        winners = analyzer.get_winning_decks('1位', 3)
        for deck in winners:
            print(f"\nEvent {deck['event_id']} - {deck['event_date']}")
            print(f"Player: {deck['player_name']} ({deck['player_area']})")
            print(f"Host: {deck['event_host']}")
            print("Key cards:")
            for card in deck['cards'][:10]:  # Show top 10 cards
                print(f"  {card['quantity']}x {card['card_name']}")
        
    finally:
        analyzer.close()
    
    print("\n" + "=" * 70)
    print("Analysis complete!")
    print("=" * 70)


if __name__ == '__main__':
    main()
