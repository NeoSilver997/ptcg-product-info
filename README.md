# ptcg-product-info

Download all PTCG (Pokémon Trading Card Game) related product information from official websites and export to CSV.

## Features

- Scrapes product information from multiple official Pokémon TCG websites:
  - ~~Japan: https://www.pokemon-card.com/products/~~ (Requires Selenium - not yet implemented)
  - Hong Kong (English): https://asia.pokemon-card.com/hk-en/card-search/ ✓ Working (3 pages, ~41 expansions)
  - Hong Kong (Chinese): https://asia.pokemon-card.com/hk/card-search/ ✓ Working (7 pages, ~123 expansions)

- **Pagination support**: Automatically scrapes all available pages to get complete product listings

- Extracts the following product information:
  - Country/Region
  - Product name (series + expansion name)
  - ~~Price~~ (not available on current pages)
  - Release date (with datetime attribute)
  - Product code (extracted from URL)
  - Link to product details
  - **Image URL** (expansion package/box art)
  - ~~Include (what's included in the product)~~ (not available on current pages)
  - Card only status (set to "Yes" for all expansions)

- Exports all data to a timestamped CSV file (or custom filename via config)

**Note**: The Japan site loads products dynamically via JavaScript (using `<div id="ProductsApp">`). 
Selenium WebDriver support is required to scrape it, but is not yet implemented. Currently disabled in config.py.

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

Run the scraper:
```bash
python scraper.py
```

This will:
1. Scrape product information from all three websites
2. Generate a CSV file named `ptcg_products_YYYYMMDD_HHMMSS.csv` with all the collected data

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

The CSV file contains the following columns:
- `country` - Source country/region
- `product_name` - Name of the product (series + expansion name)
- `price` - Product price (currently not available)
- `release_date` - Release date (YYYY-MM-DD format)
- `code` - Product code (expansion code)
- `link` - URL to the product page
- `image_url` - URL to product image (package/box art)
- `include` - What's included in the product (currently not available)
- `card_only` - Whether it's cards only (typically "Yes" for expansions)

## Requirements

- Python 3.7+
- See `requirements.txt` for Python package dependencies

## Notes

- The scraper is designed to be respectful to the servers with appropriate delays between requests
- **Pagination support**: Automatically discovers and scrapes all available pages
  - Hong Kong EN: ~3 pages (~41 expansions)
  - Hong Kong ZH: ~7 pages (~123 expansions)
- Hong Kong sites: Scrapes expansion/product listings from the card search pages
  - Extracts: name, series, release date, code, link, and image URL
- **Japan site currently disabled**: Requires Selenium WebDriver to handle JavaScript-rendered content
  - The page uses Vue.js or similar framework with `<div id="ProductsApp">` that loads content dynamically
  - Implementing Selenium support would enable Japan scraping
- Some fields may be empty if the information is not available on the website
- Release dates are extracted from `<time>` elements with `datetime` attribute
- Product images are typically expansion package/box artwork in PNG format

## License

MIT License
