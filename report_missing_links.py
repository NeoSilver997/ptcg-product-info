"""
Report on unmapped cards in the bilingual database
"""
import sqlite3
import json

def generate_missing_link_report():
    # Connect to database
    conn_event = sqlite3.connect('ptcg_events.db')
    cursor = conn_event.cursor()
    
    print("=" * 80)
    print("MISSING CARD LINK REPORT")
    print("=" * 80)
    
    # Get unmapped cards sorted by usage
    cursor.execute("""
        SELECT 
            dc.card_id,
            dc.card_name,
            dc.card_code,
            COUNT(DISTINCT dc.deck_id) as deck_count
        FROM deck_cards dc
        LEFT JOIN card_mappings cm ON dc.card_id = cm.event_card_id
        WHERE cm.event_card_id IS NULL 
        AND dc.card_code IS NOT NULL
        GROUP BY dc.card_id
        ORDER BY deck_count DESC
        LIMIT 50
    """)
    unmapped = cursor.fetchall()
    
    print("\nTop 50 Unmapped Cards (by deck usage):\n")
    print(f"{'Rank':<6}{'Card Name':<40}{'Card Code':<20}{'Decks':<10}")
    print("-" * 80)
    
    for i, (card_id, name, code, decks) in enumerate(unmapped, 1):
        print(f"{i:<6}{name[:39]:<40}{code:<20}{decks:<10}")
    
    # Get statistics
    cursor.execute("""
        SELECT COUNT(DISTINCT dc.card_id)
        FROM deck_cards dc
        LEFT JOIN card_mappings cm ON dc.card_id = cm.event_card_id
        WHERE cm.event_card_id IS NULL
    """)
    total_unmapped_cards = cursor.fetchone()[0]
    
    cursor.execute("""
        SELECT COUNT(*)
        FROM deck_cards dc
        LEFT JOIN card_mappings cm ON dc.card_id = cm.event_card_id
        WHERE cm.event_card_id IS NULL
    """)
    total_unmapped_entries = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(DISTINCT card_id) FROM deck_cards")
    total_unique_cards = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM deck_cards")
    total_entries = cursor.fetchone()[0]
    
    # Get unmapped cards by reason
    print("\n" + "=" * 80)
    print("UNMAPPED CARDS BY CATEGORY")
    print("=" * 80)
    
    # Basic Energy cards
    cursor.execute("""
        SELECT dc.card_name, COUNT(DISTINCT dc.deck_id) as deck_count
        FROM deck_cards dc
        LEFT JOIN card_mappings cm ON dc.card_id = cm.event_card_id
        WHERE cm.event_card_id IS NULL
        AND dc.card_name LIKE '%基本%エネルギー'
        GROUP BY dc.card_name
        ORDER BY deck_count DESC
        LIMIT 10
    """)
    basic_energy = cursor.fetchall()
    
    print("\n📦 Basic Energy Cards (unmapped):")
    for name, count in basic_energy:
        print(f"  {name:<35} - {count:>5} decks")
    
    # ACE SPEC cards
    cursor.execute("""
        SELECT dc.card_name, dc.card_code, COUNT(DISTINCT dc.deck_id) as deck_count
        FROM deck_cards dc
        LEFT JOIN card_mappings cm ON dc.card_id = cm.event_card_id
        WHERE cm.event_card_id IS NULL
        AND dc.card_code = 'ACE SPEC'
        GROUP BY dc.card_name
        ORDER BY deck_count DESC
    """)
    ace_spec = cursor.fetchall()
    
    print("\n⭐ ACE SPEC Cards (unmapped):")
    for name, code, count in ace_spec:
        print(f"  {name:<35} - {count:>5} decks")
    
    # Promo cards
    cursor.execute("""
        SELECT dc.card_name, dc.card_code, COUNT(DISTINCT dc.deck_id) as deck_count
        FROM deck_cards dc
        LEFT JOIN card_mappings cm ON dc.card_id = cm.event_card_id
        WHERE cm.event_card_id IS NULL
        AND dc.card_code LIKE 'SV-P%'
        GROUP BY dc.card_name
        ORDER BY deck_count DESC
        LIMIT 15
    """)
    promo = cursor.fetchall()
    
    print("\n🎁 Promo Cards (SV-P, unmapped):")
    for name, code, count in promo:
        print(f"  {name:<35} ({code:<15}) - {count:>5} decks")
    
    # Other unmapped (non-energy, non-ACE, non-promo)
    cursor.execute("""
        SELECT dc.card_name, dc.card_code, COUNT(DISTINCT dc.deck_id) as deck_count
        FROM deck_cards dc
        LEFT JOIN card_mappings cm ON dc.card_id = cm.event_card_id
        WHERE cm.event_card_id IS NULL
        AND dc.card_name NOT LIKE '%基本%エネルギー'
        AND dc.card_code != 'ACE SPEC'
        AND dc.card_code NOT LIKE 'SV-P%'
        AND dc.card_code IS NOT NULL
        GROUP BY dc.card_name
        ORDER BY deck_count DESC
        LIMIT 20
    """)
    other = cursor.fetchall()
    
    print("\n❓ Other Unmapped Cards:")
    for name, code, count in other:
        print(f"  {name:<35} ({code:<15}) - {count:>5} decks")
    
    # Summary statistics
    print("\n" + "=" * 80)
    print("SUMMARY STATISTICS")
    print("=" * 80)
    print(f"Total Unmapped Unique Cards: {total_unmapped_cards:,}")
    print(f"Total Unmapped Card Entries: {total_unmapped_entries:,}")
    print(f"Total Unique Cards: {total_unique_cards:,}")
    print(f"Total Card Entries: {total_entries:,}")
    print(f"Unmapped Card Rate: {total_unmapped_cards / total_unique_cards * 100:.2f}%")
    print(f"Unmapped Entry Rate: {total_unmapped_entries / total_entries * 100:.2f}%")
    
    # Expansion analysis
    cursor.execute("""
        SELECT 
            SUBSTR(dc.card_code, 1, INSTR(dc.card_code || ' ', ' ') - 1) as expansion,
            COUNT(DISTINCT dc.card_id) as unique_cards,
            COUNT(DISTINCT dc.deck_id) as deck_count
        FROM deck_cards dc
        LEFT JOIN card_mappings cm ON dc.card_id = cm.event_card_id
        WHERE cm.event_card_id IS NULL
        AND dc.card_code IS NOT NULL
        AND dc.card_code != 'ACE SPEC'
        GROUP BY expansion
        ORDER BY unique_cards DESC
        LIMIT 15
    """)
    expansions = cursor.fetchall()
    
    print("\n" + "=" * 80)
    print("UNMAPPED CARDS BY EXPANSION")
    print("=" * 80)
    print(f"{'Expansion':<15}{'Unique Cards':<15}{'Total Deck Usage':<20}")
    print("-" * 80)
    for exp, cards, decks in expansions:
        print(f"{exp:<15}{cards:<15}{decks:<20}")
    
    conn_event.close()
    print("\n" + "=" * 80)
    print("Report generation complete!")
    print("=" * 80)

if __name__ == "__main__":
    generate_missing_link_report()
