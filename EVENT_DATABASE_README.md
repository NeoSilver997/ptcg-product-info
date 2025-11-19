# Pokemon TCG Event Database

SQLite database containing tournament results and deck lists from official Pokemon TCG events in Japan.

## Database Overview

**Database File**: `ptcg_events.db`

**Data Coverage**:
- **427 Events** from October 5, 2025 to November 11, 2025
- **5,677 Unique Players**
- **5,640 Decks** with complete card lists
- **159,137 Card Entries** (individual card instances in decks)

## Database Schema

### Tables

#### `events`
Tournament event information.

| Column | Type | Description |
|--------|------|-------------|
| event_id | TEXT | Primary key, unique event identifier |
| event_date | DATE | Event date |
| event_title | TEXT | Event title/name |
| event_host | TEXT | Hosting store/venue |
| event_address | TEXT | Full address |
| event_location | TEXT | Location description |
| event_url | TEXT | Official event page URL |
| import_timestamp | TIMESTAMP | When data was imported |

#### `players`
Player information aggregated across all events.

| Column | Type | Description |
|--------|------|-------------|
| player_id | TEXT | Primary key, unique player identifier |
| player_name | TEXT | Player display name |
| player_area | TEXT | Player's region/prefecture |
| first_seen | TIMESTAMP | First tournament appearance |
| last_seen | TIMESTAMP | Most recent tournament |

#### `event_results`
Tournament rankings linking events and players.

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Auto-increment primary key |
| event_id | TEXT | Foreign key to events |
| player_id | TEXT | Foreign key to players |
| rank | TEXT | Placement (1位, 2位, 3位, 5位, 9位) |
| points | TEXT | Championship points earned |
| deck_id | TEXT | Deck used in tournament |

#### `decks`
Complete deck information.

| Column | Type | Description |
|--------|------|-------------|
| deck_id | TEXT | Primary key, unique deck code |
| deck_code | TEXT | Deck code for imports |
| deck_url | TEXT | Official deck list URL |
| event_id | TEXT | Foreign key to events |
| player_id | TEXT | Foreign key to players |
| rank | TEXT | Placement achieved with this deck |
| import_timestamp | TIMESTAMP | When data was imported |

#### `deck_cards`
Individual cards in each deck (60 cards per deck).

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Auto-increment primary key |
| deck_id | TEXT | Foreign key to decks |
| card_id | TEXT | Official card ID |
| card_name | TEXT | Card name (Japanese) |
| card_code | TEXT | Set code and number |
| quantity | INTEGER | Number of copies in deck |
| image_url | TEXT | Official card image URL |

## Usage Examples

### Import Data

```bash
# Import all event data from event_data/ folder
python import_events_to_sqlite.py
```

This will:
1. Create `ptcg_events.db` database
2. Create all tables with indexes
3. Import all event folders
4. Display import statistics

### Query and Analyze Data

```bash
# Run comprehensive analysis
python query_events.py
```

This provides:
- Recent events overview
- Top players by wins
- Most used cards across all decks
- Recent winning deck lists

### Python API Examples

```python
from query_events import EventDataAnalyzer

analyzer = EventDataAnalyzer('ptcg_events.db')

# Get top 10 players
top_players = analyzer.get_top_players(10)

# Find most popular cards
popular_cards = analyzer.get_most_used_cards(50)

# Search for specific card usage
decks_with_pikachu = analyzer.search_cards_in_decks('ピカチュウ')

# Get winning decks
first_place_decks = analyzer.get_winning_decks('1位', limit=20)

# Analyze specific event
event_stats = analyzer.get_event_statistics('848638')

# Player tournament history
player_history = analyzer.get_player_history('0038262168')

analyzer.close()
```

## SQL Query Examples

### Most Popular Cards
```sql
SELECT 
    card_name,
    card_code,
    COUNT(DISTINCT deck_id) as deck_count,
    SUM(quantity) as total_quantity
FROM deck_cards
WHERE card_name NOT LIKE '%エネルギー%'
GROUP BY card_name, card_code
ORDER BY deck_count DESC
LIMIT 20;
```

