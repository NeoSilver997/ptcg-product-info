#!/usr/bin/env python3
"""
PTCG Product Info Scraper
Scrapes product information from Pokemon TCG websites and exports to CSV
"""

import csv
import logging
from datetime import datetime
from typing import List, Dict
import requests
from bs4 import BeautifulSoup
import time

# Import configuration
try:
    from config import (
        OUTPUT_FILENAME, OUTPUT_ENCODING, REQUEST_TIMEOUT, 
        DELAY_BETWEEN_REQUESTS, JAPAN_URL, HONG_KONG_EN_URL, 
        HONG_KONG_ZH_URL, SCRAPE_JAPAN, SCRAPE_HONG_KONG_EN, 
        SCRAPE_HONG_KONG_ZH, USER_AGENT, LOG_LEVEL
    )
except ImportError:
    # Default configuration if config.py doesn't exist
    OUTPUT_FILENAME = None
    OUTPUT_ENCODING = "utf-8"
    REQUEST_TIMEOUT = 30
    DELAY_BETWEEN_REQUESTS = 2
    JAPAN_URL = "https://www.pokemon-card.com/products/"
    HONG_KONG_EN_URL = "https://asia.pokemon-card.com/hk-en/card-search/"
    HONG_KONG_ZH_URL = "https://asia.pokemon-card.com/hk/card-search/"
    SCRAPE_JAPAN = True
    SCRAPE_HONG_KONG_EN = True
    SCRAPE_HONG_KONG_ZH = True
    USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    LOG_LEVEL = "INFO"

# Configure logging
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class PTCGScraper:
    """Base class for PTCG product scrapers"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': USER_AGENT
        })
        self.timeout = REQUEST_TIMEOUT
    
    def scrape(self) -> List[Dict]:
        """Override this method in subclasses"""
        raise NotImplementedError


class JapanPTCGScraper(PTCGScraper):
    """
    Scraper for https://www.pokemon-card.com/products/
    
    NOTE: The Japan site uses JavaScript to dynamically load product listings.
    The page has a <div id="ProductsApp"> that's populated by JavaScript after page load.
    This scraper requires Selenium WebDriver to execute JavaScript and wait for content.
    
    Current implementation uses requests library, which cannot execute JavaScript,
    so it will return empty results. To fix this:
    1. Implement Selenium WebDriver support
    2. Wait for #ProductsApp to populate with product items
    3. Parse the dynamically loaded HTML
    """
    
    def __init__(self):
        super().__init__()
        self.base_url = "https://www.pokemon-card.com"
        self.products_url = JAPAN_URL
        self.country = "Japan"
    
    def scrape(self) -> List[Dict]:
        """Scrape product information from Japanese Pokemon Card website
        
        WARNING: This method currently returns no products because the Japan site
        loads content dynamically via JavaScript. Selenium is required.
        """
        logger.warning(f"Japan scraper is disabled: {self.products_url} requires JavaScript execution (Selenium)")
        logger.warning("The page uses <div id='ProductsApp'> which is populated dynamically after page load")
        logger.warning("To enable Japan scraping: implement Selenium WebDriver support")
        return []
        
        # Old non-working code kept for reference:
        # products = []
        # try:
        #     response = self.session.get(self.products_url, timeout=30)
        #     response.raise_for_status()
        #     soup = BeautifulSoup(response.content, 'html.parser')
        #     # Product items are loaded via JavaScript, so soup will be empty
        # except Exception as e:
        #     logger.error(f"Error scraping Japan site: {e}")
        # return products


class HongKongENPTCGScraper(PTCGScraper):
    """Scraper for https://asia.pokemon-card.com/hk-en/card-search/"""
    
    def __init__(self):
        super().__init__()
        self.base_url = "https://asia.pokemon-card.com"
        self.products_url = HONG_KONG_EN_URL
        self.country = "Hong Kong (EN)"
    
    def scrape(self) -> List[Dict]:
        """Scrape product information from Hong Kong EN Pokemon Card website with pagination support"""
        logger.info(f"Scraping {self.products_url}")
        products = []
        page_number = 1
        
        while True:
            try:
                # Construct URL with page parameter
                if page_number == 1:
                    page_url = self.products_url
                else:
                    page_url = f"{self.products_url}?pageNo={page_number}"
                
                logger.info(f"Fetching page {page_number}: {page_url}")
                response = self.session.get(page_url, timeout=self.timeout)
                response.raise_for_status()
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Find the expansionList - this is where actual products are listed
                expansion_list = soup.find('ul', class_='expansionList')
                
                if not expansion_list:
                    logger.warning(f"Could not find expansionList on page {page_number}")
                    break
                
                # Find all expansion/product items
                product_items = expansion_list.find_all('li', class_='expansion')
                
                if not product_items:
                    logger.info(f"No products found on page {page_number}, stopping pagination")
                    break
                
                logger.info(f"Found {len(product_items)} expansion items on page {page_number}")
                
                # Debug: Log first item structure
                if product_items and logger.isEnabledFor(logging.DEBUG) and page_number == 1:
                    logger.debug(f"First HK EN item HTML:\n{product_items[0].prettify()[:500]}")
                
                for item in product_items:
                    try:
                        product_data = self._parse_product_item(item)
                        if product_data:
                            products.append(product_data)
                        else:
                            logger.debug(f"HK EN: Parsed product returned None")
                    except Exception as e:
                        logger.warning(f"Error parsing product item: {e}")
                        continue
                
                # Check for next page
                pagination = soup.find('nav', class_='pagination')
                if pagination:
                    next_button = pagination.find('li', class_='paginationItem next')
                    if next_button and next_button.find('a'):
                        page_number += 1
                        time.sleep(1)  # Small delay between pages to be respectful
                    else:
                        logger.info(f"No more pages after page {page_number}")
                        break
                else:
                    # No pagination found, this is the only page
                    break
                
            except Exception as e:
                logger.error(f"Error scraping Hong Kong EN site page {page_number}: {e}")
                break
        
        logger.info(f"Scraped total of {len(products)} products from {page_number} page(s)")
        return products
    
    def _parse_product_item(self, item) -> Dict:
        """Parse a single expansion item from Hong Kong site"""
        product = {
            'country': self.country,
            'product_name': '',
            'price': '',
            'release_date': '',
            'code': '',
            'link': '',
            'image_url': '',
            'include': '',
            'card_only': 'Yes'  # Expansions are typically card packs
        }
        
        # Find product/expansion title (in h3 with class expansionTitle)
        title_elem = item.find('h3', class_='expansionTitle')
        if title_elem:
            product['product_name'] = title_elem.get_text(strip=True)
        
        # Find series name
        series_elem = item.find('span', class_='series')
        if series_elem:
            series_name = series_elem.get_text(strip=True)
            # Prepend series to product name
            if product['product_name']:
                product['product_name'] = f"{series_name} - {product['product_name']}"
            else:
                product['product_name'] = series_name
        
        # Find link
        link_elem = item.find('a', class_='expansionLink', href=True)
        if link_elem:
            href = link_elem['href']
            if href.startswith('http'):
                product['link'] = href
            else:
                product['link'] = self.base_url + href
        
        # Find image URL
        img_elem = item.find('img', src=True)
        if img_elem:
            img_src = img_elem['src']
            if img_src.startswith('http'):
                product['image_url'] = img_src
            else:
                product['image_url'] = self.base_url + img_src
        
        # Find release date (in <time> tag)
        date_elem = item.find('time', class_=lambda x: x and 'date' in str(x).lower())
        if date_elem:
            # Try to get datetime attribute first, then text content
            product['release_date'] = date_elem.get('datetime', '') or date_elem.get_text(strip=True)
        
        # Extract code from link if available (expansionCodes parameter)
        if product['link'] and 'expansionCodes=' in product['link']:
            try:
                code = product['link'].split('expansionCodes=')[1].split('&')[0]
                product['code'] = code
            except:
                pass
        
        return product if product['product_name'] or product['link'] else None


