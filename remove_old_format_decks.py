"""
Remove old format decks and events from the database.

This script removes:
1. Decks containing GX, VMAX, V cards, and ヒスイのヘビーボール
2. Events that only have old format decks (no current format decks remaining)
3. All associated data (deck_cards, event_results, players with no remaining decks)

The archived special card decks have been preserved in:
- archive/special_cards/special_decks_20251116_123300.json
- archive/special_cards/special_decks_summary_20251116_123300.txt
"""

import sqlite3
import json
from datetime import datetime

def load_archived_deck_ids():
    """Load deck IDs from the archived special decks JSON file."""
    archive_file = "archive/special_cards/special_decks_20251116_123300.json"
    
    with open(archive_file, 'r', encoding='utf-8') as f:
        archived_decks = json.load(f)
    
    deck_ids = [deck['deck_id'] for deck in archived_decks]
    print(f"Loaded {len(deck_ids)} deck IDs from archive")
    return deck_ids

def get_database_stats(conn):
    """Get current database statistics."""
    cursor = conn.cursor()
    
    stats = {}
    stats['events'] = cursor.execute("SELECT COUNT(*) FROM events").fetchone()[0]
    stats['decks'] = cursor.execute("SELECT COUNT(*) FROM decks").fetchone()[0]
    stats['deck_cards'] = cursor.execute("SELECT COUNT(*) FROM deck_cards").fetchone()[0]
    stats['players'] = cursor.execute("SELECT COUNT(*) FROM players").fetchone()[0]
    stats['event_results'] = cursor.execute("SELECT COUNT(*) FROM event_results").fetchone()[0]
    
    return stats