### Top Players by Wins
```sql
SELECT 
    p.player_name,
    p.player_area,
    COUNT(CASE WHEN er.rank = '1位' THEN 1 END) as wins,
    COUNT(*) as total_events
FROM players p
JOIN event_results er ON p.player_id = er.player_id
GROUP BY p.player_id
ORDER BY wins DESC, total_events DESC;
```

### Recent Events
```sql
SELECT 
    e.event_id,
    e.event_date,
    e.event_host,
    COUNT(DISTINCT er.player_id) as player_count
FROM events e
LEFT JOIN event_results er ON e.event_id = er.event_id
GROUP BY e.event_id
ORDER BY e.event_date DESC
LIMIT 10;
```

### Deck Archetype Analysis
```sql
SELECT 
    d.deck_id,
    d.rank,
    e.event_date,
    GROUP_CONCAT(dc.card_name || ' (' || dc.quantity || 'x)') as key_cards
FROM decks d
JOIN deck_cards dc ON d.deck_id = dc.deck_id
JOIN events e ON d.event_id = e.event_id
WHERE dc.card_name LIKE '%ex%'
GROUP BY d.deck_id
ORDER BY e.event_date DESC;
```

### Card Co-occurrence (What cards appear together)
```sql
SELECT 
    a.card_name as card_1,
    b.card_name as card_2,
    COUNT(DISTINCT a.deck_id) as deck_count
FROM deck_cards a
JOIN deck_cards b ON a.deck_id = b.deck_id AND a.card_name < b.card_name
WHERE a.card_name NOT LIKE '%エネルギー%' 
AND b.card_name NOT LIKE '%エネルギー%'
GROUP BY a.card_name, b.card_name
HAVING deck_count > 100
ORDER BY deck_count DESC
LIMIT 50;
```

## Data Sources

Event data scraped from official Pokemon Card Game Players website:
- https://players.pokemon-card.com/

Each event folder contains:
- `event_info.json`: Event details and tournament results
- `deck_*.json`: Individual deck lists with complete card information

## Performance

**Database Size**: ~50 MB (with 159k+ card entries)

**Indexes**: Optimized for common queries
- Event date lookups
- Player searches
- Card frequency analysis
- Deck composition queries

## Data Updates

To update with new events:

1. Scrape new event data using event scraper
2. Run `python import_events_to_sqlite.py` again
3. Existing events are skipped (INSERT OR REPLACE)
4. New events are added incrementally

## Analysis Capabilities

### Tournament Meta Analysis
- Most played cards across all tournaments
- Winning deck compositions
- Card popularity trends over time
- Regional meta differences

### Player Statistics
- Win rates and placement history
- Favorite decks and cards
- Tournament participation patterns

### Deck Analysis
- Archetype identification
- Card synergies and combos
- Energy distribution patterns
- Trainer card ratios

### Competitive Intelligence
- Counter-deck strategies
- Meta predictions
- Card value assessment
- Emerging archetypes

## Integration with Pokemon Card Database

This event database complements the main Pokemon card database:

**Main Card DB** (`PTCG_CardDB_Tc/pokemon_cards.db`):
- Complete card information
- Card effects and abilities
- Set information
- Card ratings

**Event DB** (`ptcg_events.db`):
- Tournament usage statistics
- Competitive deck compositions
- Real-world performance data
- Meta game trends

Combine both databases for comprehensive analysis:
- Card power level based on tournament success
- Deck building recommendations
- Meta game predictions
- Strategic card evaluations

## Technical Notes

- **Date Format**: YYYY-MM-DD (ISO 8601)
- **Text Encoding**: UTF-8 (Japanese characters fully supported)
- **Rank Values**: 1位 (1st), 2位 (2nd), 3位 (3rd), 5位 (5th), 9位 (9th)
- **Foreign Keys**: Enabled with cascading constraints
- **Transactions**: Batch inserts for performance

## Requirements

```bash
pip install sqlite3  # Built-in with Python
```

No additional dependencies required for basic usage.

## License

Data sourced from official Pokemon Trading Card Game resources for educational and analysis purposes.
