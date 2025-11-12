# Copilot Instructions for PTCG Product & Event Scraper

## Project Overview
Multi-purpose web scraper for Pokémon Trading Card Game data from official websites:

### 1. Product Scraper (`scraper.py`)
- **Japan**: ~27 products via Selenium (JavaScript-rendered `<div class="product-card">`)
- **Hong Kong EN/ZH**: ~164 products via requests/BeautifulSoup with pagination
- Outputs timestamped CSV files: product name, price, release date, code, links

### 2. Event Tournament Scraper (`event_scraper_enhanced.py`)
- **Japan tournaments**: Event details + deck lists from https://players.pokemon-card.com/
- **Batch processing**: `batch_scrape_events.py` scrapes 50+ events with pagination
- Outputs structured JSON per event folder: `event_data/event_{id}_{date}/`

**Current Status**: Japan product scraping works (enabled in `config.py`), HK sites disabled.

## Architecture Patterns

### Product Scraping: Inheritance-Based
```python
PTCGScraper                    # Base class: requests.Session + headers
├── JapanPTCGScraper          # Selenium: clicks "もっと見る" button, parses product-card
├── HongKongENPTCGScraper     # requests: expansionList pagination ?pageNo=N
└── HongKongZHPTCGScraper     # requests: same structure as EN
```

### Event Scraping: Standalone Classes
```python
EventDeckScraper              # Selenium-based: event → deck lists → individual cards
└── batch_scrape_events.py   # Orchestrates multiple events with pagination discovery
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

### Event Scraping Development
```bash
# Single event scraping
python event_scraper_enhanced.py

# Batch scraping (50 events, pagination)
python batch_scrape_events.py

# Check existing event data
ls event_data/  # Shows event_ID_DATE folders
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

### Cache Management
`card_code_cache.json`: Stores card code mappings to avoid re-fetching
`CACHE_INFO.md`: Documents cache structure and update procedures

## Adding New Scrapers
1. **Product scraper**: Inherit from `PTCGScraper`, add config flag, implement `scrape()` method
2. **Event scraper**: Follow `EventDeckScraper` pattern for structured JSON output
3. **Always** add mock data generator and debug script in `archive/`
4. Update `main()` orchestration with rate limiting delays
5. Test both online and offline modes before committing
