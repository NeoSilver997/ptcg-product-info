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

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class PTCGScraper:
    """Base class for PTCG product scrapers"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def scrape(self) -> List[Dict]:
        """Override this method in subclasses"""
        raise NotImplementedError


class JapanPTCGScraper(PTCGScraper):
    """Scraper for https://www.pokemon-card.com/products/"""
    
    def __init__(self):
        super().__init__()
        self.base_url = "https://www.pokemon-card.com"
        self.products_url = f"{self.base_url}/products/"
        self.country = "Japan"
    
    def scrape(self) -> List[Dict]:
        """Scrape product information from Japanese Pokemon Card website"""
        logger.info(f"Scraping {self.products_url}")
        products = []
        
        try:
            response = self.session.get(self.products_url, timeout=30)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Find all product items
            # The structure may vary, so we'll look for common patterns
            product_items = soup.find_all(['article', 'div'], class_=lambda x: x and ('product' in x.lower() or 'item' in x.lower()))
            
            if not product_items:
                # Try alternative structure
                product_items = soup.find_all('li', class_=lambda x: x and 'product' in str(x).lower())
            
            logger.info(f"Found {len(product_items)} potential product items")
            
            for item in product_items:
                try:
                    product_data = self._parse_product_item(item)
                    if product_data:
                        products.append(product_data)
                except Exception as e:
                    logger.warning(f"Error parsing product item: {e}")
                    continue
            
        except Exception as e:
            logger.error(f"Error scraping Japan site: {e}")
        
        return products
    
    def _parse_product_item(self, item) -> Dict:
        """Parse a single product item"""
        product = {
            'country': self.country,
            'product_name': '',
            'price': '',
            'release_date': '',
            'code': '',
            'link': '',
            'include': '',
            'card_only': ''
        }
        
        # Try to find product name
        name_elem = item.find(['h2', 'h3', 'h4', 'a', 'span'], class_=lambda x: x and ('title' in str(x).lower() or 'name' in str(x).lower()))
        if name_elem:
            product['product_name'] = name_elem.get_text(strip=True)
        
        # Try to find link
        link_elem = item.find('a', href=True)
        if link_elem:
            href = link_elem['href']
            if href.startswith('http'):
                product['link'] = href
            else:
                product['link'] = self.base_url + href
        
        # Try to find price
        price_elem = item.find(['span', 'div', 'p'], class_=lambda x: x and 'price' in str(x).lower())
        if price_elem:
            product['price'] = price_elem.get_text(strip=True)
        
        # Try to find release date
        date_elem = item.find(['span', 'div', 'p', 'time'], class_=lambda x: x and ('date' in str(x).lower() or 'release' in str(x).lower()))
        if date_elem:
            product['release_date'] = date_elem.get_text(strip=True)
        
        # Try to find product code
        code_elem = item.find(['span', 'div', 'p'], class_=lambda x: x and 'code' in str(x).lower())
        if code_elem:
            product['code'] = code_elem.get_text(strip=True)
        
        return product if product['product_name'] or product['link'] else None


class HongKongENPTCGScraper(PTCGScraper):
    """Scraper for https://asia.pokemon-card.com/hk-en/card-search/"""
    
    def __init__(self):
        super().__init__()
        self.base_url = "https://asia.pokemon-card.com"
        self.products_url = f"{self.base_url}/hk-en/card-search/"
        self.country = "Hong Kong (EN)"
    
    def scrape(self) -> List[Dict]:
        """Scrape product information from Hong Kong EN Pokemon Card website"""
        logger.info(f"Scraping {self.products_url}")
        products = []
        
        try:
            response = self.session.get(self.products_url, timeout=30)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Find all product/card items
            product_items = soup.find_all(['article', 'div', 'li'], class_=lambda x: x and ('card' in str(x).lower() or 'product' in str(x).lower()))
            
            logger.info(f"Found {len(product_items)} potential product items")
            
            for item in product_items:
                try:
                    product_data = self._parse_product_item(item)
                    if product_data:
                        products.append(product_data)
                except Exception as e:
                    logger.warning(f"Error parsing product item: {e}")
                    continue
            
        except Exception as e:
            logger.error(f"Error scraping Hong Kong EN site: {e}")
        
        return products
    
    def _parse_product_item(self, item) -> Dict:
        """Parse a single product item"""
        product = {
            'country': self.country,
            'product_name': '',
            'price': '',
            'release_date': '',
            'code': '',
            'link': '',
            'include': '',
            'card_only': ''
        }
        
        # Try to find product name
        name_elem = item.find(['h2', 'h3', 'h4', 'a', 'span'], class_=lambda x: x and ('title' in str(x).lower() or 'name' in str(x).lower()))
        if name_elem:
            product['product_name'] = name_elem.get_text(strip=True)
        
        # Try to find link
        link_elem = item.find('a', href=True)
        if link_elem:
            href = link_elem['href']
            if href.startswith('http'):
                product['link'] = href
            else:
                product['link'] = self.base_url + href
        
        # Try to find price
        price_elem = item.find(['span', 'div', 'p'], class_=lambda x: x and 'price' in str(x).lower())
        if price_elem:
            product['price'] = price_elem.get_text(strip=True)
        
        # Try to find release date
        date_elem = item.find(['span', 'div', 'p', 'time'], class_=lambda x: x and ('date' in str(x).lower() or 'release' in str(x).lower()))
        if date_elem:
            product['release_date'] = date_elem.get_text(strip=True)
        
        # Try to find product code
        code_elem = item.find(['span', 'div', 'p'], class_=lambda x: x and 'code' in str(x).lower())
        if code_elem:
            product['code'] = code_elem.get_text(strip=True)
        
        return product if product['product_name'] or product['link'] else None


