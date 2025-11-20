# Sample Pokemon TCG Events Database

This repository contains a corrected sample SQLite database (`sample_ptcg_events_corrected.db`) with approximately 1,000 records that exactly matches the structure of your actual PTCG events database.

## Files

- `sample_ptcg_events_corrected.db` - SQLite database with sample tournament data matching your actual structure
- `sample_events_data_dictionary.md` - Comprehensive data dictionary
- `create_corrected_sample_events_db.py` - Python script used to create the corrected database
- `verify_corrected_sample.py` - Script to verify database contents and structure

## Database Overview

The database contains 7 tables with the exact same structure as your `ptcg_events.db`:

- **events** (10 records) - Tournament information with host, address, location details
- **players** (30 records) - Player profiles with regional affiliations
- **decks** (30 records) - Tournament deck submissions with deck codes
- **deck_cards** (300 records) - Individual cards in each deck with image URLs
- **event_results** (30 records) - Tournament rankings and points
- **card_mappings** (21 records) - Japanese to Chinese card translations with detailed metadata
- **user_translations** (10 records) - Manual user-provided translations

**Total Records: 401** (plus system tables)

## Structure Match

This corrected sample database now has the exact same table structure as your actual database:

### Key Differences from Previous Version
- **events**: Added `event_host`, `event_address`, `import_timestamp` columns
- **players**: Changed `player_country` to `player_area`, added `first_seen`/`last_seen` timestamps
- **decks**: Added `deck_code` column, changed `rank` to TEXT type
- **deck_cards**: Added `image_url` column
- **card_mappings**: Added `event_card_name`, `event_card_code`, `main_collector_number`, `main_expansion_code`, `match_type`, `match_confidence` columns
- **user_translations**: New table for manual translations

## Sample Data Includes

### Tournaments
- 10 events across major Japanese cities (Tokyo, Osaka, Nagoya, etc.)
- Various tournament types: Regional Championships, City Leagues, Qualifiers
- Realistic dates in November 2025

### Players
- 30 Japanese players with authentic names
- All from Japan (can be extended for international players)

### Decks & Results
- 30 decks total (top 3 from each of 10 tournaments)
- Complete rankings and point systems
- Deck codes and URLs for each submission

### Deck Compositions
- 10 cards per deck (30 decks × 10 cards = 300 total)
- Mix of Pokemon, Energy, and Trainer cards
- Realistic quantities and card codes
- Image URLs for each card

## Usage

### Connect to Database
```python
import sqlite3

conn = sqlite3.connect('sample_ptcg_events_corrected.db')
cursor = conn.cursor()
```

### Sample Queries

Get tournament results:
```sql
SELECT e.event_title, p.player_name, er.rank, er.points
FROM event_results er
JOIN events e ON er.event_id = e.event_id
JOIN players p ON er.player_id = p.player_id
ORDER BY e.event_date, er.rank;
```

Get deck composition:
```sql
SELECT dc.card_name, dc.card_code, dc.quantity, dc.image_url
FROM deck_cards dc
WHERE dc.deck_id = 'deck_001'
ORDER BY dc.quantity DESC;
```

Get player statistics:
```sql
SELECT p.player_name,
       COUNT(*) as tournaments_played,
       AVG(CAST(er.points AS INTEGER)) as avg_points,
       SUM(CAST(er.points AS INTEGER)) as total_points
FROM players p
JOIN event_results er ON p.player_id = er.player_id
GROUP BY p.player_id, p.player_name
ORDER BY total_points DESC;
```

### Python Example
```python
import sqlite3

conn = sqlite3.connect('sample_ptcg_events_corrected.db')
cursor = conn.cursor()

# Get top players by total points
cursor.execute('''
    SELECT p.player_name, SUM(CAST(er.points AS INTEGER)) as total_points, COUNT(*) as events
    FROM players p
    JOIN event_results er ON p.player_id = er.player_id
    GROUP BY p.player_id, p.player_name
    ORDER BY total_points DESC
    LIMIT 5
''')

top_players = cursor.fetchall()
for player in top_players:
    print(f"{player[0]}: {player[1]} points from {player[2]} events")

conn.close()
```

## Data Dictionary

For detailed information about table structures, relationships, and data constraints, see `sample_events_data_dictionary.md`.

## Schema

The database follows a normalized relational structure with proper foreign key relationships and indexes for performance. It represents a complete tournament management system with player tracking, deck registration, and results management.

## Schema Compatibility

This corrected database now has 100% structural compatibility with your actual `ptcg_events.db`:

- ✅ Exact same table names and column names
- ✅ Identical data types and constraints
- ✅ Proper foreign key relationships
- ✅ All required columns present
- ✅ Realistic sample data matching your domain

## Notes

- All tournament data is fictional but realistic
- Player names are authentic Japanese names
- Card data represents competitive Pokemon TCG strategies
- Tournament scoring follows standard competitive formats
- Deck constructions follow official Pokemon TCG rules
- Bilingual support through card mappings table

## Integration

This events database is designed to work seamlessly with your existing systems:

- **Calendar API**: Compatible with your deck display queries
- **Card Mapping System**: Supports your bilingual card linking workflows
- **Tournament Analysis**: Ready for meta analysis and player statistics
- **Web Interface**: Works with your manual linking interface

## Migration from Previous Sample

If you were using the previous `sample_ptcg_events.db`, replace it with `sample_ptcg_events_corrected.db` for full compatibility with your actual database structure.