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

# Selenium imports for Japan site
try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.chrome.options import Options
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning("Selenium not available - Japan scraper will be disabled")

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
    
    @staticmethod
    def _format_hong_kong_date(date_str: str) -> str:
        """
        Convert Hong Kong date format to YYYY-MM-DD
        Input: "MM-DD-YYYY" (e.g., "11-14-2025")
        Output: "YYYY-MM-DD" (e.g., "2025-11-14")
        """
        try:
            import re
            # Check if it's MM-DD-YYYY format
            match = re.match(r'(\d{1,2})-(\d{1,2})-(\d{4})', date_str)
            if match:
                month = match.group(1).zfill(2)
                day = match.group(2).zfill(2)
                year = match.group(3)
                return f"{year}-{month}-{day}"
        except Exception as e:
            logger.warning(f"Error formatting Hong Kong date '{date_str}': {e}")
        
        return date_str  # Return original if parsing fails


class JapanPTCGScraper(PTCGScraper):
    """
    Scraper for https://www.pokemon-card.com/products/
    
    Uses Selenium WebDriver to handle JavaScript-rendered product listings.
    The site loads products dynamically into `<div class="product-card">` elements.
    """
    
    def __init__(self):
        super().__init__()
        self.base_url = "https://www.pokemon-card.com"
        self.products_url = JAPAN_URL
        self.country = "Japan"
    
    def scrape(self) -> List[Dict]:
        """Scrape product information from Japanese Pokemon Card website using Selenium"""
        
        if not SELENIUM_AVAILABLE:
            logger.error("Selenium is not installed. Cannot scrape Japan site.")
            logger.error("Install with: pip install selenium")
            return []
        
        products = []
        driver = None
        
        try:
            # Setup Chrome options
            chrome_options = Options()
            chrome_options.add_argument('--headless')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument(f'user-agent={USER_AGENT}')
            
            logger.info(f"Starting Selenium WebDriver for {self.products_url}")
            driver = webdriver.Chrome(options=chrome_options)
            driver.get(self.products_url)
            
            # Wait for products to load (give JavaScript time to render)
            time.sleep(5)
            
            # Load more products by clicking "もっと見る" button repeatedly
            page_num = 1
            while True:
                html = driver.page_source
                soup = BeautifulSoup(html, 'html.parser')
                
                # Find all product cards on current page
                product_cards = soup.find_all('div', class_='product-card')
                current_count = len(products)
                logger.info(f"Found {len(product_cards)} total products visible (page {page_num})")
                
                # Parse all visible cards
                for card in product_cards:
                    try:
                        product = self._parse_product_card(card, driver)
                        if product and product not in products:
                            products.append(product)
                    except Exception as e:
                        logger.warning(f"Error parsing product card: {e}")
                        continue
                
                new_products = len(products) - current_count
                logger.info(f"Parsed {new_products} new products on page {page_num}")
                
                # Look for "もっと見る" (See More) button
                try:
                    more_button = driver.find_element(By.LINK_TEXT, "もっと見る")
                    # Check if button is visible and clickable
                    if more_button.is_displayed():
                        logger.info("Clicking 'もっと見る' button to load more products...")
                        more_button.click()
                        time.sleep(3)  # Wait for new products to load
                        page_num += 1
                    else:
                        logger.info("No more pages to load")
                        break
                except Exception:
                    # Button not found or not clickable - no more pages
                    logger.info(f"No more pages after page {page_num}")
                    break
            
            logger.info(f"Scraped total of {len(products)} products from {page_num} page(s)")
                    
        except Exception as e:
            logger.error(f"Error scraping Japan site: {e}")
        finally:
            if driver:
                driver.quit()
        
        return products
    
    def _parse_product_card(self, card, driver=None) -> Dict:
        """Parse a product card element and fetch detail page"""
        product = {
            'country': self.country,
            'product_name': '',
            'price': '',
            'release_date': '',
            'code': '',
            'link': '',
            'image_url': '',
            'include': '',
            'card_only': ''
        }
        
        # Title
        title_div = card.find('div', class_='product-title')
        if title_div:
            product['product_name'] = title_div.get_text(strip=True)
        
        # Product type (拡張パック, 構築デッキ, etc.)
        type_div = card.find('div', class_='product-type')
        if type_div:
            product_type = type_div.get_text(strip=True)
            # Prepend type to name like Hong Kong scrapers do with series
            product['product_name'] = f"{product_type} {product['product_name']}"
        
        # Extract date and price from tables
        tables = card.find_all('div', class_='product-table')
        for table in tables:
            spans = table.find_all('span')
            if len(spans) == 2:
                label = spans[0].get_text(strip=True)
                value = spans[1].get_text(strip=True)
                
                if '販売日' in label:  # Release date
                    # Format: "2025年11月28日（金）" -> "2025-11-28"
                    product['release_date'] = self._format_japanese_date(value)
                elif '希望小売価格' in label or '価格' in label:  # Price
                    product['price'] = value
        
        # Image - extract code from filename
        img = card.find('img', class_='product-thumbnail')
        if img and img.get('src'):
            img_src = img.get('src')
            if img_src.startswith('http'):
                product['image_url'] = img_src
            else:
                product['image_url'] = self.base_url + img_src
            
            # Extract code from image filename (e.g., /products/2025/images/m2a.jpg -> m2a)
            if '/images/' in img_src:
                filename = img_src.split('/images/')[-1]
                code = filename.replace('.jpg', '').replace('.png', '')
                product['code'] = code
                
                # Build detail page link
                product['link'] = f"{self.base_url}/ex/{code}/"
        
        # Return None if no product name (essential field)
        if not product['product_name']:
            return None
            
        return product
    
    def _format_japanese_date(self, date_str: str) -> str:
        """
        Convert Japanese date format to YYYY-MM-DD
        Input: "2025年11月28日（金）" or "2025年 9月26日（金）"
        Output: "2025-11-28" or "2025-09-26"
        """
        try:
            import re
            # Extract year, month, day using regex
            match = re.search(r'(\d{4})年\s*(\d{1,2})月\s*(\d{1,2})日', date_str)
            if match:
                year = match.group(1)
                month = match.group(2).zfill(2)  # Pad with zero if single digit
                day = match.group(3).zfill(2)
                return f"{year}-{month}-{day}"
        except Exception as e:
            logger.warning(f"Error formatting date '{date_str}': {e}")
        
        return date_str  # Return original if parsing fails


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
            date_str = date_elem.get('datetime', '') or date_elem.get_text(strip=True)
            # Convert MM-DD-YYYY to YYYY-MM-DD
            product['release_date'] = self._format_hong_kong_date(date_str)
        
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
            date_str = date_elem.get('datetime', '') or date_elem.get_text(strip=True)
            # Convert MM-DD-YYYY to YYYY-MM-DD
            product['release_date'] = self._format_hong_kong_date(date_str)
        
        # Extract code from link if available (expansionCodes parameter)
        if product['link'] and 'expansionCodes=' in product['link']:
            try:
                code = product['link'].split('expansionCodes=')[1].split('&')[0]
                product['code'] = code
            except:
                pass
        
        return product if product['product_name'] or product['link'] else None


