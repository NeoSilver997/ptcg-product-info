"""
Calculate card statistics by usage count and win rate by type.

This script analyzes Pokemon TCG event data to rank cards by:
- Usage count (how many decks they appear in)
- Win rate (average rank performance)
- Top placements (1st and top 8 finishes)

Results are stored in a new database table for analysis.
"""

import sqlite3
import json
from pathlib import Path
import logging
from typing import Dict, List, Any

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class CardStatisticsCalculator:
    """Calculate and store card statistics from event data."""

    def __init__(self, event_db='ptcg_events.db', main_db=r'c:\AI_Server\Coding\PokemonDBByjules\PTCG_CardDB_Tc\pokemon_cards.db'):
        self.event_db_path = event_db
        self.main_db_path = main_db
        self.event_conn = None
        self.main_conn = None

    def connect(self):
        """Connect to both databases."""
        self.event_conn = sqlite3.connect(self.event_db_path)
        self.event_conn.row_factory = sqlite3.Row
        self.main_conn = sqlite3.connect(self.main_db_path)
        self.main_conn.row_factory = sqlite3.Row
        logger.info("Connected to both databases")

    def close(self):
        """Close database connections."""
        if self.event_conn:
            self.event_conn.close()
        if self.main_conn:
            self.main_conn.close()
        logger.info("Database connections closed")

    def create_statistics_table(self):
        """Create table to store card statistics."""
        cursor = self.event_conn.cursor()

        # Drop existing table if it exists
        cursor.execute("DROP TABLE IF EXISTS card_statistics")

        cursor.execute("""
            CREATE TABLE card_statistics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                card_name TEXT NOT NULL,
                chinese_name TEXT,
                card_type TEXT NOT NULL,
                main_card_id INTEGER,
                deck_count INTEGER NOT NULL,
                avg_rank REAL,
                win_rate REAL,
                top1_count INTEGER DEFAULT 0,
                top8_count INTEGER DEFAULT 0,
                top1_rate REAL,
                top8_rate REAL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Create indexes for performance
        cursor.execute("CREATE INDEX idx_card_stats_type ON card_statistics(card_type)")
        cursor.execute("CREATE INDEX idx_card_stats_deck_count ON card_statistics(deck_count DESC)")
        cursor.execute("CREATE INDEX idx_card_stats_win_rate ON card_statistics(win_rate DESC)")

        self.event_conn.commit()
        logger.info("Created card_statistics table with indexes")

    def calculate_card_statistics(self) -> List[Dict[str, Any]]:
        """Calculate card statistics from event data."""
        logger.info("Calculating card statistics...")

        # First, get all the card data from event database
        query = """
            SELECT
                COALESCE(cm.main_card_name, dc.card_name) as card_name,
                COALESCE(cm.main_card_name, dc.card_name) as chinese_name,
                COUNT(DISTINCT dc.deck_id) as deck_count,
                COUNT(DISTINCT CASE WHEN d.rank = '1位' THEN dc.deck_id END) as top1_count,
                COUNT(DISTINCT CASE WHEN d.rank IN ('1位', '2位', '3位', '4位', '5位', '6位', '7位', '8位') THEN dc.deck_id END) as top8_count,
                COALESCE(cm.main_card_id, 0) as main_card_id,
                dc.card_name as original_name,
                GROUP_CONCAT(d.rank) as all_ranks
            FROM deck_cards dc
            LEFT JOIN card_mappings cm ON dc.card_id = cm.event_card_id
            LEFT JOIN decks d ON dc.deck_id = d.deck_id
            GROUP BY COALESCE(cm.main_card_id, dc.card_name)
            HAVING deck_count >= 3
            ORDER BY deck_count DESC
        """

        cursor = self.event_conn.cursor()
        cursor.execute(query)
        rows = cursor.fetchall()

        statistics = []
        for row in rows:
            main_card_id = row['main_card_id']

            # Determine card type
            if main_card_id > 0:
                # Get card type from main database
                main_cursor = self.main_conn.cursor()
                main_cursor.execute("SELECT card_type FROM cards WHERE id = ?", (main_card_id,))
                main_row = main_cursor.fetchone()
                card_type = main_row['card_type'] if main_row else '其他'
            else:
                # Determine from card name patterns
                card_name = row['original_name']
                if 'エネルギー' in card_name:
                    card_type = '能量'
                elif '博士' in card_name or 'サポート' in card_name:
                    card_type = '支援者'
                elif 'スタジアム' in card_name:
                    card_type = '競技場'
                else:
                    card_type = '其他'

            # Normalize card types
            card_type_mapping = {
                '基本能量卡': '能量',
                '特殊能量卡': '能量',
                '支援者卡': '支援者',
                '競技場卡': '競技場',
                '寶可夢道具': '物品卡'
            }
            card_type = card_type_mapping.get(card_type, card_type) or '其他'

            # Calculate average rank from Japanese rank strings
            all_ranks = row['all_ranks']
            if all_ranks:
                rank_strings = all_ranks.split(',')
                numeric_ranks = []
                for rank_str in rank_strings:
                    if rank_str and rank_str.strip():
                        # Convert Japanese rank format to number (e.g., "1位" -> 1)
                        rank_num = rank_str.strip().replace('位', '')
                        try:
                            numeric_ranks.append(float(rank_num))
                        except ValueError:
                            continue
                avg_rank = sum(numeric_ranks) / len(numeric_ranks) if numeric_ranks else None
            else:
                avg_rank = None

            # Calculate win rate (lower rank = better performance, so invert)
            win_rate = (1 / avg_rank * 100) if avg_rank and avg_rank > 0 else 0

            # Calculate placement rates
            deck_count = row['deck_count']
            top1_rate = (row['top1_count'] / deck_count * 100) if deck_count > 0 else 0
            top8_rate = (row['top8_count'] / deck_count * 100) if deck_count > 0 else 0

            stat = {
                'card_name': row['card_name'],
                'chinese_name': row['chinese_name'],
                'card_type': card_type,
                'main_card_id': main_card_id,
                'deck_count': deck_count,
                'avg_rank': round(avg_rank, 2) if avg_rank else None,
                'win_rate': round(win_rate, 2),
                'top1_count': row['top1_count'],
                'top8_count': row['top8_count'],
                'top1_rate': round(top1_rate, 2),
                'top8_rate': round(top8_rate, 2)
            }
            statistics.append(stat)

        # Sort by deck_count DESC, then by win_rate DESC
        statistics.sort(key=lambda x: (x['deck_count'], x['win_rate'] or 0), reverse=True)

        logger.info(f"Calculated statistics for {len(statistics)} cards")
        return statistics

    def save_statistics(self, statistics: List[Dict[str, Any]]):
        """Save statistics to database."""
        logger.info("Saving statistics to database...")

        cursor = self.event_conn.cursor()

        # Clear existing data
        cursor.execute("DELETE FROM card_statistics")

        # Insert new statistics
        for stat in statistics:
            cursor.execute("""
                INSERT INTO card_statistics
                (card_name, chinese_name, card_type, main_card_id, deck_count,
                 avg_rank, win_rate, top1_count, top8_count, top1_rate, top8_rate)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                stat['card_name'],
                stat['chinese_name'],
                stat['card_type'],
                stat['main_card_id'],
                stat['deck_count'],
                stat['avg_rank'],
                stat['win_rate'],
                stat['top1_count'],
                stat['top8_count'],
                stat['top1_rate'],
                stat['top8_rate']
            ))

        self.event_conn.commit()
        logger.info(f"Saved {len(statistics)} card statistics to database")

    def get_statistics_by_type(self) -> Dict[str, List[Dict[str, Any]]]:
        """Get statistics grouped by card type, sorted by usage and win rate."""
        cursor = self.event_conn.cursor()
        cursor.execute("""
            SELECT * FROM card_statistics
            ORDER BY card_type, deck_count DESC, win_rate DESC
        """)

        rows = cursor.fetchall()
        stats_by_type = {}

        for row in rows:
            card_type = row['card_type']
            if card_type not in stats_by_type:
                stats_by_type[card_type] = []

            stat = dict(row)
            stats_by_type[card_type].append(stat)

        return stats_by_type

    def print_summary(self):
        """Print summary of card statistics."""
        stats_by_type = self.get_statistics_by_type()

        print("\n" + "="*80)
        print("Pokemon TCG Card Statistics Summary")
        print("="*80)

        total_cards = sum(len(cards) for cards in stats_by_type.values())
        print(f"Total cards analyzed: {total_cards}")

        for card_type, cards in stats_by_type.items():
            print(f"\n{card_type} ({len(cards)} cards):")
            print("-" * 40)

            # Show top 5 by usage
            top_by_usage = sorted(cards, key=lambda x: x['deck_count'], reverse=True)[:5]
            print("Top by usage:")
            for i, card in enumerate(top_by_usage, 1):
                print(f"  {i}. {card['chinese_name'] or card['card_name']} - {card['deck_count']} decks")

            # Show top 5 by win rate
            top_by_winrate = sorted(cards, key=lambda x: x['win_rate'], reverse=True)[:5]
            print("Top by win rate:")
            for i, card in enumerate(top_by_winrate, 1):
                print(f"  {i}. {card['chinese_name'] or card['card_name']} - {card['win_rate']:.1f}%")

    def run(self):
        """Run the complete statistics calculation and storage process."""
        try:
            self.connect()
            self.create_statistics_table()
            statistics = self.calculate_card_statistics()
            self.save_statistics(statistics)
            self.print_summary()
            logger.info("Card statistics calculation completed successfully")

        except Exception as e:
            logger.error(f"Error calculating card statistics: {e}")
            raise
        finally:
            self.close()


def main():
    """Main function."""
    calculator = CardStatisticsCalculator()
    calculator.run()


if __name__ == "__main__":
    main()