class HongKongZHPTCGScraper(PTCGScraper):
    """Scraper for https://asia.pokemon-card.com/hk/card-search/"""
    
    def __init__(self):
        super().__init__()
        self.base_url = "https://asia.pokemon-card.com"
        self.products_url = f"{self.base_url}/hk/card-search/"
        self.country = "Hong Kong (ZH)"
    
    def scrape(self) -> List[Dict]:
        """Scrape product information from Hong Kong ZH Pokemon Card website"""
        logger.info(f"Scraping {self.products_url}")
        products = []
        
        try:
            response = self.session.get(self.products_url, timeout=30)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Find all product/card items
            product_items = soup.find_all(['article', 'div', 'li'], class_=lambda x: x and ('card' in str(x).lower() or 'product' in str(x).lower()))
            
            logger.info(f"Found {len(product_items)} potential product items")
            
            for item in product_items:
                try:
                    product_data = self._parse_product_item(item)
                    if product_data:
                        products.append(product_data)
                except Exception as e:
                    logger.warning(f"Error parsing product item: {e}")
                    continue
            
        except Exception as e:
            logger.error(f"Error scraping Hong Kong ZH site: {e}")
        
        return products
    
    def _parse_product_item(self, item) -> Dict:
        """Parse a single product item"""
        product = {
            'country': self.country,
            'product_name': '',
            'price': '',
            'release_date': '',
            'code': '',
            'link': '',
            'include': '',
            'card_only': ''
        }
        
        # Try to find product name
        name_elem = item.find(['h2', 'h3', 'h4', 'a', 'span'], class_=lambda x: x and ('title' in str(x).lower() or 'name' in str(x).lower()))
        if name_elem:
            product['product_name'] = name_elem.get_text(strip=True)
        
        # Try to find link
        link_elem = item.find('a', href=True)
        if link_elem:
            href = link_elem['href']
            if href.startswith('http'):
                product['link'] = href
            else:
                product['link'] = self.base_url + href
        
        # Try to find price
        price_elem = item.find(['span', 'div', 'p'], class_=lambda x: x and 'price' in str(x).lower())
        if price_elem:
            product['price'] = price_elem.get_text(strip=True)
        
        # Try to find release date
        date_elem = item.find(['span', 'div', 'p', 'time'], class_=lambda x: x and ('date' in str(x).lower() or 'release' in str(x).lower()))
        if date_elem:
            product['release_date'] = date_elem.get_text(strip=True)
        
        # Try to find product code
        code_elem = item.find(['span', 'div', 'p'], class_=lambda x: x and 'code' in str(x).lower())
        if code_elem:
            product['code'] = code_elem.get_text(strip=True)
        
        return product if product['product_name'] or product['link'] else None


def export_to_csv(products: List[Dict], filename: str = None):
    """Export products to CSV file"""
    if not filename:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"ptcg_products_{timestamp}.csv"
    
    if not products:
        logger.warning("No products to export")
        return
    
    # Define CSV columns
    fieldnames = ['country', 'product_name', 'price', 'release_date', 'code', 'link', 'include', 'card_only']
    
    try:
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
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
    japan_scraper = JapanPTCGScraper()
    japan_products = japan_scraper.scrape()
    all_products.extend(japan_products)
    logger.info(f"Scraped {len(japan_products)} products from Japan site")
    time.sleep(2)  # Be respectful to the server
    
    # Scrape Hong Kong EN site
    hk_en_scraper = HongKongENPTCGScraper()
    hk_en_products = hk_en_scraper.scrape()
    all_products.extend(hk_en_products)
    logger.info(f"Scraped {len(hk_en_products)} products from Hong Kong EN site")
    time.sleep(2)  # Be respectful to the server
    
    # Scrape Hong Kong ZH site
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