def export_to_csv(products: List[Dict], filename: str = None):
    """Export products to CSV file, sorted by release date"""
    if not filename:
        if OUTPUT_FILENAME:
            filename = OUTPUT_FILENAME
        else:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"ptcg_products_{timestamp}.csv"
    
    if not products:
        logger.warning("No products to export")
        return
    
    # Sort products by release date (newest first)
    def get_sort_key(product):
        date_str = product.get('release_date', '')
        if not date_str:
            return '9999-12-31'  # Put items without dates at the end
        
        # Try to parse date to ensure consistent sorting
        try:
            # Handle YYYY-MM-DD format (Japan and standardized)
            if '-' in date_str and len(date_str) >= 10:
                return date_str[:10]
            # Handle MM-DD-YYYY format (Hong Kong)
            elif '-' in date_str:
                parts = date_str.split('-')
                if len(parts) == 3:
                    return f"{parts[2]}-{parts[0].zfill(2)}-{parts[1].zfill(2)}"
        except:
            pass
        return date_str
    
    products.sort(key=get_sort_key, reverse=True)
    
    # Define CSV columns - added image_url field
    fieldnames = ['country', 'product_name', 'price', 'release_date', 'code', 'link', 'image_url', 'include', 'card_only']
    
    try:
        with open(filename, 'w', newline='', encoding=OUTPUT_ENCODING) as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(products)
        
        logger.info(f"Successfully exported {len(products)} products to {filename} (sorted by date)")
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
