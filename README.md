# ptcg-product-info

Download all PTCG (Pokémon Trading Card Game) related product information from official websites and export to CSV.

## Features

### Product Information Scraper (`scraper.py`)

- Scrapes product information from multiple official Pokémon TCG websites:
  - **Japan**: https://www.pokemon-card.com/products/ ✓ Working (2 pages via "もっと見る" button, ~27 products)
  - **Hong Kong (English)**: https://asia.pokemon-card.com/hk-en/card-search/ ✓ Working (3 pages, ~41 expansions)
  - **Hong Kong (Chinese)**: https://asia.pokemon-card.com/hk/card-search/ ✓ Working (7 pages, ~123 expansions)

- **Pagination support**: 
  - Japan: Clicks "もっと見る" (See More) button to load additional products
  - Hong Kong: Navigates through multiple pages using `?pageNo=N` parameter

- Extracts the following product information:
  - Country/Region
  - Product name (with product type/series prefix)
  - Price (Japan only)
  - **Release date** (YYYY-MM-DD format, standardized across all sites)
  - **Product code** (extracted from image filenames or URL parameters)
  - **Link to product details** (Japan: `https://www.pokemon-card.com/ex/{code}/`, Hong Kong: card listing pages)
  - **Image URL** (expansion package/box art)
  - Include (what's included in the product)
  - Card only status

- **Date sorting**: Products are automatically sorted by release date (newest first) in the CSV output

- **Japan date formatting**: Converts Japanese dates (e.g., "2025年11月28日（金）") to ISO format (2025-11-28)

- Exports all data to a timestamped CSV file (or custom filename via config)

**Technical Note**: The Japan site uses Selenium WebDriver to handle JavaScript-rendered content. 
Product listings are dynamically loaded into `<div class="product-card">` elements after page load.

### Event Deck List Scraper (`event_scraper.py`) ✨ NEW

- Scrapes deck list information from Japan event results:
  - Event List: https://players.pokemon-card.com/event/result/list

- Extracts the following information:
  - **Events**: event name, date, location, URL, type
  - **Deck Lists**: player name, rank, deck type, deck URL, deck code
  - **Detailed Decks**: card name, count, card number, set name

- Supports three-level scraping:
  1. Event list - List of all events
  2. Deck lists per event - Player decks from each event
  3. Detailed card lists - Individual cards in each deck

- Exports data to separate timestamped CSV files for each level

## Installation

1. Clone this repository:
```bash
git clone https://github.com/NeoSilver997/ptcg-product-info.git
cd ptcg-product-info
```

2. Install required dependencies:
```bash
pip install -r requirements.txt
```

## Usage

### Product Scraper

Run the product scraper:
```bash
python scraper.py
```

This will:
<<<<<<< HEAD
1. Scrape product information from all enabled websites (Japan, Hong Kong EN/ZH)
2. Sort products by release date (newest first)
3. Generate a CSV file named `ptcg_products.csv` (or `ptcg_products_YYYYMMDD_HHMMSS.csv` if OUTPUT_FILENAME is None)

**Total products scraped**: ~191 (27 Japan + 41 HK EN + 123 HK ZH)
=======
1. Scrape product information from enabled websites (Hong Kong EN/ZH)
2. Generate a CSV file named `ptcg_products_YYYYMMDD_HHMMSS.csv` with all the collected data
>>>>>>> fe1af2aa5475d158a64002653ec1a5843b30d258

### Event Deck List Scraper ✨ NEW

Run the event deck list scraper:
```bash
python event_scraper.py
```

This will:
1. Scrape the event list and generate `ptcg_events_YYYYMMDD_HHMMSS.csv`
2. Scrape deck lists from events (first 5) and generate `ptcg_deck_lists_YYYYMMDD_HHMMSS.csv`
3. Scrape detailed card lists from decks (first 3) and generate `ptcg_deck_cards_YYYYMMDD_HHMMSS.csv`

You can modify the script to scrape more events/decks or customize the behavior.

### Configuration

You can customize the scraper behavior by editing `config.py`:

- `OUTPUT_FILENAME` - Set a custom output filename (or use None for auto-timestamped files)
- `REQUEST_TIMEOUT` - Timeout for HTTP requests in seconds
- `DELAY_BETWEEN_REQUESTS` - Delay between requests to be respectful to servers
- `SCRAPE_JAPAN` - Enable/disable Japan site scraping (requires Selenium)
- `SCRAPE_HONG_KONG_EN` - Enable/disable Hong Kong EN site scraping
- `SCRAPE_HONG_KONG_ZH` - Enable/disable Hong Kong ZH site scraping
- `LOG_LEVEL` - Set logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)

