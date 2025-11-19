"""
Final Accurate Coverage Statistics
==================================
Calculate accurate coverage metrics.
"""

import sqlite3

EVENT_DB = "ptcg_events.db"

conn = sqlite3.connect(EVENT_DB)
cursor = conn.cursor()

print("="*80)
print("FINAL CARD MAPPING COVERAGE ANALYSIS")
print("="*80)

# Get distinct card_code + card_name combinations
cursor.execute("""
    SELECT COUNT(DISTINCT card_code || '|' || card_name) 
    FROM deck_cards
""")
total_unique_cards = cursor.fetchone()[0]

# Get distinct mapped card_code + card_name combinations
cursor.execute("""
    SELECT COUNT(DISTINCT dc.card_code || '|' || dc.card_name)
    FROM deck_cards dc
    JOIN card_mappings cm ON dc.card_code = cm.event_card_code 
        AND dc.card_name = cm.event_card_name
""")
mapped_unique_cards = cursor.fetchone()[0]

# Calculate accurate coverage
accurate_coverage = (mapped_unique_cards / total_unique_cards * 100) if total_unique_cards > 0 else 0

print(f"\nAccurate Coverage Metrics:")
print(f"  Total Unique Card Variants:  {total_unique_cards:5d}")
print(f"  Mapped Card Variants:        {mapped_unique_cards:5d}")
print(f"  Unmapped Card Variants:      {total_unique_cards - mapped_unique_cards:5d}")
print(f"  Accurate Coverage:           {accurate_coverage:5.2f}%")

# Get total deck usage coverage
cursor.execute("""
    SELECT COUNT(*) FROM deck_cards
""")
total_card_instances = cursor.fetchone()[0]

cursor.execute("""
    SELECT COUNT(*)
    FROM deck_cards dc
    JOIN card_mappings cm ON dc.card_code = cm.event_card_code 
        AND dc.card_name = cm.event_card_name
""")
mapped_card_instances = cursor.fetchone()[0]

usage_coverage = (mapped_card_instances / total_card_instances * 100) if total_card_instances > 0 else 0

print(f"\nDeck Usage Coverage:")
print(f"  Total Card Instances in Decks: {total_card_instances:7d}")
print(f"  Mapped Card Instances:         {mapped_card_instances:7d}")
print(f"  Unmapped Card Instances:       {total_card_instances - mapped_card_instances:7d}")
print(f"  Usage Coverage:                {usage_coverage:5.2f}%")

# Show unmapped cards
print(f"\n{'='*80}")
print("REMAINING UNMAPPED CARDS")
print("="*80)

cursor.execute("""
    SELECT 
        dc.card_name,
        dc.card_code,
        COUNT(DISTINCT dc.deck_id) as deck_count,
        COUNT(*) as total_copies
    FROM deck_cards dc
    LEFT JOIN card_mappings cm ON dc.card_code = cm.event_card_code 
        AND dc.card_name = cm.event_card_name
    WHERE cm.main_card_id IS NULL
    GROUP BY dc.card_name, dc.card_code
    ORDER BY deck_count DESC
""")

unmapped = cursor.fetchall()

print(f"\nTotal: {len(unmapped)} unmapped card variants\n")

for i, (name, code, deck_count, total_copies) in enumerate(unmapped, 1):
    code_display = code if code else "[NO CODE]"
    print(f"{i:2d}. {name:35s} {code_display:20s} ({deck_count:3d} decks, {total_copies:4d} copies)")

print("\n" + "="*80)
print("COVERAGE IMPROVEMENT SUMMARY")
print("="*80)
print(f"""
Starting Coverage:     58.10% (initial linking by expansion code)
After MA/SVN Import:   61.44% (+3.34%)
After Special Fixes:   85.80% (+24.36%)
After Name Matching:   {accurate_coverage:.2f}% (+{accurate_coverage - 85.80:.2f}%)

Total Improvement:     +{accurate_coverage - 58.10:.2f} percentage points

Deck Usage Coverage:   {usage_coverage:.2f}%
  (This means {usage_coverage:.2f}% of all card slots in tournament decks are mapped)
""")

conn.close()
