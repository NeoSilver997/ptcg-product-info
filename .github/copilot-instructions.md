# Copilot Instructions for PTCG Tournament & Product Data System

## Project Overview
Dual-purpose Pokemon TCG data platform combining web scraping, tournament analytics, and bilingual card mapping:

### 1. Product Scraper (`scraper.py`)
- **Japan**: ~27 products via Selenium (JavaScript-rendered `<div class="product-card">`)
- **Hong Kong EN/ZH**: ~164 products via requests/BeautifulSoup with pagination
- Outputs timestamped CSV files: product name, price, release date, code, links
- **Current Status**: Japan scraping enabled in `config.py`, HK sites disabled

### 2. Event Tournament Database (`ptcg_events.db`)
- **427 tournaments** (Oct 5 - Nov 11, 2025) with 5,677 unique players
- **5,640 complete decks** (60 cards each) = 159,137 card entries
- Data flow: `event_data/` JSON → `import_events_to_sqlite.py` → SQLite database
- Normalized schema: events, players, decks, deck_cards, event_results tables

### 3. Bilingual Card Linking (`link_cards.py`)
- Maps Japanese tournament cards → Chinese main database
- **1,564 / 2,692 cards mapped** (58.1% coverage via expansion code + collector number)
- Links stored in `card_mappings` table + `japanese_card_links` in main DB
- Enables bilingual deck analysis and competitive meta tracking

**Critical Integration**: This project bridges Japanese tournament data (event_data/) with Chinese card database (`c:\AI_Server\Coding\PokemonDBByjules\PTCG_CardDB_Tc\pokemon_cards.db`) for cross-language card analysis.

## Architecture Patterns

### Product Scraping: Inheritance-Based
```python
PTCGScraper                    # Base class: requests.Session + headers
├── JapanPTCGScraper          # Selenium: clicks "もっと見る" button, parses product-card
├── HongKongENPTCGScraper     # requests: expansionList pagination ?pageNo=N
└── HongKongZHPTCGScraper     # requests: same structure as EN
```

### Event Data Pipeline: JSON → Database → Analysis
```python
# Step 1: Scrape events to JSON files
EventDeckScraper              # Selenium: event → deck lists → cards
└── batch_scrape_events.py   # Batch processing with pagination (50+ events)
    └── event_data/event_{id}_{date}/
        ├── event_info.json       # Event metadata + all results
        └── deck_*.json           # Individual deck with 60 cards

# Step 2: Import to normalized database
EventDataImporter             # import_events_to_sqlite.py
└── ptcg_events.db            # Tables: events, players, decks, deck_cards, event_results

# Step 3: Link with main database
CardLinker                    # link_cards.py
└── Matches: expansion_code + collector_number
    ├── card_mappings (in ptcg_events.db)
    └── japanese_card_links (in pokemon_cards.db)
```

### Bilingual Card Linking Algorithm
```python
# Parse: "SV8a 120/187" → expansion="SV8a", number="120"
expansion_code, collector_number = parse_card_code(card_code)

# Match in main DB
SELECT id, name FROM cards 
WHERE expansion_id = (SELECT id FROM expansions WHERE code = 'SV8a')
AND collector_number = '120'

# Store bidirectional mapping
Japanese: ドラパルトex (SV8a 120/187) ↔ Chinese: 多龍巴魯托ex
```

### Configuration-Driven Design
All behavior controlled via `config.py` with graceful fallbacks:
- Scraper enable/disable: `SCRAPE_JAPAN`, `SCRAPE_HONG_KONG_EN`, `SCRAPE_HONG_KONG_ZH`
- Rate limiting: `DELAY_BETWEEN_REQUESTS` between sites/pages
- Output: `OUTPUT_FILENAME = None` → auto-timestamps, custom names supported
- **Never hardcode URLs or delays** - always use config values

## Critical Development Workflows

### Product Scraping Development
```bash
# Full scraping with current config
python scraper.py

# Test without network (uses mock data)
python archive/test_scraper.py

# Debug HTML structure changes
# Set LOG_LEVEL = "DEBUG" in config.py first
python scraper.py  # Check logs for parse failures
```

### Event Database Management
```bash
# Import new event JSON files to database
python import_events_to_sqlite.py

# Link Japanese event cards → Chinese main database
python link_cards.py

# Query event data (popular cards, top players, recent tournaments)
python query_events.py

# Query bilingual card mappings
python query_linked_cards.py

# Export all data to CSV/JSON
python export_event_data.py
```