class HongKongZHPTCGScraper(PTCGScraper):
    """Scraper for https://asia.pokemon-card.com/hk/card-search/"""
    
    def __init__(self):
        super().__init__()
        self.base_url = "https://asia.pokemon-card.com"
        self.products_url = HONG_KONG_ZH_URL
        self.country = "Hong Kong (ZH)"
    
    def scrape(self) -> List[Dict]:
        """Scrape product information from Hong Kong ZH Pokemon Card website with pagination support"""
        logger.info(f"Scraping {self.products_url}")
        products = []
        page_number = 1
        
        while True:
            try:
                # Construct URL with page parameter
                if page_number == 1:
                    page_url = self.products_url
                else:
                    page_url = f"{self.products_url}?pageNo={page_number}"
                
                logger.info(f"Fetching page {page_number}: {page_url}")
                response = self.session.get(page_url, timeout=self.timeout)
                response.raise_for_status()
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Find the expansionList - this is where actual products are listed
                expansion_list = soup.find('ul', class_='expansionList')
                
                if not expansion_list:
                    logger.warning(f"Could not find expansionList on page {page_number}")
                    break
                
                # Find all expansion/product items
                product_items = expansion_list.find_all('li', class_='expansion')
                
                if not product_items:
                    logger.info(f"No products found on page {page_number}, stopping pagination")
                    break
                
                logger.info(f"Found {len(product_items)} expansion items on page {page_number}")
                
                # Debug: Log first item structure
                if product_items and logger.isEnabledFor(logging.DEBUG) and page_number == 1:
                    logger.debug(f"First HK ZH item HTML:\n{product_items[0].prettify()[:500]}")
                
                for item in product_items:
                    try:
                        product_data = self._parse_product_item(item)
                        if product_data:
                            products.append(product_data)
                        else:
                            logger.debug(f"HK ZH: Parsed product returned None")
                    except Exception as e:
                        logger.warning(f"Error parsing product item: {e}")
                        continue
                
                # Check for next page
                pagination = soup.find('nav', class_='pagination')
                if pagination:
                    next_button = pagination.find('li', class_='paginationItem next')
                    if next_button and next_button.find('a'):
                        page_number += 1
                        time.sleep(1)  # Small delay between pages to be respectful
                    else:
                        logger.info(f"No more pages after page {page_number}")
                        break
                else:
                    # No pagination found, this is the only page
                    break
                
            except Exception as e:
                logger.error(f"Error scraping Hong Kong ZH site page {page_number}: {e}")
                break
        
        logger.info(f"Scraped total of {len(products)} products from {page_number} page(s)")
        return products
    
    def _parse_product_item(self, item) -> Dict:
        """Parse a single expansion item from Hong Kong site"""
        product = {
            'country': self.country,
            'product_name': '',
            'price': '',
            'release_date': '',
            'code': '',
            'link': '',
            'image_url': '',
            'include': '',
            'card_only': 'Yes'  # Expansions are typically card packs
        }
        
        # Find product/expansion title (in h3 with class expansionTitle)
        title_elem = item.find('h3', class_='expansionTitle')
        if title_elem:
            product['product_name'] = title_elem.get_text(strip=True)
        
        # Find series name
        series_elem = item.find('span', class_='series')
        if series_elem:
            series_name = series_elem.get_text(strip=True)
            # Prepend series to product name
            if product['product_name']:
                product['product_name'] = f"{series_name} - {product['product_name']}"
            else:
                product['product_name'] = series_name
        
        # Find link
        link_elem = item.find('a', class_='expansionLink', href=True)
        if link_elem:
            href = link_elem['href']
            if href.startswith('http'):
                product['link'] = href
            else:
                product['link'] = self.base_url + href
        
        # Find image URL
        img_elem = item.find('img', src=True)
        if img_elem:
            img_src = img_elem['src']
            if img_src.startswith('http'):
                product['image_url'] = img_src
            else:
                product['image_url'] = self.base_url + img_src
        
        # Find release date (in <time> tag)
        date_elem = item.find('time', class_=lambda x: x and 'date' in str(x).lower())
        if date_elem:
            # Try to get datetime attribute first, then text content
            product['release_date'] = date_elem.get('datetime', '') or date_elem.get_text(strip=True)
        
        # Extract code from link if available (expansionCodes parameter)
        if product['link'] and 'expansionCodes=' in product['link']:
            try:
                code = product['link'].split('expansionCodes=')[1].split('&')[0]
                product['code'] = code
            except:
                pass
        
        return product if product['product_name'] or product['link'] else None


