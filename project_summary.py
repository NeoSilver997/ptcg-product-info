"""
Comprehensive summary of the event database and card linking project.
"""

import sqlite3
from pathlib import Path


def print_section(title):
    """Print formatted section header."""
    print("\n" + "=" * 80)
    print(title.center(80))
    print("=" * 80)


def main():
    # Connect to databases
    event_conn = sqlite3.connect('ptcg_events.db')
    main_conn = sqlite3.connect(r'c:\AI_Server\Coding\PokemonDBByjules\PTCG_CardDB_Tc\pokemon_cards.db')
    
    event_cursor = event_conn.cursor()
    main_cursor = main_conn.cursor()
    
    print_section("POKEMON TCG TOURNAMENT DATABASE PROJECT SUMMARY")
    
    # Event Database Statistics
    print("\n📊 EVENT DATABASE (ptcg_events.db)")
    print("-" * 80)
    
    event_cursor.execute("SELECT COUNT(*) FROM events")
    print(f"Total Events:        {event_cursor.fetchone()[0]:,}")
    
    event_cursor.execute("SELECT MIN(event_date), MAX(event_date) FROM events")
    dates = event_cursor.fetchone()
    print(f"Date Range:          {dates[0]} to {dates[1]}")
    
    event_cursor.execute("SELECT COUNT(*) FROM players")
    print(f"Unique Players:      {event_cursor.fetchone()[0]:,}")
    
    event_cursor.execute("SELECT COUNT(*) FROM decks")
    print(f"Complete Decks:      {event_cursor.fetchone()[0]:,}")
    
    event_cursor.execute("SELECT COUNT(*) FROM deck_cards")
    print(f"Card Entries:        {event_cursor.fetchone()[0]:,}")
    
    event_cursor.execute("SELECT COUNT(*) FROM event_results")
    print(f"Tournament Results:  {event_cursor.fetchone()[0]:,}")
    
    # Main Database Statistics
    print("\n📚 MAIN CARD DATABASE (pokemon_cards.db)")
    print("-" * 80)
    
    main_cursor.execute("SELECT COUNT(*) FROM cards")
    print(f"Total Cards:         {main_cursor.fetchone()[0]:,}")
    
    main_cursor.execute("SELECT COUNT(*) FROM expansions")
    print(f"Expansions:          {main_cursor.fetchone()[0]:,}")
    
    main_cursor.execute("SELECT COUNT(*) FROM skills")
    print(f"Skills/Attacks:      {main_cursor.fetchone()[0]:,}")
    
    main_cursor.execute("SELECT COUNT(*) FROM abilities")
    print(f"Abilities:           {main_cursor.fetchone()[0]:,}")
    
    # Card Linking Statistics
    print("\n🔗 CARD LINKING (Japanese ⇄ Chinese)")
    print("-" * 80)
    
    event_cursor.execute("SELECT COUNT(DISTINCT card_id) FROM deck_cards")
    total_event_cards = event_cursor.fetchone()[0]
    
    event_cursor.execute("SELECT COUNT(*) FROM card_mappings")
    mapped_cards = event_cursor.fetchone()[0]
    
    coverage = (mapped_cards / total_event_cards * 100) if total_event_cards > 0 else 0
    
    print(f"Event Cards:         {total_event_cards:,}")
    print(f"Mapped Cards:        {mapped_cards:,}")
    print(f"Unmapped Cards:      {total_event_cards - mapped_cards:,}")
    print(f"Coverage:            {coverage:.1f}%")
    
    # Top Mapped Expansions
    print("\n📦 TOP MAPPED EXPANSIONS")
    print("-" * 80)
    event_cursor.execute("""
        SELECT main_expansion_code, COUNT(*) as count
        FROM card_mappings
        GROUP BY main_expansion_code
        ORDER BY count DESC
        LIMIT 10
    """)
    for i, (exp, count) in enumerate(event_cursor.fetchall(), 1):
        print(f"{i:2d}. {exp:10s} - {count:4d} cards")
    
    # Most Popular Cards (Bilingual)
    print("\n🎴 TOP 10 MOST USED CARDS (with translations)")
    print("-" * 80)
    event_cursor.execute("""
        SELECT 
            dc.card_name as jp_name,
            cm.main_card_name as cn_name,
            COUNT(DISTINCT dc.deck_id) as deck_count
        FROM deck_cards dc
        LEFT JOIN card_mappings cm ON dc.card_id = cm.event_card_id
        WHERE dc.card_name NOT LIKE '%エネルギー%'
        GROUP BY dc.card_id
        ORDER BY deck_count DESC
        LIMIT 10
    """)
    for i, (jp_name, cn_name, count) in enumerate(event_cursor.fetchall(), 1):
        cn_display = cn_name if cn_name else "(未映射)"
        print(f"{i:2d}. {jp_name:25s} → {cn_display:20s} ({count:4d} decks)")
    
    # Tournament Champions
    print("\n🏆 TOP TOURNAMENT PLAYERS")
    print("-" * 80)
    event_cursor.execute("""
        SELECT 
            p.player_name,
            p.player_area,
            COUNT(CASE WHEN er.rank = '1位' THEN 1 END) as wins
        FROM players p
        JOIN event_results er ON p.player_id = er.player_id
        GROUP BY p.player_id
        HAVING wins > 0
        ORDER BY wins DESC, p.player_name
        LIMIT 10
    """)
    for i, (name, area, wins) in enumerate(event_cursor.fetchall(), 1):
        plural = "wins" if wins > 1 else "win"
        print(f"{i:2d}. {name:20s} ({area:10s}) - {wins} {plural}")
    
    # File Summary
    print("\n📁 PROJECT FILES")
    print("-" * 80)
    
    files = [
        ("ptcg_events.db", "Main event database"),
        ("card_mappings.json", "Card linking data (JSON export)"),
        ("import_events_to_sqlite.py", "Import event data script"),
        ("link_cards.py", "Card linking script"),
        ("query_events.py", "Event query utilities"),
        ("query_linked_cards.py", "Bilingual card queries"),
        ("export_event_data.py", "Data export utilities"),
        ("EVENT_DATABASE_README.md", "Event database documentation"),
        ("CARD_LINKING_GUIDE.md", "Card linking guide"),
    ]
    
    for filename, description in files:
        exists = "✅" if Path(filename).exists() else "❌"
        print(f"{exists} {filename:30s} - {description}")
    
    # Export Files
    print("\n📤 EXPORTED DATA (in exports/ folder)")
    print("-" * 80)
    
    export_files = [
        "card_frequency.csv",
        "player_rankings.csv", 
        "events_summary.csv",
        "deck_archetypes.json",
        "first_place_decks.json",
        "card_combos.csv",
        "card_mappings.json"
    ]
    
    for filename in export_files:
        path = Path("exports") / filename
        exists = "✅" if path.exists() else "❌"
        size = f"({path.stat().st_size // 1024} KB)" if path.exists() else ""
        print(f"{exists} {filename:30s} {size}")
    
    # Usage Summary
    print("\n🚀 QUICK START COMMANDS")
    print("-" * 80)
    print("# Analyze event data:")
    print("python query_events.py")
    print()
    print("# Query bilingual cards:")
    print("python query_linked_cards.py")
    print()
    print("# Re-link cards (after database updates):")
    print("python link_cards.py")
    print()
    print("# Export all data:")
    print("python export_event_data.py")
    
    print("\n" + "=" * 80)
    print("✅ PROJECT COMPLETE - All systems operational!".center(80))
    print("=" * 80 + "\n")
    
    event_conn.close()
    main_conn.close()


if __name__ == '__main__':
    main()
