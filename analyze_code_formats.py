import json
import re

# Load card code cache
with open('card_code_cache.json', 'r', encoding='utf-8') as f:
    code_cache = json.load(f)

print('=== ANALYZING CARD CODE FORMATS ===')

# Get sample codes
codes = []
for card_id, code in list(code_cache.items())[:50]:  # First 50
    if code and isinstance(code, str):
        codes.append(code)

print(f'Analyzing {len(codes)} sample codes:')

# Analyze patterns
patterns = {
    r'^([A-Z]{2,3}\d+[a-z]?)\s+(\d+)/(\d+)$': 'Standard (SV8a 120/187)',
    r'^([A-Z]{2,4}-[A-Z]{1,3})\s+(\d+)/(\d+)$': 'Dash format (DPs-Sd 011/014)',
    r'^([A-Z]{2,3}\d+)\s+(\d+)/(\d+)$': 'No letter (BW1 049/053)',
    r'^([A-Z]{1,3})\s+(\d+)/(\d+)$': 'Short prefix (BW 049/053)',
    r'^([A-Z]{2,3}\d+[a-z]?)-([A-Z]{1,3})\s+(\d+)/(\d+)$': 'Complex (BW1-Bb 049/053)',
}

for code in codes[:20]:  # Show first 20
    print(f'Code: "{code}"')
    matched = False
    for pattern, desc in patterns.items():
        if re.match(pattern, code):
            print(f'  Matches: {desc}')
            matched = True
            break
    if not matched:
        print(f'  No match found')
    print()