def export_to_csv(products: List[Dict], filename: str = None):
    """Export products to CSV file"""
    if not filename:
        if OUTPUT_FILENAME:
            filename = OUTPUT_FILENAME
        else:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"ptcg_products_{timestamp}.csv"
    
    if not products:
        logger.warning("No products to export")
        return
    
    # Define CSV columns - added image_url field
    fieldnames = ['country', 'product_name', 'price', 'release_date', 'code', 'link', 'image_url', 'include', 'card_only']
    
    try:
        with open(filename, 'w', newline='', encoding=OUTPUT_ENCODING) as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(products)
        
        logger.info(f"Successfully exported {len(products)} products to {filename}")
    except Exception as e:
        logger.error(f"Error exporting to CSV: {e}")


def main():
    """Main function to orchestrate scraping and export"""
    logger.info("Starting PTCG Product Info Scraper")
    
    all_products = []
    
    # Scrape Japan site
    if SCRAPE_JAPAN:
        japan_scraper = JapanPTCGScraper()
        japan_products = japan_scraper.scrape()
        all_products.extend(japan_products)
        logger.info(f"Scraped {len(japan_products)} products from Japan site")
        time.sleep(DELAY_BETWEEN_REQUESTS)  # Be respectful to the server
    
    # Scrape Hong Kong EN site
    if SCRAPE_HONG_KONG_EN:
        hk_en_scraper = HongKongENPTCGScraper()
        hk_en_products = hk_en_scraper.scrape()
        all_products.extend(hk_en_products)
        logger.info(f"Scraped {len(hk_en_products)} products from Hong Kong EN site")
        time.sleep(DELAY_BETWEEN_REQUESTS)  # Be respectful to the server
    
    # Scrape Hong Kong ZH site
    if SCRAPE_HONG_KONG_ZH:
        hk_zh_scraper = HongKongZHPTCGScraper()
        hk_zh_products = hk_zh_scraper.scrape()
        all_products.extend(hk_zh_products)
        logger.info(f"Scraped {len(hk_zh_products)} products from Hong Kong ZH site")
    
    # Export to CSV
    logger.info(f"Total products scraped: {len(all_products)}")
    export_to_csv(all_products)
    
    logger.info("Scraping completed!")


if __name__ == "__main__":
    main()
