#!/usr/bin/env python3
"""
Import card code cache into database
"""
import json
import sqlite3
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def load_card_code_cache(cache_file='card_code_cache.json'):
    """Load card code cache from JSON file"""
    try:
        with open(cache_file, 'r', encoding='utf-8') as f:
            cache = json.load(f)
        logger.info(f"Loaded {len(cache)} card codes from cache")
        return cache
    except Exception as e:
        logger.error(f"Failed to load cache file: {e}")
        return {}

def import_cache_to_db(cache, db_file='ptcg_events.db'):
    """Import cache data into database"""
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()

    # Get current state
    cursor.execute("SELECT COUNT(*) FROM deck_cards WHERE card_code = '' OR card_code IS NULL")
    empty_codes_before = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM deck_cards WHERE card_code != '' AND card_code IS NOT NULL")
    filled_codes_before = cursor.fetchone()[0]

    logger.info(f"Before import: {empty_codes_before} empty codes, {filled_codes_before} filled codes")

    # First, clean up empty entries that have been properly broken down into filled entries
    cursor.execute("""
        DELETE FROM deck_cards
        WHERE (card_code = '' OR card_code IS NULL)
        AND (deck_id, card_name) IN (
            SELECT deck_id, card_name
            FROM deck_cards
            WHERE card_code != '' AND card_code IS NOT NULL
            GROUP BY deck_id, card_name
        )
    """)
    cleaned_up = cursor.rowcount
    if cleaned_up > 0:
        logger.info(f"Cleaned up {cleaned_up} empty entries that had been properly broken down")

    # Update remaining empty code entries with cache data
    updated_count = 0
    cache_hits = 0
    skipped_no_cache = 0

    for card_id_str, card_code in cache.items():
        # Update all rows with this card_id that still have empty card_code
        cursor.execute("""
            UPDATE deck_cards
            SET card_code = ?
            WHERE card_id = ? AND (card_code = '' OR card_code IS NULL)
        """, (card_code, card_id_str))

        if cursor.rowcount > 0:
            updated_count += cursor.rowcount
            cache_hits += 1

    conn.commit()

    # Get final state
    cursor.execute("SELECT COUNT(*) FROM deck_cards WHERE card_code = '' OR card_code IS NULL")
    empty_codes_after = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM deck_cards WHERE card_code != '' AND card_code IS NOT NULL")
    filled_codes_after = cursor.fetchone()[0]

    logger.info(f"After import: {empty_codes_after} empty codes, {filled_codes_after} filled codes")
    logger.info(f"Updated {updated_count} deck card entries from {cache_hits} cache entries")
    logger.info(f"Cleaned up {cleaned_up} duplicate empty entries")

    # Show some examples
    cursor.execute("""
        SELECT card_id, card_name, card_code
        FROM deck_cards
        WHERE card_code != '' AND card_code IS NOT NULL
        ORDER BY id DESC
        LIMIT 10
    """)
    examples = cursor.fetchall()

    print("\n📝 SAMPLE UPDATED ENTRIES:")
    print("-" * 50)
    for card_id, card_name, card_code in examples:
        print(f"ID: {card_id:>8} | {card_name[:25]:<25} | {card_code}")

    conn.close()

    return {
        'updated_count': updated_count,
        'cache_hits': cache_hits,
        'cleaned_up': cleaned_up,
        'empty_before': empty_codes_before,
        'empty_after': empty_codes_after
    }

def main():
    """Main execution"""
    logger.info("Starting card code cache import")

    # Load cache
    cache = load_card_code_cache()
    if not cache:
        logger.error("No cache data loaded, exiting")
        return

    # Import to database
    stats = import_cache_to_db(cache)

    print("\n" + "=" * 60)
    print("CARD CODE CACHE IMPORT SUMMARY")
    print("=" * 60)
    print(f"Cache entries processed: {len(cache)}")
    print(f"Database entries updated: {stats['updated_count']}")
    print(f"Cache hits: {stats['cache_hits']}")
    print(f"Duplicate empty entries cleaned: {stats['cleaned_up']}")
    print(f"Empty codes before: {stats['empty_before']}")
    print(f"Empty codes after: {stats['empty_after']}")
    print(f"Improvement: {stats['empty_before'] - stats['empty_after']} codes filled")
    print("=" * 60)

    logger.info("Card code cache import completed")

if __name__ == "__main__":
    main()