import sqlite3

event_db = sqlite3.connect('ptcg_events.db')
main_db = sqlite3.connect(r'c:\AI_Server\Coding\PokemonDBByjules\PTCG_CardDB_Tc\pokemon_cards.db')

ec = event_db.cursor()
mc = main_db.cursor()

print("=== Creating Name-Based Mappings for Old Expansions ===\n")

# Common Japanese to Chinese name mappings for trainer cards
common_mappings = {
    'N': 'N',
    'ハイパーボール': '超級球',
    'すごいつりざお': '厲害釣竿',
    'ふしぎなアメ': '神奇糖果',
    'ポケモンいれかえ': '寶可夢替換',
    'ボスの指令': '老大的指令',
    '博士の研究': '博士的研究',
    'ポケギア3.0': '寶可齒輪3.0',
    'げんきのハチマキ': '元氣頭巾',
    'ツールスクラッパー': '道具廢除者',
    'ナンジャモ': '奇樹',
    'なかよしポフィン': '好友寶芬',
    'ふうせん': '氣球',
    'かるいし': '輕石',
    'ちからのハチマキ': '力量頭巾',
    'しんかのおこう': '進化之香',
    'せいなるはい': '聖灰',
    'あなぬけのヒモ': '逃生繩',
    'ポケモンキャッチャー': '寶可夢捕獲器',
    'エネルギーつけかえ': '能量轉移',
    'エネルギー回収': '能量回收',
    'ダブル無色エネルギー': '雙倍無色能量',
    'レスキュータンカ': '救援坦克',
    'ポケモン通信': '寶可夢通訊',
    'バトルサーチャー': '對戰搜尋器',
    'VS': '對戰搜尋器'
}

# Get unmapped cards
ec.execute("""
    SELECT DISTINCT dc.card_id, dc.card_name, dc.card_code
    FROM deck_cards dc
    LEFT JOIN card_mappings cm ON dc.card_id = cm.event_card_id
    WHERE cm.event_card_id IS NULL
""")

unmapped_cards = ec.fetchall()

linked_count = 0
failed_count = 0

for card_id, card_name, card_code in unmapped_cards:
    # Check if we have a common mapping
    if card_name in common_mappings:
        chinese_name = common_mappings[card_name]
        
        # Find the card in main DB
        mc.execute("""
            SELECT id, name, card_type
            FROM cards
            WHERE name = ?
            LIMIT 1
        """, (chinese_name,))
        
        match = mc.fetchone()
        
        if match:
            main_card_id, main_card_name, card_type = match
            
            try:
                ec.execute("""
                    INSERT OR REPLACE INTO card_mappings
                    (event_card_id, event_card_name, event_card_code,
                     main_card_id, main_card_name, main_expansion_code,
                     main_collector_number, match_type, match_confidence)
                    VALUES (?, ?, ?, ?, ?, '', '', 'name_common_trainer', 0.90)
                """, (card_id, card_name, card_code or '',
                      main_card_id, main_card_name))
                
                linked_count += 1
                print(f"✓ {card_name} → {main_card_name}")
            except Exception as e:
                failed_count += 1
                print(f"✗ Failed: {card_name} - {e}")
        else:
            # Try fuzzy match
            mc.execute("""
                SELECT id, name
                FROM cards
                WHERE name LIKE ?
                LIMIT 1
            """, (f'%{chinese_name}%',))
            
            fuzzy_match = mc.fetchone()
            
            if fuzzy_match:
                main_card_id, main_card_name = fuzzy_match
                
                try:
                    ec.execute("""
                        INSERT OR REPLACE INTO card_mappings
                        (event_card_id, event_card_name, event_card_code,
                         main_card_id, main_card_name, main_expansion_code,
                         main_collector_number, match_type, match_confidence)
                        VALUES (?, ?, ?, ?, ?, '', '', 'name_fuzzy_match', 0.80)
                    """, (card_id, card_name, card_code or '',
                          main_card_id, main_card_name))
                    
                    linked_count += 1
                    print(f"✓ {card_name} → {main_card_name} (fuzzy)")
                except Exception as e:
                    failed_count += 1

# Commit changes
event_db.commit()

print(f"\n{'='*60}")
print(f"✅ Successfully linked: {linked_count} cards")
print(f"❌ Failed: {failed_count} cards")

# Update statistics
ec.execute("SELECT COUNT(DISTINCT event_card_id) FROM card_mappings")
total_mapped = ec.fetchone()[0]

ec.execute("SELECT COUNT(DISTINCT card_id) FROM deck_cards")
total_cards = ec.fetchone()[0]

print(f"\n📊 Final Statistics:")
print(f"  Total unique cards: {total_cards}")
print(f"  Mapped cards: {total_mapped} ({total_mapped/total_cards*100:.1f}%)")
print(f"  Unmapped cards: {total_cards - total_mapped} ({(total_cards - total_mapped)/total_cards*100:.1f}%)")

event_db.close()
main_db.close()

print("\n✅ Done! Restart the server to see the changes.")
