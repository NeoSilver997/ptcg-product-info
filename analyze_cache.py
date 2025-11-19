import json

# Load cache
with open('card_code_cache.json', 'r', encoding='utf-8') as f:
    cache = json.load(f)

# Filter MA cards
ma_cards = []
svn_cards = []
svp_cards = []

for card_id, data in cache.items():
    if isinstance(data, dict):
        code = data.get('card_code', '')
        if code.startswith('MA '):
            ma_cards.append({
                'card_id': card_id,
                'card_name': data.get('card_name', ''),
                'card_code': code
            })
        elif code.startswith('SVN '):
            svn_cards.append({
                'card_id': card_id,
                'card_name': data.get('card_name', ''),
                'card_code': code
            })
        elif code.startswith('SV-P '):
            svp_cards.append({
                'card_id': card_id,
                'card_name': data.get('card_name', ''),
                'card_code': code
            })

print("=" * 60)
print("MISSING EXPANSION CARDS IN CACHE")
print("=" * 60)
print(f"\nMA expansion:  {len(ma_cards)} cards")
print(f"SVN expansion: {len(svn_cards)} cards")
print(f"SV-P promos:   {len(svp_cards)} cards")

print("\n" + "=" * 60)
print("SAMPLE MA CARDS:")
print("=" * 60)
for card in sorted(ma_cards, key=lambda x: x['card_code'])[:20]:
    print(f"{card['card_code']:15s} - {card['card_name']}")

print("\n" + "=" * 60)
print("SAMPLE SVN CARDS:")
print("=" * 60)
for card in sorted(svn_cards, key=lambda x: x['card_code'])[:15]:
    print(f"{card['card_code']:15s} - {card['card_name']}")
