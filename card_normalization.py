#!/usr/bin/env python3
"""
Card normalization mapping for grouping reprints by function
"""

# Mapping of card names to normalized functional names
CARD_NORMALIZATION = {
    # Rare Candy - all printings have same function
    'ふしぎなアメ': 'rare_candy',
    
    # Hyper Ball - same function across printings
    'ハイパーボール': 'hyper_ball',
    
    # Professor's Research - same function (draw 7)
    '博士の研究': 'professors_research',
    
    # Boss's Orders - same function
    'ボスの指令': 'boss_orders',
    
    # Basic Energy cards - same function per type
    '基本炎エネルギー': 'basic_fire_energy',
    '基本水エネルギー': 'basic_water_energy',
    '基本雷エネルギー': 'basic_electric_energy',
    '基本草エネルギー': 'basic_grass_energy',
    '基本闘エネルギー': 'basic_fighting_energy',
    '基本超エネルギー': 'basic_psychic_energy',
    '基本悪エネルギー': 'basic_dark_energy',
    '基本鋼エネルギー': 'basic_metal_energy',
    
    # Other common cards
    'ネストボール': 'nest_ball',
    'ポケモンいれかえ': 'pokemon_switch',
    'ナンジャモ': 'nemona',
    'ポケギア3.0': 'pokegear_30',
    'エネルギーつけかえ': 'energy_switch',
    'エネルギー転送': 'energy_search',
    'すごいつりざお': 'super_rod',
    'ジャッジマン': 'judge',
}

def normalize_card_name(japanese_name):
    """Convert Japanese card name to normalized functional name"""
    return CARD_NORMALIZATION.get(japanese_name, japanese_name)

def get_functional_groups(cards):
    """Group cards by their functional name regardless of printing"""
    functional_groups = {}
    
    for card in cards:
        japanese_name = card.get('card_name', '')
        functional_name = normalize_card_name(japanese_name)
        
        if functional_name not in functional_groups:
            functional_groups[functional_name] = []
        functional_groups[functional_name].append(card)
    
    return functional_groups

# Example usage:
if __name__ == "__main__":
    # Test normalization
    test_names = ['ふしぎなアメ', 'ハイパーボール', '基本炎エネルギー', 'Unknown Card']
    
    for name in test_names:
        normalized = normalize_card_name(name)
        print(f"{name} -> {normalized}")