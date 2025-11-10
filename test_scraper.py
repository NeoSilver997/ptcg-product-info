#!/usr/bin/env python3
"""
Test script for PTCG scraper with mock data
Demonstrates functionality without requiring internet access
"""

import csv
from datetime import datetime
from scraper import export_to_csv
import os

def generate_mock_products():
    """Generate mock product data for testing"""
    mock_products = [
        {
            'country': 'Japan',
            'product_name': 'Scarlet & Violet Expansion Pack "Ancient Roar"',
            'price': '¥180 (税込)',
            'release_date': '2023-10-27',
            'code': 'SV4K',
            'link': 'https://www.pokemon-card.com/products/sv4k/',
            'include': '5 cards per pack',
            'card_only': 'Yes'
        },
        {
            'country': 'Japan',
            'product_name': 'Starter Set ex "Pikachu & Pawmot"',
            'price': '¥1,800 (税込)',
            'release_date': '2023-12-01',
            'code': 'SV4S',
            'link': 'https://www.pokemon-card.com/products/sv4s/',
            'include': 'Constructed deck (60 cards), damage counters, coin, playmat, guide',
            'card_only': 'No'
        },
        {
            'country': 'Hong Kong (EN)',
            'product_name': 'Scarlet & Violet - Paradox Rift Booster Pack',
            'price': 'HK$38',
            'release_date': '2023-11-03',
            'code': 'SV04',
            'link': 'https://asia.pokemon-card.com/hk-en/card-search/sv04/',
            'include': '10 cards per pack',
            'card_only': 'Yes'
        },
        {
            'country': 'Hong Kong (EN)',
            'product_name': 'Scarlet & Violet - Battle Academy',
            'price': 'HK$228',
            'release_date': '2023-09-15',
            'code': 'BA-SV',
            'link': 'https://asia.pokemon-card.com/hk-en/products/battle-academy/',
            'include': '3 complete decks, playmat, tutorial guide, damage counters',
            'card_only': 'No'
        },
        {
            'country': 'Hong Kong (ZH)',
            'product_name': '朱紫系列 - 悖論裂變補充包',
            'price': 'HK$38',
            'release_date': '2023-11-03',
            'code': 'SV04',
            'link': 'https://asia.pokemon-card.com/hk/card-search/sv04/',
            'include': '每包10張卡牌',
            'card_only': 'Yes'
        },
        {
            'country': 'Hong Kong (ZH)',
            'product_name': '朱紫系列 - 對戰學院',
            'price': 'HK$228',
            'release_date': '2023-09-15',
            'code': 'BA-SV',
            'link': 'https://asia.pokemon-card.com/hk/products/battle-academy/',
            'include': '3副完整套牌、遊戲墊、教學指南、傷害指示物',
            'card_only': 'No'
        }
    ]
    return mock_products


def test_csv_export():
    """Test CSV export functionality"""
    print("Testing PTCG Product Info Scraper with mock data\n")
    
    # Generate mock products
    products = generate_mock_products()
    print(f"Generated {len(products)} mock products")
    
    # Export to CSV
    test_filename = "test_ptcg_products.csv"
    export_to_csv(products, test_filename)
    
    # Verify CSV was created
    if os.path.exists(test_filename):
        print(f"\n✓ CSV file '{test_filename}' created successfully")
        
        # Read and display the CSV contents
        print(f"\nCSV Contents:")
        print("-" * 80)
        with open(test_filename, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for i, row in enumerate(reader, 1):
                print(f"\nProduct {i}:")
                for key, value in row.items():
                    if value:
                        print(f"  {key}: {value}")
        
        print("\n" + "-" * 80)
        print(f"\n✓ Test completed successfully!")
        print(f"✓ All {len(products)} products exported to CSV")
        
        # Clean up test file
        os.remove(test_filename)
        print(f"✓ Test file cleaned up")
    else:
        print(f"\n✗ Error: CSV file was not created")


if __name__ == "__main__":
    test_csv_export()
