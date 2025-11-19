#!/usr/bin/env python3
"""
Fix Quantity Inflation in PTCG Events Database

This script corrects the quantity inflation issue where deck card quantities
were multiplied by import iterations. Decks should have exactly 60 cards total.

The fix identifies decks with inflated totals and divides all quantities by
the appropriate multiplier to restore correct values.
"""

import sqlite3
import logging
from pathlib import Path

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class QuantityFixer:
    """Fix inflated card quantities in the PTCG events database."""

    def __init__(self, db_path='ptcg_events.db'):
        self.db_path = Path(db_path)
        self.conn = None

    def connect(self):
        """Connect to the database."""
        if not self.db_path.exists():
            raise FileNotFoundError(f"Database not found: {self.db_path}")

        self.conn = sqlite3.connect(str(self.db_path))
        logger.info(f"Connected to database: {self.db_path}")

    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()
            logger.info("Database connection closed")

    def analyze_inflation(self):
        """Analyze the quantity inflation patterns."""
        cursor = self.conn.cursor()

        # Get deck totals distribution
        cursor.execute('''
            SELECT total_cards, COUNT(*) as deck_count
            FROM (
                SELECT d.deck_id, SUM(dc.quantity) as total_cards
                FROM decks d
                JOIN deck_cards dc ON d.deck_id = dc.deck_id
                GROUP BY d.deck_id
            )
            GROUP BY total_cards
            ORDER BY total_cards
        ''')

        logger.info("Current deck total distribution:")
        total_decks = 0
        inflated_decks = 0

        for total_cards, deck_count in cursor.fetchall():
            total_decks += deck_count
            if total_cards != 60:
                inflated_decks += deck_count
            logger.info(f"  {total_cards} cards: {deck_count} decks")

        logger.info(f"\nTotal decks: {total_decks}")
        logger.info(f"Inflated decks: {inflated_decks}")
        logger.info(f"Correct decks: {total_decks - inflated_decks}")

        return total_decks, inflated_decks

    def calculate_multiplier(self, total_cards):
        """Calculate the inflation multiplier for a deck."""
        # Only fix decks that are clear multiples of 60
        if total_cards % 60 == 0 and total_cards > 60:
            return total_cards // 60
        else:
            # Don't fix decks that don't divide evenly by 60
            return None

    def fix_inflated_decks(self):
        """Fix all decks with inflated quantities."""
        cursor = self.conn.cursor()

        # Get all decks with their total cards
        cursor.execute('''
            SELECT d.deck_id, SUM(dc.quantity) as total_cards
            FROM decks d
            JOIN deck_cards dc ON d.deck_id = dc.deck_id
            GROUP BY d.deck_id
            HAVING total_cards != 60
            ORDER BY total_cards DESC
        ''')

        inflated_decks = cursor.fetchall()
        logger.info(f"Found {len(inflated_decks)} decks to fix")

        fixed_count = 0
        error_count = 0

        for deck_id, total_cards in inflated_decks:
            try:
                multiplier = self.calculate_multiplier(total_cards)
                if multiplier is None:
                    logger.debug(f"Skipping deck {deck_id}: {total_cards} cards (not a clear multiple of 60)")
                    continue
                    
                logger.debug(f"Fixing deck {deck_id}: {total_cards} cards, multiplier {multiplier}")

                # Update all quantities in this deck
                cursor.execute('''
                    UPDATE deck_cards
                    SET quantity = quantity / ?
                    WHERE deck_id = ?
                ''', (multiplier, deck_id))

                # Verify the fix
                cursor.execute('''
                    SELECT SUM(quantity) as new_total
                    FROM deck_cards
                    WHERE deck_id = ?
                ''', (deck_id,))

                new_total = cursor.fetchone()[0]
                logger.debug(f"Deck {deck_id}: {total_cards} -> {new_total} cards")

                fixed_count += 1

            except Exception as e:
                logger.error(f"Error fixing deck {deck_id}: {e}")
                error_count += 1

        self.conn.commit()
        logger.info(f"Fixed {fixed_count} decks, {error_count} errors")

        return fixed_count, error_count

    def validate_fix(self):
        """Validate that the fix worked correctly."""
        cursor = self.conn.cursor()

        # Check deck totals after fix
        cursor.execute('''
            SELECT total_cards, COUNT(*) as deck_count
            FROM (
                SELECT d.deck_id, SUM(dc.quantity) as total_cards
                FROM decks d
                JOIN deck_cards dc ON d.deck_id = dc.deck_id
                GROUP BY d.deck_id
            )
            GROUP BY total_cards
            ORDER BY total_cards
        ''')

        logger.info("Deck totals after fix:")
        correct_decks = 0
        still_inflated = 0

        for total_cards, deck_count in cursor.fetchall():
            if total_cards == 60:
                correct_decks += deck_count
            else:
                still_inflated += deck_count
            logger.info(f"  {total_cards} cards: {deck_count} decks")

        logger.info(f"\nValidation results:")
        logger.info(f"Correct decks (60 cards): {correct_decks}")
        logger.info(f"Still inflated: {still_inflated}")

        # Check for any invalid quantities (0 or negative)
        cursor.execute('''
            SELECT COUNT(*) as invalid_quantities
            FROM deck_cards
            WHERE quantity <= 0
        ''')

        invalid_count = cursor.fetchone()[0]
        if invalid_count > 0:
            logger.warning(f"Found {invalid_count} cards with invalid quantities (<= 0)")
        else:
            logger.info("All quantities are valid (> 0)")

        return correct_decks, still_inflated, invalid_count

    def create_backup(self):
        """Create a backup of the database before making changes."""
        backup_path = self.db_path.with_suffix('.backup.db')
        import shutil
        shutil.copy2(self.db_path, backup_path)
        logger.info(f"Backup created: {backup_path}")
        return backup_path


def main():
    """Main execution function."""
    logger.info("Starting quantity inflation fix")

    fixer = QuantityFixer()

    try:
        fixer.connect()

        # Create backup
        backup_path = fixer.create_backup()

        # Analyze current state
        logger.info("=" * 60)
        logger.info("ANALYSIS - BEFORE FIX")
        logger.info("=" * 60)
        total_decks, inflated_decks = fixer.analyze_inflation()

        # Apply fix
        logger.info("\n" + "=" * 60)
        logger.info("APPLYING FIX")
        logger.info("=" * 60)
        fixed_count, error_count = fixer.fix_inflated_decks()

        # Validate results
        logger.info("\n" + "=" * 60)
        logger.info("VALIDATION - AFTER FIX")
        logger.info("=" * 60)
        correct_decks, still_inflated, invalid_count = fixer.validate_fix()

        # Summary
        logger.info("\n" + "=" * 60)
        logger.info("SUMMARY")
        logger.info("=" * 60)
        logger.info(f"Total decks processed: {total_decks}")
        logger.info(f"Inflated decks found: {inflated_decks}")
        logger.info(f"Decks successfully fixed: {fixed_count}")
        logger.info(f"Fix errors: {error_count}")
        logger.info(f"Correct decks after fix: {correct_decks}")
        logger.info(f"Still inflated: {still_inflated}")
        logger.info(f"Invalid quantities: {invalid_count}")
        logger.info(f"Backup saved to: {backup_path}")

        if still_inflated == 0 and invalid_count == 0:
            logger.info("✅ Fix completed successfully!")
        else:
            logger.warning("⚠️  Some issues remain - manual review recommended")

    except Exception as e:
        logger.error(f"Fix failed: {e}")
        raise
    finally:
        fixer.close()


if __name__ == '__main__':
    main()