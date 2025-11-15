"""
Export event data to various formats for analysis and reporting.
"""

import sqlite3
import json
import csv
from pathlib import Path


class EventDataExporter:
    """Export event data to various formats."""
    
    def __init__(self, db_path='ptcg_events.db'):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
    
    def close(self):
        if self.conn:
            self.conn.close()
    
    def export_card_frequency_csv(self, output_file='card_frequency.csv'):
        """Export card usage frequency to CSV."""
        query = """
            SELECT 
                card_name,
                card_code,
                COUNT(DISTINCT deck_id) as deck_count,
                SUM(quantity) as total_copies,
                ROUND(AVG(quantity), 2) as avg_per_deck,
                ROUND(COUNT(DISTINCT deck_id) * 100.0 / (SELECT COUNT(*) FROM decks), 2) as usage_percentage
            FROM deck_cards
            GROUP BY card_name, card_code
            ORDER BY deck_count DESC
        """
        
        cursor = self.conn.execute(query)
        
        with open(output_file, 'w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['Card Name', 'Card Code', 'Decks Used In', 'Total Copies', 'Avg Per Deck', 'Usage %'])
            
            for row in cursor:
                writer.writerow([
                    row['card_name'],
                    row['card_code'],
                    row['deck_count'],
                    row['total_copies'],
                    row['avg_per_deck'],
                    row['usage_percentage']
                ])
        
        print(f"✅ Exported card frequency to {output_file}")
    
    def export_player_rankings_csv(self, output_file='player_rankings.csv'):
        """Export player performance rankings to CSV."""
        query = """
            SELECT 
                p.player_id,
                p.player_name,
                p.player_area,
                COUNT(*) as total_events,
                COUNT(CASE WHEN er.rank = '1位' THEN 1 END) as first_place,
                COUNT(CASE WHEN er.rank = '2位' THEN 1 END) as second_place,
                COUNT(CASE WHEN er.rank = '3位' THEN 1 END) as third_place,
                COUNT(CASE WHEN er.rank IN ('1位', '2位', '3位') THEN 1 END) as top3_finishes,
                SUM(CAST(REPLACE(er.points, 'pt', '') AS INTEGER)) as total_points
            FROM players p
            JOIN event_results er ON p.player_id = er.player_id
            GROUP BY p.player_id
            ORDER BY first_place DESC, second_place DESC, third_place DESC, total_points DESC
        """
        
        cursor = self.conn.execute(query)
        
        with open(output_file, 'w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                'Player ID', 'Name', 'Region', 'Total Events', 
                '1st Place', '2nd Place', '3rd Place', 'Top-3 Total', 'Total Points'
            ])
            
            for row in cursor:
                writer.writerow([
                    row['player_id'],
                    row['player_name'],
                    row['player_area'],
                    row['total_events'],
                    row['first_place'],
                    row['second_place'],
                    row['third_place'],
                    row['top3_finishes'],
                    row['total_points']
                ])
        
        print(f"✅ Exported player rankings to {output_file}")
    
    def export_deck_archetypes_json(self, output_file='deck_archetypes.json'):
        """Export deck archetypes based on key Pokemon."""
        query = """
            SELECT 
                d.deck_id,
                d.rank,
                e.event_id,
                e.event_date,
                e.event_host,
                p.player_name,
                (
                    SELECT GROUP_CONCAT(card_name || ' (' || quantity || 'x)')
                    FROM deck_cards dc
                    WHERE dc.deck_id = d.deck_id
                    AND (dc.card_name LIKE '%ex%' OR dc.card_name LIKE '%V%')
                ) as key_pokemon
            FROM decks d
            JOIN events e ON d.event_id = e.event_id
            LEFT JOIN players p ON d.player_id = p.player_id
            WHERE d.rank IN ('1位', '2位', '3位')
            ORDER BY e.event_date DESC, d.rank
        """
        
        cursor = self.conn.execute(query)
        results = [dict(row) for row in cursor.fetchall()]
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        
        print(f"✅ Exported deck archetypes to {output_file}")
    
    def export_events_summary_csv(self, output_file='events_summary.csv'):
        """Export event summary data."""
        query = """
            SELECT 
                e.event_id,
                e.event_date,
                e.event_host,
                e.event_location,
                e.event_address,
                COUNT(DISTINCT er.player_id) as player_count,
                COUNT(DISTINCT d.deck_id) as deck_count,
                e.event_url
            FROM events e
            LEFT JOIN event_results er ON e.event_id = er.event_id
            LEFT JOIN decks d ON e.event_id = d.event_id
            GROUP BY e.event_id
            ORDER BY e.event_date DESC
        """
        
        cursor = self.conn.execute(query)
        
        with open(output_file, 'w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                'Event ID', 'Date', 'Host', 'Location', 'Address', 
                'Players', 'Decks', 'URL'
            ])
            
            for row in cursor:
                writer.writerow([
                    row['event_id'],
                    row['event_date'],
                    row['event_host'],
                    row['event_location'],
                    row['event_address'],
                    row['player_count'],
                    row['deck_count'],
                    row['event_url']
                ])
        
        print(f"✅ Exported events summary to {output_file}")
    
    def export_winning_decks_json(self, rank='1位', output_file='winning_decks.json'):
        """Export complete winning deck lists."""
        query = """
            SELECT 
                d.deck_id,
                d.rank,
                e.event_id,
                e.event_date,
                e.event_host,
                p.player_name,
                p.player_area
            FROM decks d
            JOIN events e ON d.event_id = e.event_id
            LEFT JOIN players p ON d.player_id = p.player_id
            WHERE d.rank = ?
            ORDER BY e.event_date DESC
        """
        
        cursor = self.conn.execute(query, (rank,))
        decks = []
        
        for row in cursor:
            deck = dict(row)
            
            # Get cards for this deck
            card_query = """
                SELECT card_name, card_code, quantity
                FROM deck_cards
                WHERE deck_id = ?
                ORDER BY card_name
            """
            card_cursor = self.conn.execute(card_query, (row['deck_id'],))
            deck['cards'] = [dict(card) for card in card_cursor]
            
            decks.append(deck)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(decks, f, ensure_ascii=False, indent=2)
        
        print(f"✅ Exported {len(decks)} winning decks to {output_file}")
    
    def export_card_combinations(self, min_count=50, output_file='card_combos.csv'):
        """Export common card combinations."""
        query = """
            SELECT 
                a.card_name as card_1,
                b.card_name as card_2,
                COUNT(DISTINCT a.deck_id) as deck_count
            FROM deck_cards a
            JOIN deck_cards b ON a.deck_id = b.deck_id AND a.card_name < b.card_name
            WHERE a.card_name NOT LIKE '%エネルギー%' 
            AND b.card_name NOT LIKE '%エネルギー%'
            GROUP BY a.card_name, b.card_name
            HAVING deck_count >= ?
            ORDER BY deck_count DESC
        """
        
        cursor = self.conn.execute(query, (min_count,))
        
        with open(output_file, 'w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['Card 1', 'Card 2', 'Co-occurrence Count'])
            
            for row in cursor:
                writer.writerow([row['card_1'], row['card_2'], row['deck_count']])
        
        print(f"✅ Exported card combinations to {output_file}")


def main():
    """Export all data formats."""
    output_dir = Path('exports')
    output_dir.mkdir(exist_ok=True)
    
    exporter = EventDataExporter('ptcg_events.db')
    
    try:
        print("=" * 60)
        print("EXPORTING EVENT DATA")
        print("=" * 60)
        
        exporter.export_card_frequency_csv(output_dir / 'card_frequency.csv')
        exporter.export_player_rankings_csv(output_dir / 'player_rankings.csv')
        exporter.export_events_summary_csv(output_dir / 'events_summary.csv')
        exporter.export_deck_archetypes_json(output_dir / 'deck_archetypes.json')
        exporter.export_winning_decks_json('1位', output_dir / 'first_place_decks.json')
        exporter.export_card_combinations(min_count=100, output_file=output_dir / 'card_combos.csv')
        
        print("=" * 60)
        print("✅ All exports completed successfully!")
        print(f"📁 Files saved to: {output_dir.absolute()}")
        print("=" * 60)
        
    finally:
        exporter.close()


if __name__ == '__main__':
    main()