def remove_old_format_decks(db_path='ptcg_events.db', dry_run=False):
    """
    Remove old format decks and their associated data from the database.
    
    Args:
        db_path: Path to the database file
        dry_run: If True, only show what would be deleted without actually deleting
    """
    # Load archived deck IDs
    deck_ids_to_remove = load_archived_deck_ids()
    
    conn = sqlite3.connect(db_path, timeout=30.0)
    conn.execute("PRAGMA journal_mode=WAL")
    cursor = conn.cursor()
    
    # Get initial stats
    print("\n=== Initial Database Statistics ===")
    initial_stats = get_database_stats(conn)
    for key, value in initial_stats.items():
        print(f"{key}: {value}")
    
    # Get events associated with these decks
    placeholders = ','.join('?' * len(deck_ids_to_remove))
    query = f"""
    SELECT DISTINCT er.event_id
    FROM event_results er
    WHERE er.deck_id IN ({placeholders})
    """
    cursor.execute(query, deck_ids_to_remove)
    event_ids = [row[0] for row in cursor.fetchall()]
    print(f"\nFound {len(event_ids)} events containing old format decks")
    
    # Check which events have ONLY old format decks
    events_to_remove = []
    events_to_keep = []
    
    for event_id in event_ids:
        # Count total decks in this event
        cursor.execute("""
            SELECT COUNT(DISTINCT deck_id)
            FROM event_results
            WHERE event_id = ?
        """, (event_id,))
        total_decks = cursor.fetchone()[0]
        
        # Count old format decks in this event
        query = f"""
            SELECT COUNT(DISTINCT deck_id)
            FROM event_results
            WHERE event_id = ? AND deck_id IN ({placeholders})
        """
        cursor.execute(query, [event_id] + deck_ids_to_remove)
        old_format_decks = cursor.fetchone()[0]
        
        if old_format_decks == total_decks:
            events_to_remove.append(event_id)
        else:
            events_to_keep.append(event_id)
    
    print(f"\nEvents to remove (only old format): {len(events_to_remove)}")
    print(f"Events to keep (mixed format): {len(events_to_keep)}")
    
    # Get detailed counts
    print("\n=== Items to Remove ===")
    
    # Count deck_cards
    query = f"""
        SELECT COUNT(*)
        FROM deck_cards
        WHERE deck_id IN ({placeholders})
    """
    cursor.execute(query, deck_ids_to_remove)
    deck_cards_count = cursor.fetchone()[0]
    print(f"deck_cards entries: {deck_cards_count}")
    
    # Count event_results
    query = f"""
        SELECT COUNT(*)
        FROM event_results
        WHERE deck_id IN ({placeholders})
    """
    cursor.execute(query, deck_ids_to_remove)
    event_results_count = cursor.fetchone()[0]
    print(f"event_results entries: {event_results_count}")
    
    # Count players who only have old format decks
    query = f"""
        SELECT player_id
        FROM players
        WHERE player_id NOT IN (
            SELECT DISTINCT player_id
            FROM event_results
            WHERE deck_id NOT IN ({placeholders})
        )
    """
    cursor.execute(query, deck_ids_to_remove)
    players_to_remove = [row[0] for row in cursor.fetchall()]
    print(f"players (with no current format decks): {len(players_to_remove)}")
    
    print(f"decks: {len(deck_ids_to_remove)}")
    print(f"events: {len(events_to_remove)}")
    
    if dry_run:
        print("\n=== DRY RUN - No changes made ===")
        conn.close()
        return
    
    # Confirm before deletion
    print("\n" + "="*60)
    print("WARNING: This will permanently delete the following:")
    print(f"- {deck_cards_count} deck_cards entries")
    print(f"- {event_results_count} event_results entries")
    print(f"- {len(deck_ids_to_remove)} decks")
    print(f"- {len(players_to_remove)} players")
    print(f"- {len(events_to_remove)} events")
    print("="*60)
    response = input("\nAre you sure you want to proceed? (yes/no): ")
    
    if response.lower() != 'yes':
        print("Operation cancelled")
        conn.close()
        return
    
    # Perform deletions in correct order (respecting foreign keys)
    print("\n=== Removing Old Format Data ===")
    
    # 1. Delete deck_cards
    print("Deleting deck_cards...")
    query = f"DELETE FROM deck_cards WHERE deck_id IN ({placeholders})"
    cursor.execute(query, deck_ids_to_remove)
    print(f"Deleted {cursor.rowcount} deck_cards entries")
    
    # 2. Delete event_results
    print("Deleting event_results...")
    query = f"DELETE FROM event_results WHERE deck_id IN ({placeholders})"
    cursor.execute(query, deck_ids_to_remove)
    print(f"Deleted {cursor.rowcount} event_results entries")
    
    # 3. Delete decks
    print("Deleting decks...")
    query = f"DELETE FROM decks WHERE deck_id IN ({placeholders})"
    cursor.execute(query, deck_ids_to_remove)
    print(f"Deleted {cursor.rowcount} decks")
    
    # 4. Delete players with no remaining decks
    if players_to_remove:
        print("Deleting players with no current format decks...")
        placeholders_players = ','.join('?' * len(players_to_remove))
        query = f"DELETE FROM players WHERE player_id IN ({placeholders_players})"
        cursor.execute(query, players_to_remove)
        print(f"Deleted {cursor.rowcount} players")
    
    # 5. Delete events with only old format decks
    if events_to_remove:
        print("Deleting events with only old format decks...")
        placeholders_events = ','.join('?' * len(events_to_remove))
        query = f"DELETE FROM events WHERE event_id IN ({placeholders_events})"
        cursor.execute(query, events_to_remove)
        print(f"Deleted {cursor.rowcount} events")
    
    # Commit changes
    conn.commit()
    print("\n=== Changes committed successfully ===")
    
    # Get final stats
    print("\n=== Final Database Statistics ===")
    final_stats = get_database_stats(conn)
    for key, value in final_stats.items():
        diff = initial_stats[key] - value
        print(f"{key}: {value} (removed {diff})")
    
    # Optimize database
    print("\n=== Optimizing Database ===")
    print("Running VACUUM...")
    conn.execute("VACUUM")
    print("Running ANALYZE...")
    conn.execute("ANALYZE")
    print("Database optimization complete")
    
    conn.close()
    
    # Create summary report
    summary = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "removed": {
            "decks": len(deck_ids_to_remove),
            "events": len(events_to_remove),
            "players": len(players_to_remove),
            "deck_cards": deck_cards_count,
            "event_results": event_results_count
        },
        "before": initial_stats,
        "after": final_stats
    }
    
    summary_file = f"archive/special_cards/removal_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    print(f"\nSummary saved to: {summary_file}")

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Remove old format decks from database')
    parser.add_argument('--dry-run', action='store_true',
                      help='Show what would be deleted without actually deleting')
    parser.add_argument('--db', default='ptcg_events.db',
                      help='Path to database file (default: ptcg_events.db)')
    
    args = parser.parse_args()
    
    print("="*60)
    print("Remove Old Format Decks from Database")
    print("="*60)
    
    if args.dry_run:
        print("\n*** DRY RUN MODE - No changes will be made ***\n")
    
    remove_old_format_decks(db_path=args.db, dry_run=args.dry_run)

if __name__ == "__main__":
    main()
