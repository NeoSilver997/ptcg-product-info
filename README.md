# ptcg-product-info

Download all PTCG (Pokémon Trading Card Game) related product information from official websites and export to CSV.

## Features

- Scrapes product information from multiple official Pokémon TCG websites:
  - Japan: https://www.pokemon-card.com/products/
  - Hong Kong (English): https://asia.pokemon-card.com/hk-en/card-search/
  - Hong Kong (Chinese): https://asia.pokemon-card.com/hk/card-search/

- Extracts the following product information:
  - Country
  - Product name
  - Price
  - Release date
  - Product code
  - Link
  - Include (what's included in the product)
  - Card only (whether it's cards only)

- Exports all data to a timestamped CSV file

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

## CSV Output Format

The CSV file contains the following columns:
- `country` - Source country/region
- `product_name` - Name of the product
- `price` - Product price
- `release_date` - Release date
- `code` - Product code
- `link` - URL to the product page
- `include` - What's included in the product
- `card_only` - Whether it's cards only

## Requirements

- Python 3.7+
- See `requirements.txt` for Python package dependencies

## Notes

- The scraper is designed to be respectful to the servers with appropriate delays between requests
- The actual structure of the websites may change over time, requiring updates to the scraper
- Some fields may be empty if the information is not available on the website

## License

MIT License
