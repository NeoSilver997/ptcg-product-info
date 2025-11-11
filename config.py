# PTCG Scraper Configuration
# Customize the behavior of the scraper

# Output settings
OUTPUT_FILENAME = "ptcg_products_japan.csv"  # Set to None for auto-timestamped filename
OUTPUT_ENCODING = "utf-8"

# Scraping settings
REQUEST_TIMEOUT = 30  # seconds
DELAY_BETWEEN_REQUESTS = 2  # seconds, be respectful to servers

# Website URLs (can be customized if URLs change)
JAPAN_URL = "https://www.pokemon-card.com/products/"
HONG_KONG_EN_URL = "https://asia.pokemon-card.com/hk-en/card-search/"
HONG_KONG_ZH_URL = "https://asia.pokemon-card.com/hk/card-search/"

# Enable/disable specific scrapers
SCRAPE_JAPAN = True  # Now uses Selenium for JavaScript-rendered content
SCRAPE_HONG_KONG_EN = False
SCRAPE_HONG_KONG_ZH = False

# User agent for requests
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

# Logging
LOG_LEVEL = "INFO"  # DEBUG, INFO, WARNING, ERROR, CRITICAL