### Database Verification & Updates
```bash
# Verify event database integrity
python verify_db.py

# Update Chinese main database with Japanese links
python update_chinese_db.py

# Verify Chinese database after update
python verify_chinese_db.py
```

### Cache Management (Card Codes)
```bash
# Fetch missing card codes (uses cache to avoid redundant requests)
python fetch_card_codes.py

# Analyze cache structure and coverage
python analyze_cache.py
python check_cache_structure.py
```

### Debugging Selenium Issues
Japan scraping uses headless Chrome. For debugging:
1. Remove `--headless` from ChromeOptions in scraper code
2. Add `time.sleep(5)` before `driver.quit()` to inspect page
3. Check `debug_japan_selenium.html` in archive/ for saved page source

## Site-Specific Implementation Patterns

### Japan: Selenium + BeautifulSoup Hybrid
```python
# Key pattern: Wait for JS-rendered content, then parse static HTML
driver.get(url)
WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CLASS_NAME, "product-card")))
soup = BeautifulSoup(driver.page_source, 'html.parser')
products = soup.find_all('div', class_='product-card')
```

Date parsing for Japanese format:
```python
# "2025年11月28日（金）" → "2025-11-28"
date_match = re.search(r'(\d{4})年(\d{1,2})月(\d{1,2})日', date_text)
```

### Hong Kong: Pagination Discovery Pattern
```python
while True:
    page_url = f"{base_url}?pageNo={page_number}" if page_number > 1 else base_url
    # ... scrape current page ...
    
    # Check for next page
    pagination = soup.find('nav', class_='pagination')
    next_button = pagination.find('li', class_='paginationItem next')
    if not (next_button and next_button.find('a')):
        break  # No more pages
    page_number += 1
    time.sleep(1)  # Respectful delay
```

### Event Data: Structured JSON Output
Events organized in folders: `event_data/event_{id}_{date}/`
- `event_info.json`: Event details + all tournament results
- `deck_{deck_id}.json`: Individual deck with 60 cards
- **Batch processing**: Auto-discovers event IDs from list pages with pagination

## Common Patterns & Gotchas

### Database Linking Pattern
**ALWAYS follow this order when working with bilingual data:**
1. Import events: `import_events_to_sqlite.py` (creates event database)
2. Link cards: `link_cards.py` (creates mappings in event DB)
3. Update main DB: `update_chinese_db.py` (adds japanese_card_links table)
4. Verify: `verify_chinese_db.py` (confirms bidirectional links work)

### Card Code Parsing
```python
# Standard format: "SV8a 120/187"
expansion_code, collector_number = parse_card_code(card_code)

# Special cases to handle:
- ACE SPEC cards: Return None, None (no standard codes)
- Basic Energy: Often missing codes
- Promo cards (SV-P): May not be in main database
```

### Query Patterns for Bilingual Data
```python
# Get Japanese card with Chinese translation
SELECT 
    dc.card_name as japanese,
    cm.main_card_name as chinese,
    dc.quantity
FROM deck_cards dc
LEFT JOIN card_mappings cm ON dc.card_id = cm.event_card_id
WHERE dc.deck_id = ?

# Get top cards with both names
SELECT 
    dc.card_name as japanese,
    cm.main_card_name as chinese,
    COUNT(DISTINCT dc.deck_id) as deck_count
FROM deck_cards dc
LEFT JOIN card_mappings cm ON dc.card_id = cm.event_card_id
GROUP BY dc.card_id
ORDER BY deck_count DESC
```

### Error Handling Philosophy
Scrapers continue on individual item failures, never crash entire runs:
```python
try:
    product = self._parse_product_item(item)
    if product:  # Only add if valid (has name + link)
        products.append(product)
except Exception as e:
    logger.warning(f"Error parsing product item: {e}")
    continue  # Skip this item, continue processing
```

### Performance Considerations
- **Event import**: 427 events takes ~30 seconds with proper indexing
- **Card linking**: ~2,700 cards matched in <1 second with expansion map
- **Cache usage**: 812 cards with cache = instant, without = 27 minutes
- **Batch sizes**: Selenium requests limited to 2-second delays between pages

## Integration Points & Data Flow

### CSV Schema (Fixed Order)
`['country', 'product_name', 'price', 'release_date', 'code', 'link', 'image_url', 'include', 'card_only']`
- Always strings, empty string for missing data (never `None`)
- Products sorted by release date (newest first)

### Event Data Schema
JSON structure with nested tournament results:
```json
{
  "event_id": "848638",
  "event_date": "2025-11-11", 
  "results": [{"rank": "1位", "deck_id": "...", "deck_url": "..."}]
}
```

