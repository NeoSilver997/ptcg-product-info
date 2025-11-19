# Pokemon TCG Event Database & Card Linking Project

## Overview

Comprehensive Pokemon TCG tournament database with bilingual card mapping (Japanese ⇄ Chinese) for competitive meta analysis.

## 📊 Project Statistics

### Event Database
- **427 Tournaments** (Oct 5 - Nov 11, 2025)
- **5,677 Unique Players**
- **5,640 Complete Decks** (60 cards each)
- **159,137 Card Entries**
- **5,797 Tournament Results**

### Card Linking
- **2,692 Unique Event Cards** (Japanese names)
- **1,564 Successfully Mapped** to Chinese database (58.1% coverage)
- **Link Method**: Expansion code + Collector number matching

### Main Card Database
- **4,858 Total Cards** (Chinese names)
- **103 Expansions**
- **6,673 Skills/Attacks**
- **779 Abilities**

### Web Interface (Calendar View)
```bash
cd c:\AI_Server\Coding\ptcg-product-info\manual-linking-web
node server.js
```
Then open http://localhost:3000 in your browser to:
- Browse tournament calendar
- View deck details with card images
- See bilingual card information
- Analyze tournament results

### Test Card Type Detection (Python)
```python
import sqlite3

event_conn = sqlite3.connect('ptcg_events.db')
event_cursor = event_conn.cursor()

# Get a sample deck with energy cards
event_cursor.execute('SELECT deck_id FROM decks LIMIT 1')
deck_result = event_cursor.fetchone()
deck_id = deck_result[0]

print('Testing deck:', deck_id)

# Get cards from this deck
event_cursor.execute('SELECT card_name, card_code, quantity FROM deck_cards WHERE deck_id = ? ORDER BY card_name', (deck_id,))
cards = event_cursor.fetchall()

print('Cards in deck:')
for card in cards:
    card_name, card_code, quantity = card
    card_type = None
    
    # Simulate the server.js logic for card type detection
    if 'エネルギー' in card_name:
        # Check if it's basic energy (contains '基本') or special energy
        if '基本' in card_name or (card_code and '基本' in card_code):
            card_type = '基本能量'
        else:
            card_type = '特殊能量'
    elif '博士' in card_name or 'サポート' in card_name:
        card_type = '支援者'
    elif 'スタジアム' in card_name:
        card_type = '競技場'
    else:
        card_type = '其他'
    
    print(f'  {card_name} | {card_code} | {quantity}x | Type: {card_type}')

event_conn.close()
```

### Analyze Event Data
```bash
python query_events.py
```
Shows:
- Recent tournaments
- Top players by wins
- Most popular cards
- Recent winning decks

### Query Bilingual Cards
```bash
python query_linked_cards.py
```
Shows:
- Popular cards with Japanese/Chinese names
- Deck translations
- Card search functionality

### Re-link Cards
```bash
python link_cards.py
```
Updates card mappings between databases.

### Export All Data
```bash
python export_event_data.py
```
Exports to CSV/JSON in `exports/` folder.

## 📁 Project Structure

```
ptcg-product-info/
├── ptcg_events.db              # Main event database (SQLite)
├── import_events_to_sqlite.py  # Import event JSON to database
├── link_cards.py               # Link Japanese ⇄ Chinese cards
├── query_events.py             # Event analysis queries
├── query_linked_cards.py       # Bilingual card queries
├── export_event_data.py        # Data export utilities
├── project_summary.py          # Comprehensive project summary
│
├── event_data/                 # Source JSON files (427 events)
│   ├── event_794997_2025-10-05/
│   │   ├── event_info.json
│   │   ├── deck_1st_*.json
│   │   └── deck_2nd_*.json
│   └── ...
│
├── exports/                    # Exported analysis data
│   ├── card_frequency.csv      # Card usage statistics
│   ├── player_rankings.csv     # Player performance
│   ├── events_summary.csv      # Event listings
│   ├── deck_archetypes.json    # Top deck compositions
│   ├── first_place_decks.json  # Winning deck lists
│   ├── card_combos.csv         # Common card pairs
│   └── card_mappings.json      # Japanese ⇄ Chinese mappings
│
└── docs/
    ├── EVENT_DATABASE_README.md      # Database documentation
    ├── CARD_LINKING_GUIDE.md         # Card linking guide
    └── EVENT_IMPORT_SUMMARY.md       # Import summary
```

## 🔗 Card Linking System

### How It Works

1. **Parse Card Code**: Extract expansion and collector number
   ```
   "SV8a 120/187" → expansion="SV8a", number="120"
   ```

2. **Match in Main Database**: Find card by expansion_id + collector_number
   ```sql
   SELECT id, name FROM cards 
   WHERE expansion_id = (SELECT id FROM expansions WHERE code = 'SV8a')
   AND collector_number = '120'
   ```

3. **Store Mapping**: Save Japanese ⇄ Chinese relationship
   ```
   ドラパルトex (SV8a 120/187) → 多龍巴魯托ex
   ```

