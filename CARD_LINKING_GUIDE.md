# Card Linking Documentation

## Overview

Successfully linked Japanese Pokemon TCG event cards with Chinese card database using expansion codes and collector numbers.

## Linking Statistics

- **Total Event Cards**: 2,692 unique cards
- **Successfully Mapped**: 1,564 cards (58.1% coverage)
- **Unmapped Cards**: 1,128 cards (41.9%)

### Why 58% Coverage?

The unmapped cards are primarily:
1. **ACE SPEC Cards**: Special cards without standard collector numbers
2. **Basic Energy Cards**: Often don't have set-specific codes
3. **Promo Cards** (SV-P series): May not be in main database yet
4. **Recent Releases**: MA (Master Art) series and new expansions
5. **Special Sets**: Limited edition or promotional sets

## Database Schema

### New Table: `card_mappings`

Created in `ptcg_events.db` to store the linking relationships:

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Auto-increment primary key |
| event_card_id | TEXT | Card ID from event database (Japanese) |
| event_card_name | TEXT | Japanese card name (e.g., ピカチュウex) |
| event_card_code | TEXT | Card code (e.g., SV8 033/106) |
| main_card_id | INTEGER | Card ID from main database |
| main_card_name | TEXT | Chinese card name (e.g., 皮卡丘ex) |
| main_collector_number | TEXT | Collector number (e.g., 033) |
| main_expansion_code | TEXT | Expansion code (e.g., SV8) |
| match_confidence | TEXT | Matching confidence level |
| created_at | TIMESTAMP | When mapping was created |

## Linking Algorithm

```python
# Parse card code: "SV8a 120/187" → expansion="SV8a", number="120"
expansion_code, collector_number = parse_card_code(card_code)

# Find matching expansion in main database
expansion_id = expansion_map[expansion_code]['id']

# Match by expansion_id AND collector_number
SELECT id, name, collector_number
FROM cards
WHERE expansion_id = ? AND collector_number = ?
```

## Top Mapped Expansions

| Expansion | Mapped Cards |
|-----------|--------------|
| SV8a | 244 cards |
| SV4a | 157 cards |
| SV6 | 62 cards |
| SV9 | 52 cards |
| SVM | 49 cards |
| SV10 | 48 cards |
| M1S | 44 cards |
| SV8 | 43 cards |
| M1L | 43 cards |
| SV9a | 42 cards |

## Usage Examples

### 1. Query Popular Cards (Bilingual)

```python
from query_linked_cards import LinkedCardQuery

query = LinkedCardQuery()
query.connect()

# Get top 30 most used cards with translations
popular = query.get_popular_cards_bilingual(30)
for card in popular:
    print(f"{card['japanese_name']} → {card['chinese_name']}")
    print(f"  Used in {card['deck_count']} decks")
```

### 2. Get Deck with Translations

```python
# Get winning deck with card translations
deck = query.get_deck_with_translations('k5F5Fk-hRH7Hn-VvFfkV')

print(f"Player: {deck['player_name']}")
for card in deck['cards']:
    print(f"{card['quantity']}x {card['japanese_name']} → {card['chinese_name']}")
```

### 3. Search Cards

```python
# Search by Japanese name
results = query.search_cards('ピカチュウ', search_japanese=True)

# Search by Chinese name
results = query.search_cards('皮卡丘', search_chinese=True)

# Search both languages
results = query.search_cards('ex', search_japanese=True, search_chinese=True)
```

### 4. Get Full Card Details

```python
# Get complete card information from main database
card_details = query.get_card_full_details(main_card_id=1234)

print(f"Name: {card_details['name']}")
print(f"HP: {card_details['hp']}")
print(f"Type: {card_details['attribute']}")
print(f"Skills: {card_details['skills']}")
print(f"Abilities: {card_details['abilities']}")
```

## SQL Query Examples

### Get All Mappings for a Deck

```sql
SELECT 
    dc.card_name as japanese_name,
    cm.main_card_name as chinese_name,
    dc.card_code,
    dc.quantity
FROM deck_cards dc
LEFT JOIN card_mappings cm ON dc.card_id = cm.event_card_id
WHERE dc.deck_id = 'DECK_ID_HERE'
ORDER BY dc.card_name;
```

### Find Most Used Cards with Both Names

```sql
SELECT 
    dc.card_name as japanese_name,
    cm.main_card_name as chinese_name,
    COUNT(DISTINCT dc.deck_id) as deck_count,
    SUM(dc.quantity) as total_copies
FROM deck_cards dc
LEFT JOIN card_mappings cm ON dc.card_id = cm.event_card_id
WHERE dc.card_name NOT LIKE '%エネルギー%'
GROUP BY dc.card_id
ORDER BY deck_count DESC
LIMIT 50;
```

