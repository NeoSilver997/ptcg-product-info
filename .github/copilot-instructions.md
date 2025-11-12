# Copilot Instructions for PTCG Product Info Scraper

## Project Overview
Web scraper for Pokémon Trading Card Game product information from official websites. Currently supports Hong Kong EN/ZH sites via `requests` library with **pagination support**. Outputs timestamped CSV files with product details: name, series, release date, code, link, and image URL.

**Japan site disabled**: Requires Selenium for JavaScript-rendered content (Vue.js app in `<div id="ProductsApp">`).

**Current capabilities**: Scrapes ~164 total products (41 EN + 123 ZH) across multiple pages automatically.

## Architecture Pattern
Class-based scraper with inheritance:
- `PTCGScraper`: Base class with `requests.Session` and shared headers/timeout
- `HongKongENPTCGScraper` / `HongKongZHPTCGScraper`: Parse `<ul class="expansionList">` with `<li class="expansion">` items
  - **Pagination**: Loop through pages using `?pageNo=N` parameter until no "Next" button found
  - Extract from `<h3 class="expansionTitle">`, `<span class="series">`, `<time>` tags, `<img>` src, and URL parameters
  - Return `List[Dict]` with standardized schema
  - Small delay (1s) between pages to be respectful
- `JapanPTCGScraper`: Currently returns empty list with warning (needs Selenium implementation)

## Configuration-Driven Behavior
All scraping controlled via `config.py`:
- `SCRAPE_JAPAN = False`: Disabled (requires Selenium)
- `SCRAPE_HONG_KONG_EN`, `SCRAPE_HONG_KONG_ZH`: Enable/disable scrapers
- `OUTPUT_FILENAME = None` → auto-timestamped filenames (`ptcg_products_YYYYMMDD_HHMMSS.csv`)
- `DELAY_BETWEEN_REQUESTS = 2`: Rate limiting between sites
- Graceful fallback to hardcoded defaults if `config.py` missing

**When modifying**: Maintain backward compatibility with config flags. Never hardcode URLs/delays.

## Development Workflow

### Running the scraper
```bash
python scraper.py
```
Output: `ptcg_products_YYYYMMDD_HHMMSS.csv` (or custom filename from config)

### Testing without internet
```bash
python test_scraper.py
```
Generates `test_ptcg_products.csv` using mock data defined in `generate_mock_products()`. Use this to verify CSV export logic and schema changes without hitting live sites.

### Debugging failed scrapes
1. Set `LOG_LEVEL = "DEBUG"` in `config.py` to see detailed HTML structure logs
2. Check `logger.warning(f"Error parsing product item: {e}")` for partial failures
3. HTML structure fragility: Scrapers log items found but continue on parse errors—verify actual site structure hasn't changed

## Critical Patterns

### Hong Kong Sites: expansionList Parsing
Hong Kong scrapers target specific structure with pagination:
```python
# Pagination loop
while True:
    page_url = f"{self.products_url}?pageNo={page_number}" if page_number > 1 else self.products_url
    expansion_list = soup.find('ul', class_='expansionList')
    product_items = expansion_list.find_all('li', class_='expansion')
    
    # Check for next page
    pagination = soup.find('nav', class_='pagination')
    next_button = pagination.find('li', class_='paginationItem next')
    if not (next_button and next_button.find('a')):
        break
    page_number += 1
    time.sleep(1)  # Respectful delay between pages
```

Parser extracts:
- Title: `item.find('h3', class_='expansionTitle')`
- Series: `item.find('span', class_='series')` → prepended to product name
- Date: `item.find('time')` with `datetime` attribute fallback to text
- Code: Extracted from URL param `expansionCodes=XXX`
- Link: `item.find('a', class_='expansionLink')` with base URL prepending
- Image: `item.find('img')` src attribute with base URL prepending

**Always**: Return `None` if no product_name or link. Log warnings on parse errors, never raise exceptions.

### URL Handling
Hong Kong scrapers construct absolute URLs:
```python
if href.startswith('http'):
    product['link'] = href
else:
    product['link'] = self.base_url + href
```

### Japan Site: JavaScript Requirement
Japan site (`https://www.pokemon-card.com/products/`) uses `<div id="ProductsApp">` populated by JavaScript after page load. `requests` library cannot access this content. To implement:
1. Use Selenium WebDriver to load page and wait for JavaScript execution
2. Wait for `#ProductsApp` to contain product items
3. Parse rendered HTML with BeautifulSoup
4. Update `JapanPTCGScraper.scrape()` method

### Adding New Scrapers
1. Inherit from `PTCGScraper`
2. Set `self.country`, `self.base_url`, `self.products_url` in `__init__`
3. Implement `scrape()` to call `self._parse_product_item()` on BeautifulSoup results
4. Add config flag (e.g., `SCRAPE_NEW_REGION`) to `config.py` and `scraper.py` import/defaults
5. Add scraper instantiation in `main()` with `time.sleep(DELAY_BETWEEN_REQUESTS)` after scrape
6. Add mock data to `test_scraper.py` for the new region

## CSV Schema (Fixed Order)
`['country', 'product_name', 'price', 'release_date', 'code', 'link', 'image_url', 'include', 'card_only']`

All fields are strings. Empty strings for missing data (never `None` or omit keys).

## Dependencies
- `requests`/`BeautifulSoup`: HTTP fetching and HTML parsing
- `selenium` (in requirements but unused): Likely for future JS-heavy pages—not currently implemented
- Python 3.7+ required (type hints in function signatures)

## Known Limitations
- Hong Kong scrapers work correctly with `expansionList` structure
- Japan site requires Selenium (not implemented) - currently disabled with warning logs
- No retry logic for failed HTTP requests (raises on `response.raise_for_status()`)
- Sequential scraping only (no parallelization)
- Selenium installed but not used for Japan site