And more configuration options in the file.

## CSV Output Format

<<<<<<< HEAD
The CSV file contains the following columns (sorted by release date, newest first):
- `country` - Source country/region (Japan, Hong Kong (EN), Hong Kong (ZH))
- `product_name` - Name of the product (includes product type/series prefix)
- `price` - Product price (Japan only, in format like "550円（税込）")
- `release_date` - Release date in YYYY-MM-DD format (e.g., "2025-11-28")
- `code` - Product code (extracted from image filenames or URL parameters)
- `link` - URL to the product page (Japan: detail pages like `https://www.pokemon-card.com/ex/{code}/`, Hong Kong: card listing pages)
- `image_url` - URL to product image (package/box art)
- `include` - What's included in the product (currently not available)
- `card_only` - Whether it's cards only (typically "Yes" for expansions)
=======
### Product Scraper Output

The CSV file contains the following columns:
- `country` - Source country/region
- `product_name` - Name of the product
- `price` - Product price
- `release_date` - Release date
- `code` - Product code
- `link` - URL to the product page
- `include` - What's included in the product
- `card_only` - Whether it's cards only
>>>>>>> fe1af2aa5475d158a64002653ec1a5843b30d258

### Event Deck List Scraper Output ✨ NEW

**Events CSV** (`ptcg_events_*.csv`):
- `event_name` - Name of the event
- `event_date` - Event date
- `event_location` - Event location
- `event_url` - URL to the event results
- `event_type` - Type of event (Champions League, City League, etc.)

**Deck Lists CSV** (`ptcg_deck_lists_*.csv`):
- `event_url` - URL of the event
- `player_name` - Player name
- `player_rank` - Player's rank/position
- `deck_type` - Type of deck (e.g., "Mew VMAX", "Lugia VSTAR")
- `deck_url` - URL to the detailed deck list
- `deck_code` - Deck import code (if available)

**Detailed Deck Cards CSV** (`ptcg_deck_cards_*.csv`):
- `deck_url` - URL of the deck
- `card_name` - Name of the card
- `card_count` - Number of copies in the deck
- `card_number` - Card number (e.g., "114/172")
- `set_name` - Set/expansion name

## Requirements

- Python 3.7+
- **Selenium WebDriver** (for Japan site scraping)
- Chrome/Chromium browser (for headless Selenium)
- See `requirements.txt` for Python package dependencies

## Notes

- The scraper is designed to be respectful to the servers with appropriate delays between requests
- **Pagination support**: Automatically discovers and scrapes all available pages
  - **Japan**: ~2 pages by clicking "もっと見る" button (~27 products including expansions and accessories)
  - **Hong Kong EN**: ~3 pages (~41 expansions)
  - **Hong Kong ZH**: ~7 pages (~123 expansions)
- **Japan site**: Uses Selenium WebDriver to handle JavaScript-rendered product cards
  - Extracts: name, type, price, release date (formatted to YYYY-MM-DD), code (from image filename), detail page link, image URL
  - Product codes derived from image filenames (e.g., `m2a`, `M2`, `mc`)
  - Detail pages accessible at `https://www.pokemon-card.com/ex/{code}/`
- **Hong Kong sites**: Uses requests library for static HTML parsing
  - Extracts: name, series, release date, code (from URL parameter), card listing link, image URL
- **Date formatting**: All dates standardized to YYYY-MM-DD format regardless of source
- **CSV sorting**: Output is automatically sorted by release date (newest first)
- Some fields may be empty if the information is not available on the website
<<<<<<< HEAD
=======
- Release dates are extracted from `<time>` elements and may be in various formats
- **Event scraper**: May need updates if the website structure changes. The scraper uses flexible HTML parsing to handle various structures
- Event/deck scraping is rate-limited to be respectful to servers (defaults to first 5 events and first 3 detailed decks in the main script)
>>>>>>> fe1af2aa5475d158a64002653ec1a5843b30d258

## License

MIT License
