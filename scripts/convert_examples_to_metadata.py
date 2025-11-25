import json, glob

files = glob.glob('llm_training_data/ptcg_training_data_full_*.json')

for f in files:
    print('Processing', f)
    with open(f, 'r', encoding='utf-8') as fh:
        data = json.load(fh)

    updated = False
    # Fields to move to metadata if present at top-level
    card_fields = set([
        'card_id', 'card_name', 'category', 'expansion', 'rarity', 'tournament_usage',
        'japanese_name', 'chinese_name', 'has_abilities', 'has_attacks', 'hp', 'attribute',
        'card_type', 'oracle_text', 'effect', 'attacks', 'attack', 'collector_number'
    ])

    for ex in data.get('examples', []):
        meta = ex.get('metadata', {}) or {}
        # Move instruction/input/output if present
        if 'instruction' in ex:
            meta['instruction'] = ex.pop('instruction')
        if 'input' in ex:
            meta['input'] = ex.pop('input')
        if 'output' in ex:
            meta['output'] = ex.pop('output')

        # Move any known card fields to metadata
        for fld in list(ex.keys()):
            if fld in card_fields:
                # Avoid overwriting existing metadata values unless missing
                if fld not in meta:
                    meta[fld] = ex.pop(fld)
                    updated = True
                else:
                    # Already in metadata, remove duplicate top-level
                    ex.pop(fld)
                    updated = True

        # Save metadata back to example
        if meta:
            ex['metadata'] = meta

    if updated:
        with open(f, 'w', encoding='utf-8') as fh:
            json.dump(data, fh, ensure_ascii=False, indent=2)
        print('Updated', f)
    else:
        print('No changes for', f)

print('Done')
