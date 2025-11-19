"""
Database cleanup and integrity checker for PTCG Events Database.

This script:
1. Identifies and removes duplicate records
2. Validates data integrity
3. Repairs any referential integrity issues
4. Optimizes database performance
"""

import sqlite3
import os
from datetime import datetime
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class DatabaseCleaner:
    """Clean and validate PTCG events database."""

    def __init__(self, db_path='ptcg_events.db'):
        self.db_path = db_path
        self.conn = None
        self.backup_path = None

    def connect(self):
        """Connect to database."""
        self.conn = sqlite3.connect(self.db_path)
        self.conn.execute("PRAGMA foreign_keys = ON")
        logger.info(f"Connected to database: {self.db_path}")

    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()
            logger.info("Database connection closed")

    def create_backup(self):
        """Create database backup before cleanup."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.backup_path = f'{self.db_path}.backup_{timestamp}'

        # Use SQLite backup for consistency
        backup_conn = sqlite3.connect(self.backup_path)
        self.conn.backup(backup_conn)
        backup_conn.close()

        logger.info(f"Database backup created: {self.backup_path}")
        return self.backup_path

    def find_duplicates(self):
        """Find all duplicate records in the database."""
        cursor = self.conn.cursor()
        duplicates = {}

        # Check deck_cards for duplicates
        cursor.execute("""
            SELECT deck_id, card_name, card_code, COUNT(*) as count,
                   GROUP_CONCAT(id) as ids, GROUP_CONCAT(quantity) as quantities
            FROM deck_cards
            GROUP BY deck_id, card_name, card_code
            HAVING count > 1
            ORDER BY count DESC
        """)

        deck_card_duplicates = cursor.fetchall()
        duplicates['deck_cards'] = deck_card_duplicates

        # Check event_results for duplicates
        cursor.execute("""
            SELECT event_id, player_id, rank, COUNT(*) as count, GROUP_CONCAT(id) as ids
            FROM event_results
            GROUP BY event_id, player_id, rank
            HAVING count > 1
        """)

        event_result_duplicates = cursor.fetchall()
        duplicates['event_results'] = event_result_duplicates

        # Check decks for duplicates
        cursor.execute("""
            SELECT deck_id, COUNT(*) as count
            FROM decks
            GROUP BY deck_id
            HAVING count > 1
        """)

        deck_duplicates = cursor.fetchall()
        duplicates['decks'] = deck_duplicates

        # Check events for duplicates
        cursor.execute("""
            SELECT event_id, COUNT(*) as count
            FROM events
            GROUP BY event_id
            HAVING count > 1
        """)

        event_duplicates = cursor.fetchall()
        duplicates['events'] = event_duplicates

        return duplicates

    def remove_deck_card_duplicates(self):
        """Remove duplicate deck cards, keeping the one with highest quantity."""
        cursor = self.conn.cursor()

        logger.info("Removing deck card duplicates...")

        # Find duplicates and keep the one with highest quantity
        duplicates_query = """
            SELECT deck_id, card_name, card_code,
                   MAX(quantity) as max_quantity,
                   GROUP_CONCAT(id) as all_ids
            FROM deck_cards
            GROUP BY deck_id, card_name, card_code
            HAVING COUNT(*) > 1
        """

        cursor.execute(duplicates_query)
        duplicates = cursor.fetchall()

        removed_count = 0

        for dup in duplicates:
            deck_id, card_name, card_code, max_quantity, all_ids = dup
            ids_list = all_ids.split(',')

            # Keep the first ID, delete the rest
            keep_id = ids_list[0]
            delete_ids = ids_list[1:]

            # Update the kept record with max quantity
            cursor.execute("""
                UPDATE deck_cards
                SET quantity = ?
                WHERE id = ?
            """, (max_quantity, keep_id))

            # Delete duplicates
            if delete_ids:
                placeholders = ','.join('?' * len(delete_ids))
                cursor.execute(f"""
                    DELETE FROM deck_cards
                    WHERE id IN ({placeholders})
                """, delete_ids)

            removed_count += len(delete_ids)

        self.conn.commit()
        logger.info(f"Removed {removed_count} duplicate deck card entries")
        return removed_count

    def remove_event_result_duplicates(self):
        """Remove duplicate event results."""
        cursor = self.conn.cursor()

        logger.info("Removing event result duplicates...")

        # Find duplicates
        cursor.execute("""
            SELECT event_id, player_id, rank, GROUP_CONCAT(id) as ids
            FROM event_results
            GROUP BY event_id, player_id, rank
            HAVING COUNT(*) > 1
        """)

        duplicates = cursor.fetchall()
        removed_count = 0

        for dup in duplicates:
            event_id, player_id, rank, ids_str = dup
            ids_list = ids_str.split(',')

            # Keep the first one, delete the rest
            keep_id = ids_list[0]
            delete_ids = ids_list[1:]

            if delete_ids:
                placeholders = ','.join('?' * len(delete_ids))
                cursor.execute(f"""
                    DELETE FROM event_results
                    WHERE id IN ({placeholders})
                """, delete_ids)

            removed_count += len(delete_ids)

        self.conn.commit()
        logger.info(f"Removed {removed_count} duplicate event result entries")
        return removed_count

    def remove_table_duplicates(self, table_name, key_columns):
        """Generic method to remove duplicates from any table."""
        cursor = self.conn.cursor()

        # Build GROUP BY clause
        group_by = ', '.join(key_columns)
        count_col = 'COUNT(*) as count'

        # For tables with 'id' column, include it in select
        if table_name in ['event_results', 'deck_cards']:
            select_cols = ', '.join(key_columns + [count_col, 'GROUP_CONCAT(id) as ids'])
        else:
            # For tables without 'id' column, use primary key
            primary_key = key_columns[0]  # Assume first key column is primary key
            select_cols = ', '.join(key_columns + [count_col, f'GROUP_CONCAT({primary_key}) as ids'])

        query = f"""
            SELECT {select_cols}
            FROM {table_name}
            GROUP BY {group_by}
            HAVING count > 1
        """

        cursor.execute(query)
        duplicates = cursor.fetchall()

        if not duplicates:
            return 0

        logger.info(f"Removing duplicates from {table_name}...")

        removed_count = 0
        for dup in duplicates:
            ids_str = dup[-1]  # Last column is the concatenated IDs/keys
            ids_list = ids_str.split(',')

            # Keep the first one, delete the rest
            delete_ids = ids_list[1:]

            if delete_ids:
                if table_name in ['event_results', 'deck_cards']:
                    # Use 'id' column
                    placeholders = ','.join('?' * len(delete_ids))
                    cursor.execute(f"""
                        DELETE FROM {table_name}
                        WHERE id IN ({placeholders})
                    """, delete_ids)
                else:
                    # Use primary key column
                    primary_key = key_columns[0]
                    placeholders = ','.join('?' * len(delete_ids))
                    cursor.execute(f"""
                        DELETE FROM {table_name}
                        WHERE {primary_key} IN ({placeholders})
                    """, delete_ids)

            removed_count += len(delete_ids)

        self.conn.commit()
        logger.info(f"Removed {removed_count} duplicate {table_name} entries")
        return removed_count

    def validate_referential_integrity(self):
        """Check and fix referential integrity issues."""
        cursor = self.conn.cursor()
        issues = []

        logger.info("Checking referential integrity...")

        # Check for event_results without valid events
        cursor.execute("""
            SELECT COUNT(*) FROM event_results
            WHERE event_id NOT IN (SELECT event_id FROM events)
        """)
        orphaned_results = cursor.fetchone()[0]
        if orphaned_results > 0:
            logger.warning(f"Found {orphaned_results} event_results with invalid event_id")
            issues.append(f"event_results: {orphaned_results} orphaned records")

            # Remove orphaned records
            cursor.execute("""
                DELETE FROM event_results
                WHERE event_id NOT IN (SELECT event_id FROM events)
            """)
            logger.info(f"Removed {cursor.rowcount} orphaned event_results")

        # Check for decks without valid events
        cursor.execute("""
            SELECT COUNT(*) FROM decks
            WHERE event_id NOT IN (SELECT event_id FROM events)
        """)
        orphaned_decks = cursor.fetchone()[0]
        if orphaned_decks > 0:
            logger.warning(f"Found {orphaned_decks} decks with invalid event_id")
            issues.append(f"decks: {orphaned_decks} orphaned records")

            cursor.execute("""
                DELETE FROM decks
                WHERE event_id NOT IN (SELECT event_id FROM events)
            """)
            logger.info(f"Removed {cursor.rowcount} orphaned decks")

        # Check for deck_cards without valid decks
        cursor.execute("""
            SELECT COUNT(*) FROM deck_cards
            WHERE deck_id NOT IN (SELECT deck_id FROM decks)
        """)
        orphaned_cards = cursor.fetchone()[0]
        if orphaned_cards > 0:
            logger.warning(f"Found {orphaned_cards} deck_cards with invalid deck_id")
            issues.append(f"deck_cards: {orphaned_cards} orphaned records")

            cursor.execute("""
                DELETE FROM deck_cards
                WHERE deck_id NOT IN (SELECT deck_id FROM decks)
            """)
            logger.info(f"Removed {cursor.rowcount} orphaned deck_cards")

        # Check for event_results without valid players
        cursor.execute("""
            SELECT COUNT(*) FROM event_results
            WHERE player_id NOT IN (SELECT player_id FROM players)
        """)
        invalid_players = cursor.fetchone()[0]
        if invalid_players > 0:
            logger.warning(f"Found {invalid_players} event_results with invalid player_id")
            issues.append(f"event_results: {invalid_players} invalid player references")

        self.conn.commit()

        if not issues:
            logger.info("✅ Referential integrity check passed")
        else:
            logger.warning(f"Fixed {len(issues)} referential integrity issues")

        return issues

    def validate_deck_integrity(self):
        """Validate that all decks have correct card counts."""
        cursor = self.conn.cursor()

        logger.info("Validating deck card counts...")

        # Check decks with incorrect card counts
        cursor.execute("""
            SELECT d.deck_id, d.rank, COALESCE(SUM(dc.quantity), 0) as total_cards
            FROM decks d
            LEFT JOIN deck_cards dc ON d.deck_id = dc.deck_id
            GROUP BY d.deck_id
            HAVING total_cards != 60
            ORDER BY total_cards DESC
        """)

        invalid_decks = cursor.fetchall()

        if invalid_decks:
            logger.warning(f"Found {len(invalid_decks)} decks with incorrect card counts:")
            for deck in invalid_decks[:10]:  # Show first 10
                logger.warning(f"  Deck {deck[0]} (Rank: {deck[1]}): {deck[2]} cards")
            return invalid_decks
        else:
            logger.info("✅ All decks have correct card counts (60 cards)")
            return []

    def optimize_database(self):
        """Optimize database performance."""
        logger.info("Optimizing database...")

        # Rebuild indexes
        self.conn.execute("REINDEX")

        # Vacuum database to reclaim space
        self.conn.execute("VACUUM")

        # Analyze for query optimization
        self.conn.execute("ANALYZE")

        logger.info("✅ Database optimization complete")

    def get_statistics(self):
        """Get comprehensive database statistics."""
        cursor = self.conn.cursor()

        stats = {}

        # Basic counts
        cursor.execute("SELECT COUNT(*) FROM events")
        stats['total_events'] = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM players")
        stats['total_players'] = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM decks")
        stats['total_decks'] = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM deck_cards")
        stats['total_card_entries'] = cursor.fetchone()[0]

        # Duplicate counts
        cursor.execute("""
            SELECT COUNT(*) FROM (
                SELECT deck_id, card_name, card_code, COUNT(*) as cnt
                FROM deck_cards
                GROUP BY deck_id, card_name, card_code
                HAVING cnt > 1
            )
        """)
        stats['duplicate_card_entries'] = cursor.fetchone()[0]

        # Integrity issues
        cursor.execute("SELECT COUNT(*) FROM event_results WHERE event_id NOT IN (SELECT event_id FROM events)")
        stats['orphaned_event_results'] = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM decks WHERE event_id NOT IN (SELECT event_id FROM events)")
        stats['orphaned_decks'] = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM deck_cards WHERE deck_id NOT IN (SELECT deck_id FROM decks)")
        stats['orphaned_deck_cards'] = cursor.fetchone()[0]

        # Deck validation
        cursor.execute("""
            SELECT COUNT(*) FROM (
                SELECT d.deck_id
                FROM decks d
                LEFT JOIN deck_cards dc ON d.deck_id = dc.deck_id
                GROUP BY d.deck_id
                HAVING COALESCE(SUM(dc.quantity), 0) != 60
            )
        """)
        stats['invalid_deck_counts'] = cursor.fetchone()[0]

        return stats

    def cleanup(self):
        """Run complete database cleanup."""
        logger.info("Starting comprehensive database cleanup...")

        # Create backup
        self.create_backup()

        # Find initial duplicates
        initial_duplicates = self.find_duplicates()
        logger.info("Initial duplicate analysis:")
        for table, duplicates in initial_duplicates.items():
            logger.info(f"  {table}: {len(duplicates)} duplicate groups")

        # Remove duplicates
        total_removed = 0

        # Remove deck card duplicates
        removed = self.remove_deck_card_duplicates()
        total_removed += removed

        # Remove event result duplicates
        removed = self.remove_event_result_duplicates()
        total_removed += removed

        # Remove other table duplicates
        removed += self.remove_table_duplicates('decks', ['deck_id'])
        removed += self.remove_table_duplicates('events', ['event_id'])
        total_removed += removed

        # Fix referential integrity
        integrity_issues = self.validate_referential_integrity()

        # Validate deck integrity
        invalid_decks = self.validate_deck_integrity()

        # Optimize database
        self.optimize_database()

        # Final statistics
        final_stats = self.get_statistics()

        logger.info("=" * 60)
        logger.info("CLEANUP SUMMARY")
        logger.info("=" * 60)
        logger.info(f"Total duplicate entries removed: {total_removed}")
        logger.info(f"Referential integrity issues fixed: {len(integrity_issues)}")
        logger.info(f"Decks with invalid card counts: {final_stats['invalid_deck_counts']}")
        logger.info(f"Final database state:")
        logger.info(f"  Events: {final_stats['total_events']}")
        logger.info(f"  Players: {final_stats['total_players']}")
        logger.info(f"  Decks: {final_stats['total_decks']}")
        logger.info(f"  Card entries: {final_stats['total_card_entries']}")
        logger.info(f"  Remaining duplicates: {final_stats['duplicate_card_entries']}")
        logger.info("=" * 60)
        logger.info(f"Backup preserved at: {self.backup_path}")

        return {
            'duplicates_removed': total_removed,
            'integrity_issues_fixed': len(integrity_issues),
            'invalid_decks': len(invalid_decks),
            'final_stats': final_stats,
            'backup_path': self.backup_path
        }


def main():
    """Main cleanup execution."""
    logger.info("Starting database cleanup and integrity check")

    cleaner = DatabaseCleaner()

    try:
        cleaner.connect()
        results = cleaner.cleanup()

        if results['duplicates_removed'] == 0 and results['integrity_issues_fixed'] == 0:
            logger.info("✅ Database was already clean!")
        else:
            logger.info("✅ Database cleanup completed successfully!")

    except Exception as e:
        logger.error(f"Cleanup failed: {e}")
        raise
    finally:
        cleaner.close()


if __name__ == '__main__':
    main()