### Get Full Card Details via Mapping

```sql
SELECT 
    cm.event_card_name as japanese_name,
    c.name as chinese_name,
    c.hp,
    c.attribute,
    e.name as expansion_name,
    i.name as illustrator
FROM card_mappings cm
JOIN cards c ON cm.main_card_id = c.id
LEFT JOIN expansions e ON c.expansion_id = e.id
LEFT JOIN illustrators i ON c.illustrator_id = i.id
WHERE cm.event_card_name LIKE '%ピカチュウ%';
```

### Export Deck with Translations

```sql
SELECT 
    d.deck_id,
    d.rank,
    e.event_date,
    p.player_name,
    dc.quantity || 'x ' || dc.card_name as japanese_card,
    dc.quantity || 'x ' || cm.main_card_name as chinese_card
FROM decks d
JOIN deck_cards dc ON d.deck_id = dc.deck_id
JOIN events e ON d.event_id = e.event_id
LEFT JOIN players p ON d.player_id = p.player_id
LEFT JOIN card_mappings cm ON dc.card_id = cm.event_card_id
WHERE d.rank = '1位'
ORDER BY e.event_date DESC, dc.card_name;
```

## Files Created

### Core Scripts

1. **`link_cards.py`** - Main linking script
   - Parses card codes from event database
   - Matches with main database by expansion_id + collector_number
   - Creates `card_mappings` table
   - Exports mappings to JSON

2. **`query_linked_cards.py`** - Query utility
   - Bilingual card search
   - Deck translation
   - Popular card analysis
   - Full card details retrieval

3. **`check_codes.py`** - Expansion code analyzer
   - Verifies expansion codes in both databases
   - Shows mapping distribution

### Exported Data

- **`exports/card_mappings.json`** - Complete mapping data
  ```json
  [
    {
      "event_card_id": "46781",
      "event_card_name": "ドラパルトex",
      "event_card_code": "SV8a 120/187",
      "main_card_id": 1234,
      "main_card_name": "多龍巴魯托ex",
      "main_collector_number": "120",
      "main_expansion_code": "SV8a",
      "match_confidence": "high"
    }
  ]
  ```

## Sample Mappings

| Japanese Name | Chinese Name | Card Code | Usage |
|---------------|--------------|-----------|-------|
| ピカチュウex | 皮卡丘ex | SV8 033/106 | 215 decks |
| リザードンex | 噴火龍ex | SV4a 118/190 | 189 decks |
| ミュウツーex | 超夢ex | SV4a 193/190 | 156 decks |
| ルナトーン | 月石 | M1L 026/063 | 1237 decks |
| ソルロック | 太陽岩 | M1L 027/063 | 1237 decks |
| ヒカリ | 小光 | M2 077/080 | 1162 decks |

## Improving Coverage

To improve the 58% coverage:

1. **Add Missing Expansions**: Import newer sets (MA, recent SV series) to main database
2. **Handle ACE SPEC Cards**: Create special mapping for ACE SPEC cards
3. **Promo Cards**: Map SV-P promotional cards manually or via web scraping
4. **Basic Energy**: Create generic mappings for basic energy cards
5. **Manual Corrections**: Review and manually map high-usage unmapped cards

## Integration Benefits

### For Deck Analysis
- Show deck lists with familiar Chinese names
- Cross-reference tournament performance with card database
- Analyze meta trends with full card details

### For Card Evaluation
- See real tournament usage statistics
- Correlate card ratings with competitive performance
- Identify undervalued/overvalued cards

### For Players
- Build decks using Chinese card names
- Find Japanese tournament equivalents
- Understand competitive meta in their language

## Technical Notes

- **Matching Method**: Expansion code + Collector number (exact match)
- **Confidence Level**: Currently all matches are "high" confidence
- **Performance**: Linking ~2,150 cards takes <1 second
- **Database Size**: card_mappings table adds ~200 KB to event database

## Future Enhancements

1. **Fuzzy Name Matching**: Match unmapped cards by name similarity
2. **Card Image Comparison**: Use image hashes to match cards
3. **Auto-update**: Re-link when new cards added to main database
4. **Confidence Scoring**: Add multiple confidence levels based on matching method
5. **Translation API**: Integrate Google Translate for unmapped cards
6. **Web Interface**: Create web UI for browsing bilingual card data

---

**Last Updated**: November 13, 2025
**Coverage**: 58.1% (1,564 / 2,692 cards)
**Script**: `link_cards.py`
