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
    
    def _fetch_price_from_detail_page(self, code: str, language: str = 'hk') -> str:
        """
        Fetch price from Hong Kong special detail page
        Args:
            code: Product code (e.g., 'm1', 'm2', 'sv10')
            language: 'hk' for Chinese or 'hk-en' for English
        Returns:
            Price string (e.g., '12元') or empty string if not found
        """
        import re
        
        if not code:
            return ''
        
        # Convert code to lowercase for URL
        code_lower = code.lower()
        detail_url = f"https://asia.pokemon-card.com/{language}/archive/special/card/{code_lower}/"
        
        try:
            response = self.session.get(detail_url, timeout=self.timeout)
            
            # Check if page exists
            if response.status_code == 404:
                logger.debug(f"No detail page found for code {code}")
                return ''
            
            response.raise_for_status()
            response.encoding = 'utf-8'
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find the product section
            section = soup.find('section', class_='section-product')
            if not section:
                logger.debug(f"No product section found on detail page for {code}")
                return ''
            
            # Try Method 1: Look for data-product div (M2 style)
            data_product = section.find('div', class_='data-product')
            if data_product:
                text = data_product.get_text()
                price_match = re.search(r'建議零售價[：:]\s*(\d+)元', text)
                if price_match:
                    price = f"{price_match.group(1)}元"
                    logger.info(f"Found price for {code}: {price}")
                    return price
            
            # Try Method 2: Look for box-red containers (SV10 style)
            box_red = section.find('div', class_='box-red')
            if box_red:
                # Look for <p> tag with price
                p_tags = box_red.find_all('p')
                for p in p_tags:
                    text = p.get_text()
                    price_match = re.search(r'建議零售價[：:]\s*(\d+)元', text)
                    if price_match:
                        price = f"{price_match.group(1)}元"
                        logger.info(f"Found price for {code}: {price}")
                        return price
            
            # Try Method 3: Search entire section for first price mention
            section_text = section.get_text()
            price_match = re.search(r'建議零售價[：:]\s*(\d+)元', section_text)
            if price_match:
                price = f"{price_match.group(1)}元"
                logger.info(f"Found price for {code}: {price}")
                return price
            
            logger.debug(f"No price found on detail page for {code}")
            return ''
            
        except Exception as e:
            logger.debug(f"Error fetching detail page for {code}: {e}")
            return ''


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
        """Scrape products from Japan site using API endpoint"""
        products = []
        
        try:
            # Use the API endpoint for ALL products (no filter)
            api_url = "https://www.pokemon-card.com/products/resultAPI.php"
            params = {
                'page': 1
            }
            
            logger.info(f"Fetching ALL Japan products from API: {api_url}")
            
            # First request to get total pages
            response = self.session.get(api_url, params=params, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()
            
            max_page = data.get('maxPage', 1)
            logger.info(f"Total pages available: {max_page}")
            
            # Loop through all pages
            for page_num in range(1, max_page + 1):
                params['page'] = page_num
                logger.info(f"Fetching page {page_num}/{max_page}...")
                
                response = self.session.get(api_url, params=params, timeout=self.timeout)
                response.raise_for_status()
                data = response.json()
                
                if data.get('result') != 1:
                    logger.warning(f"API returned error on page {page_num}: {data.get('errMsg')}")
                    continue
                
                page_products = data.get('products', [])
                logger.info(f"Page {page_num}: Found {len(page_products)} products")
                
                for item in page_products:
                    try:
                        product = self._parse_api_product(item)
                        if product:
                            products.append(product)
                    except Exception as e:
                        logger.warning(f"Error parsing product: {e}")
                        continue
                
                # Small delay between requests
                if page_num < max_page:
                    time.sleep(1)
            
            logger.info(f"Scraped total of {len(products)} products from {max_page} page(s)")
                    
        except Exception as e:
            logger.error(f"Error scraping Japan site: {e}")
        
        return products
    
    def _parse_api_product(self, item: Dict) -> Dict:
        """Parse a product from API response - saves ALL available fields"""
        product = {
            'country': self.country,
            'product_name': '',
            'price': '',
            'release_date': '',
            'code': '',
            'link': '',
            'image_url': '',
            'include': '',
            'card_only': '',
            # Additional API fields
            'product_type': '',
            'beginner_flag': '',
            'stores_available': '',
            'link_card_list': '',
            'link_pokemon_center': ''
        }
        
        # Title and type
        product_type = item.get('productType', '')
        product_title = item.get('productTitle', '')
        product['product_type'] = product_type  # Save original type
        
        if product_type and product_title:
            product['product_name'] = f"{product_type} {product_title}"
        elif product_title:
            product['product_name'] = product_title
        
        # Price
        product['price'] = item.get('priceTxt', '')
        
        # Release date - format: "2025年11月28日（金）"
        release_date = item.get('releaseDate', '')
        if release_date:
            product['release_date'] = self._format_japanese_date(release_date)
        
        # Image URL
        thumbs_img = item.get('tumbsImg', '')
        if thumbs_img:
            if thumbs_img.startswith('http'):
                product['image_url'] = thumbs_img
            else:
                product['image_url'] = self.base_url + thumbs_img
            
            # Extract code from image filename (e.g., /products/2025/images/m2a.jpg -> m2a)
            if '/images/' in thumbs_img:
                filename = thumbs_img.split('/images/')[-1]
                code = filename.replace('.jpg', '').replace('.png', '')
                product['code'] = code
        
        # Detail page link
        detail_link = item.get('link_detailPage', '')
        if detail_link:
            if detail_link.startswith('http'):
                product['link'] = detail_link
            else:
                product['link'] = self.base_url + detail_link
        
        # Include (description)
        description = item.get('description', '')
        if description:
            # Clean up the description (remove newlines and extra spaces)
            product['include'] = description.replace('\n', ' ').strip()
        
        # Additional API fields
        product['beginner_flag'] = str(item.get('beginnerFlg', ''))
        product['stores_available'] = item.get('storesAvailable', '')
        
        # Card list link
        card_list = item.get('link_cardList', '')
        if card_list:
            if card_list.startswith('http'):
                product['link_card_list'] = card_list
            else:
                product['link_card_list'] = self.base_url + card_list if card_list else ''
        
        # Pokemon Center link
        pokemon_center = item.get('link_pokemonCenter', '')
        if pokemon_center:
            if pokemon_center.startswith('http'):
                product['link_pokemon_center'] = pokemon_center
            else:
                product['link_pokemon_center'] = self.base_url + pokemon_center if pokemon_center else ''
        
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
                
                # Try to fetch price from detail page (EN site uses 'hk-en')
                price = self._fetch_price_from_detail_page(code, 'hk-en')
                if price:
                    product['price'] = price
                    
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
                
                # Try to fetch price from detail page (ZH site uses 'hk')
                price = self._fetch_price_from_detail_page(code, 'hk')
                if price:
                    product['price'] = price
                    
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
    
    # Define CSV columns - includes all API fields
    fieldnames = [
        'country', 'product_name', 'price', 'release_date', 'code', 'link', 
        'image_url', 'include', 'card_only', 'product_type', 'beginner_flag', 
        'stores_available', 'link_card_list', 'link_pokemon_center'
    ]
    
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