### Database Relationships
```
ptcg_events.db (Japanese tournament data):
  events → event_results → decks → deck_cards
  card_mappings (Japanese → Chinese mapping)

pokemon_cards.db (Chinese main database):
  cards → expansions, skills, abilities
  japanese_card_links (bidirectional link to event data)
```

### Critical Database Path
Main Chinese database: `c:\AI_Server\Coding\PokemonDBByjules\PTCG_CardDB_Tc\pokemon_cards.db`
- **Always use this absolute path** in scripts that integrate with main database
- Contains cards, expansions, skills, abilities, illustrators tables
- Enhanced with `japanese_card_links` table for bilingual support

### Cache Management
`card_code_cache.json`: Stores card code mappings to avoid re-fetching
- **Format**: `{"card_id": "expansion_code collector/total"}`
- **Benefits**: Instant retrieval, resumable, incremental updates
- **Usage**: Automatically loaded/saved by `fetch_card_codes.py`

## Key Reference Files

**Data Processing:**
- `scraper.py`: Product scraping with Selenium/BeautifulSoup hybrid
- `event_scraper_enhanced.py`: Tournament data scraping
- `batch_scrape_events.py`: Batch event processing with pagination
- `import_events_to_sqlite.py`: JSON → database import
- `link_cards.py`: Bilingual card mapping algorithm
- `update_chinese_db.py`: Main database integration

**Query & Analysis:**
- `query_events.py`: Tournament analysis queries
- `query_linked_cards.py`: Bilingual card search
- `export_event_data.py`: Data export utilities
- `verify_db.py`: Event database verification
- `verify_chinese_db.py`: Main database verification

**Configuration:**
- `config.py`: All scraper settings and feature flags
- `card_code_cache.json`: Card code cache (auto-generated)
- `CACHE_INFO.md`: Cache documentation
- `CARD_LINKING_GUIDE.md`: Linking methodology and examples

**Documentation:**
- `PROJECT_README.md`: Comprehensive project overview
- `EVENT_DATABASE_README.md`: Database schema and queries
- `CARD_LINKING_GUIDE.md`: Bilingual linking patterns

## Testing & Debugging Infrastructure

### Mock Testing Pattern
`archive/test_scraper.py` generates sample data without network calls:
```python
def generate_mock_products():
    return [{'country': 'Japan', 'product_name': '...', ...}]
```
Use this pattern for new scrapers to test CSV export logic.

### Archive-Driven Debugging
`archive/` contains debugging scripts for each site/feature:
- `test_japan_selenium.py`: Test Japan scraper in isolation
- `check_pagination_structure.py`: Verify HK pagination HTML
- `debug_event_848624.py`: Test specific event parsing
- **Pattern**: Create focused debug scripts, save HTML samples for offline analysis

## Development Best Practices

### When Adding New Features
1. **Event scraping**: Follow `EventDeckScraper` pattern for structured JSON output
2. **Database changes**: Update both event DB and main DB schemas
3. **Card mapping**: Re-run `link_cards.py` after schema changes
4. **Always verify**: Run verify scripts after database updates
5. Add comprehensive error handling and logging

### Database Schema Changes
1. Update event database schema first (`import_events_to_sqlite.py`)
2. Modify card linking logic if needed (`link_cards.py`)
3. Update main database integration (`update_chinese_db.py`)
4. Test bidirectional queries work correctly
5. Update TypeScript types if web app is affected

### Performance Monitoring
- Use cache system for card codes (saves hours of scraping)
- Monitor Selenium delays (2 seconds between requests)
- Profile database queries (use indexes for common patterns)
- Track import times (should be <1 minute for full dataset)

### Adding New Scrapers
1. **Product scraper**: Inherit from `PTCGScraper`, add config flag, implement `scrape()` method
2. **Event scraper**: Follow `EventDeckScraper` pattern for structured JSON output
3. **Always** add mock data generator and debug script in `archive/`
4. Update `main()` orchestration with rate limiting delays
5. Test both online and offline modes before committing

### Debug Script Patterns
- Place debug scripts in `temp/debug/` with auto-numbered prefixes (`01_debug_rarity.py`)
- Include markdown documentation for new debug scripts
- Use focused debug scripts for testing individual components before integration

### Data Processing Conventions
- Handle alphanumeric collector numbers as strings
- Validate HP as integers, defaulting to 0 on failure
- Skip cards missing essential fields (`Web Card ID`, `Name`)
- Use batch processing for large datasets (100-1000 records per batch)

Remember: This codebase bridges Japanese tournament data with Chinese card database for competitive meta analysis. Always test end-to-end when making changes that affect the linking system.
