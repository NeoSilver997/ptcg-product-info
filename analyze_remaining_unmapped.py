"""
Analyze Remaining Unmapped Cards
=================================
After importing MA and SVN expansions, check what's still unmapped.
"""

import sqlite3
import json
from collections import Counter

EVENT_DB = "ptcg_events.db"

conn = sqlite3.connect(EVENT_DB)
cursor = conn.cursor()

# Get unmapped cards
query = """
SELECT dc.card_code, dc.card_name, COUNT(DISTINCT dc.deck_id) as deck_count
FROM deck_cards dc
LEFT JOIN card_mappings cm ON dc.card_code = cm.event_card_code
WHERE cm.main_card_id IS NULL
GROUP BY dc.card_code, dc.card_name
ORDER BY deck_count DESC
"""

cursor.execute(query)
unmapped = cursor.fetchall()

print("="*70)
print("REMAINING UNMAPPED CARDS ANALYSIS")
print("="*70)
print(f"\nTotal unmapped cards: {len(unmapped)}")

# Analyze by expansion
expansion_counts = Counter()
for card_code, name, count in unmapped:
    expansion = card_code.split()[0] if ' ' in card_code else 'UNKNOWN'
    expansion_counts[expansion] += 1

print(f"\nUnmapped cards by expansion:")
print("-" * 70)
for expansion, count in expansion_counts.most_common(15):
    print(f"  {expansion:15s}: {count:4d} cards")

print("\n" + "="*70)
print("TOP 30 MOST-USED UNMAPPED CARDS")
print("="*70)
for i, (card_code, name, deck_count) in enumerate(unmapped[:30], 1):
    print(f"{i:2d}. {card_code:20s} - {name:40s} ({deck_count:4d} decks)")

# Check for patterns
print("\n" + "="*70)
print("SPECIAL PATTERNS")
print("="*70)

ace_specs = [c for c in unmapped if 'ACE' in c[0] or 'SPEC' in c[0]]
promos = [c for c in unmapped if 'SV-P' in c[0] or 'SVOD' in c[0]]

print(f"\nACE SPEC cards: {len(ace_specs)}")
for card_code, name, deck_count in ace_specs[:5]:
    print(f"  {card_code:20s} - {name:40s} ({deck_count} decks)")

print(f"\nPromo cards (SV-P, SVOD): {len(promos)}")
for card_code, name, deck_count in promos[:5]:
    print(f"  {card_code:20s} - {name:40s} ({deck_count} decks)")

conn.close()