### Coverage by Expansion

| Expansion | Mapped Cards |
|-----------|--------------|
| SV8a | 244 cards |
| SV4a | 157 cards |
| SV6 | 62 cards |
| SV9 | 52 cards |
| SVM | 49 cards |

## 📚 Database Schema

### Event Database Tables

**events** - Tournament information
- event_id, event_date, event_host, event_location

**players** - Player profiles
- player_id, player_name, player_area

**event_results** - Tournament placements
- event_id, player_id, rank, points, deck_id

**decks** - Deck metadata
- deck_id, event_id, player_id, rank

**deck_cards** - Individual cards (60 per deck)
- deck_id, card_id, card_name, card_code, quantity

**card_mappings** - Japanese ⇄ Chinese linking
- event_card_id, event_card_name, main_card_id, main_card_name

## 🎴 Top Cards (Bilingual)

| Japanese Name | Chinese Name | Usage |
|---------------|--------------|-------|
| ルナトーン | 月石 | 1,237 decks |
| ソルロック | 太陽岩 | 1,237 decks |
| ヒカリ | 小光 | 1,162 decks |
| リーリエの決心 | 老大的指令 | 1,298 decks |
| なかよしポフィン | 好友寶芬 | 1,006 decks |

## 🏆 Tournament Analysis

### Top Players
1. **カドワキ** (Tokyo) - 2 tournament wins
2. Multiple players with 1 win and consistent top-3 finishes

### Meta Insights
- No single dominant archetype
- Regional diversity across Japan
- Strong support card presence (Nest Ball, Bowl Town)
- Balanced meta with various Pokemon-ex strategies

## 🔧 API Examples

### Python API

```python
from query_linked_cards import LinkedCardQuery

query = LinkedCardQuery()
query.connect()

# Get popular cards with both names
cards = query.get_popular_cards_bilingual(30)

# Search by name
results = query.search_cards('ピカチュウ', search_japanese=True)
results = query.search_cards('皮卡丘', search_chinese=True)

# Get deck with translations
deck = query.get_deck_with_translations('deck_id_here')

# Get full card details
details = query.get_card_full_details(card_id=1234)

query.close()
```

### SQL Queries

```sql
-- Get all mappings for a deck
SELECT 
    dc.card_name as japanese,
    cm.main_card_name as chinese,
    dc.quantity
FROM deck_cards dc
LEFT JOIN card_mappings cm ON dc.card_id = cm.event_card_id
WHERE dc.deck_id = ?;

-- Find most used cards with translations
SELECT 
    dc.card_name as japanese,
    cm.main_card_name as chinese,
    COUNT(DISTINCT dc.deck_id) as usage
FROM deck_cards dc
LEFT JOIN card_mappings cm ON dc.card_id = cm.event_card_id
GROUP BY dc.card_id
ORDER BY usage DESC;
```

## 📈 Use Cases

### For Competitive Players
- Analyze winning deck compositions
- Track meta trends over time
- Find Chinese equivalents of Japanese cards
- Study tournament-proven strategies

### For Deck Builders
- See real tournament performance data
- Identify popular card combinations
- Build decks with both Japanese/Chinese cards
- Optimize based on competitive results

### For Data Analysts
- Meta game evolution tracking
- Regional playstyle differences
- Card usage correlations
- Predictive modeling for tournament success

### For Collectors/Traders
- Identify high-demand tournament cards
- Track card value based on competitive usage
- Understand meta-driven price changes
- Find equivalent cards across languages

## 🔄 Data Updates

### Import New Events
```bash
# Place new event folders in event_data/
python import_events_to_sqlite.py
```

### Re-link Cards
```bash
# After updating main card database
python link_cards.py
```

### Export Latest Data
```bash
python export_event_data.py
```

## 🛠️ Technical Details

- **Databases**: SQLite 3
- **Languages**: Python 3.8+
- **Encoding**: UTF-8 (full Japanese/Chinese support)
- **Performance**: Sub-second queries for most operations
- **Storage**: ~55 MB total (event DB + exports)

## 📖 Documentation

- [Event Database Guide](EVENT_DATABASE_README.md) - Complete database documentation
- [Card Linking Guide](CARD_LINKING_GUIDE.md) - Linking methodology and examples
- [Import Summary](EVENT_IMPORT_SUMMARY.md) - Import statistics and process

## 🎯 Future Enhancements

1. **Improve Coverage**: Add missing expansions to main database
2. **Fuzzy Matching**: Use name similarity for unmapped cards
3. **Auto-translation**: Integrate translation APIs
4. **Web Interface**: Build web UI for browsing
5. **Real-time Updates**: Automated event scraping and import
6. **Advanced Analytics**: ML models for deck prediction
7. **Export Formats**: Add Excel, Parquet support

## 📝 License

Data sourced from official Pokemon Trading Card Game resources for educational and analysis purposes.

---

**Last Updated**: November 13, 2025
**Status**: ✅ Operational
**Coverage**: 58.1% card mapping, 427 tournaments, 5,677 players
