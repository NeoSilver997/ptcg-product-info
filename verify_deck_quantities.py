#!/usr/bin/env python3
"""
Verify deck card quantities against JSON source files.

This script compares the quantities in the database with the original JSON files
to ensure data integrity after the quantity inflation fixes.
"""

import sqlite3
import json
import os
from pathlib import Path
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DeckQuantityVerifier:
    """Verify deck card quantities against JSON source files."""

    def __init__(self, db_path='ptcg_events.db', event_data_dir='event_data'):
        self.db_path = Path(db_path)
        self.event_data_dir = Path(event_data_dir)
        self.conn = None

    def connect_db(self):
        """Connect to the database."""
        if not self.db_path.exists():
            raise FileNotFoundError(f"Database not found: {self.db_path}")

        self.conn = sqlite3.connect(str(self.db_path))
        logger.info(f"Connected to database: {self.db_path}")

    def close_db(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()
            logger.info("Database connection closed")

    def get_all_deck_ids(self):
        """Get all deck IDs from the database."""
        cursor = self.conn.cursor()
        cursor.execute('SELECT deck_id FROM decks ORDER BY deck_id')
        return [row[0] for row in cursor.fetchall()]

    def build_deck_file_mapping(self):
        """Build a mapping of deck_id to JSON file path."""
        logger.info("Building deck to JSON file mapping...")
        mapping = {}

        # Scan all JSON files once
        for event_dir in self.event_data_dir.iterdir():
            if event_dir.is_dir():
                for json_file in event_dir.glob('*.json'):
                    try:
                        with open(json_file, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                            deck_id = data.get('deck_id')
                            if deck_id:
                                mapping[deck_id] = json_file
                    except (json.JSONDecodeError, KeyError, UnicodeDecodeError):
                        continue

        logger.info(f"Found {len(mapping)} deck JSON files")
        return mapping

    def verify_single_deck(self, deck_id, file_mapping):
        """Verify quantities for a single deck."""
        # Find the JSON file
        json_file = file_mapping.get(deck_id)
        if not json_file:
            return {'status': 'NO_JSON', 'deck_id': deck_id}

        # Load JSON data
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                json_data = json.load(f)
        except Exception as e:
            return {'status': 'JSON_ERROR', 'deck_id': deck_id, 'error': str(e)}

        # Extract JSON quantities
        json_cards = {}
        for card in json_data.get('cards', []):
            key = (card['card_name'], card.get('card_code', ''))
            json_cards[key] = card['quantity']

        # Get database quantities
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT card_name, card_code, quantity
            FROM deck_cards
            WHERE deck_id = ?
            ORDER BY card_name
        ''', (deck_id,))

        db_cards = {}
        for row in cursor.fetchall():
            key = (row[0], row[1] or '')
            db_cards[key] = row[2]

        # Compare
        matches = 0
        mismatches = []
        json_only = []
        db_only = []

        # Check JSON cards against DB
        for key, json_qty in json_cards.items():
            if key in db_cards:
                if db_cards[key] == json_qty:
                    matches += 1
                else:
                    mismatches.append({
                        'card': key[0],
                        'code': key[1],
                        'json_qty': json_qty,
                        'db_qty': db_cards[key]
                    })
            else:
                json_only.append(key)

        # Check for DB cards not in JSON
        for key in db_cards:
            if key not in json_cards:
                db_only.append(key)

        total_json = sum(json_cards.values())
        total_db = sum(db_cards.values())

        return {
            'status': 'VERIFIED',
            'deck_id': deck_id,
            'json_file': str(json_file),
            'total_json': total_json,
            'total_db': total_db,
            'matches': matches,
            'mismatches': mismatches,
            'json_only': json_only,
            'db_only': db_only,
            'json_card_count': len(json_cards),
            'db_card_count': len(db_cards)
        }

    def verify_all_decks(self, limit=None):
        """Verify all decks in the database."""
        deck_ids = self.get_all_deck_ids()
        if limit:
            deck_ids = deck_ids[:limit]

        # Build file mapping once
        file_mapping = self.build_deck_file_mapping()

        logger.info(f"Verifying {len(deck_ids)} decks...")

        results = {
            'total': len(deck_ids),
            'verified': 0,
            'no_json': 0,
            'json_errors': 0,
            'perfect_matches': 0,
            'quantity_mismatches': 0,
            'structural_issues': 0,
            'details': []
        }

        for i, deck_id in enumerate(deck_ids):
            if (i + 1) % 500 == 0:
                logger.info(f"Processed {i + 1}/{len(deck_ids)} decks...")

            result = self.verify_single_deck(deck_id, file_mapping)
            results['details'].append(result)

            if result['status'] == 'VERIFIED':
                results['verified'] += 1
                if result['total_json'] == result['total_db'] and len(result['mismatches']) == 0 and len(result['json_only']) == 0 and len(result['db_only']) == 0:
                    results['perfect_matches'] += 1
                elif len(result['mismatches']) > 0:
                    results['quantity_mismatches'] += 1
                elif len(result['json_only']) > 0 or len(result['db_only']) > 0:
                    results['structural_issues'] += 1
            elif result['status'] == 'NO_JSON':
                results['no_json'] += 1
            elif result['status'] == 'JSON_ERROR':
                results['json_errors'] += 1

        return results

    def print_summary(self, results):
        """Print verification summary."""
        print("\n" + "="*80)
        print("DECK QUANTITY VERIFICATION SUMMARY")
        print("="*80)

        print(f"Total decks checked: {results['total']}")
        print(f"Decks with JSON files: {results['verified']}")
        print(f"Decks without JSON files: {results['no_json']}")
        print(f"JSON parsing errors: {results['json_errors']}")
        print()

        if results['verified'] > 0:
            print("Among verified decks:")
            print(f"  Perfect matches: {results['perfect_matches']} ({results['perfect_matches']/results['verified']*100:.1f}%)")
            print(f"  Quantity mismatches: {results['quantity_mismatches']} ({results['quantity_mismatches']/results['verified']*100:.1f}%)")
            print(f"  Structural issues: {results['structural_issues']} ({results['structural_issues']/results['verified']*100:.1f}%)")

        # Show some examples of issues
        if results['quantity_mismatches'] > 0:
            print("\nSample quantity mismatches:")
            count = 0
            for result in results['details']:
                if result['status'] == 'VERIFIED' and len(result['mismatches']) > 0:
                    print(f"  Deck {result['deck_id']}: {len(result['mismatches'])} mismatched quantities")
                    for mismatch in result['mismatches'][:2]:  # Show first 2 per deck
                        print(f"    {mismatch['card']}: JSON={mismatch['json_qty']}, DB={mismatch['db_qty']}")
                    count += 1
                    if count >= 3:  # Show max 3 decks
                        break


def main():
    """Main execution function."""
    verifier = DeckQuantityVerifier()

    try:
        verifier.connect_db()

        # Verify all decks (or limit for testing)
        results = verifier.verify_all_decks(limit=None)  # Set limit=10 for testing

        verifier.print_summary(results)

    except Exception as e:
        logger.error(f"Verification failed: {e}")
        raise
    finally:
        verifier.close_db()


if __name__ == '__main__':
    main()