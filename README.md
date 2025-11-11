# ptcg-product-info

Download all PTCG (Pokémon Trading Card Game) related product information from official websites and export to CSV.

## Features

### Product Information Scraper (`scraper.py`)

- Scrapes product information from multiple official Pokémon TCG websites:
  - ~~Japan: https://www.pokemon-card.com/products/~~ (Requires Selenium - not yet implemented)
  - Hong Kong (English): https://asia.pokemon-card.com/hk-en/card-search/ ✓ Working
  - Hong Kong (Chinese): https://asia.pokemon-card.com/hk/card-search/ ✓ Working

- Extracts the following product information:
  - Country
  - Product name (series + expansion name)
  - ~~Price~~ (not available on current pages)
  - Release date
  - Product code (extracted from URL)
  - Link
  - ~~Include (what's included in the product)~~ (not available on current pages)
  - Card only status (set to "Yes" for all expansions)

- Exports all data to a timestamped CSV file

**Note**: The Japan site loads products dynamically via JavaScript (using `<div id="ProductsApp">`). 
Selenium WebDriver support is required to scrape it, but is not yet implemented. Currently disabled in config.py.

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
1. Scrape product information from enabled websites (Hong Kong EN/ZH)
2. Generate a CSV file named `ptcg_products_YYYYMMDD_HHMMSS.csv` with all the collected data

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
- `SCRAPE_JAPAN` - Enable/disable Japan site scraping
- `SCRAPE_HONG_KONG_EN` - Enable/disable Hong Kong EN site scraping
- `SCRAPE_HONG_KONG_ZH` - Enable/disable Hong Kong ZH site scraping
- `LOG_LEVEL` - Set logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)

And more configuration options in the file.

## CSV Output Format

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
- See `requirements.txt` for Python package dependencies

## Notes

- The scraper is designed to be respectful to the servers with appropriate delays between requests
- Hong Kong sites: Scrapes expansion/product listings from the card search pages
- **Japan site currently disabled**: Requires Selenium WebDriver to handle JavaScript-rendered content
  - The page uses Vue.js or similar framework with `<div id="ProductsApp">` that loads content dynamically
  - Implementing Selenium support would enable Japan scraping
- Some fields may be empty if the information is not available on the website
- Release dates are extracted from `<time>` elements and may be in various formats
- **Event scraper**: May need updates if the website structure changes. The scraper uses flexible HTML parsing to handle various structures
- Event/deck scraping is rate-limited to be respectful to servers (defaults to first 5 events and first 3 detailed decks in the main script)

## License

MIT License
