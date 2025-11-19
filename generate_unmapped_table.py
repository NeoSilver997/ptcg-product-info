"""
Generate comprehensive table of all unmapped cards with Chinese translations
"""
import sqlite3
import csv

# Connect to databases
conn_event = sqlite3.connect('ptcg_events.db')
conn_main = sqlite3.connect(r'c:\AI_Server\Coding\PokemonDBByjules\PTCG_CardDB_Tc\pokemon_cards.db')

cursor_event = conn_event.cursor()
cursor_main = conn_main.cursor()

# Common card name translations (Japanese → Chinese)
COMMON_TRANSLATIONS = {
    # Trainers
    'ボスの指令': '老大的指令',
    'ナンジャモ': '奇樹',
    'ペパー': '派帕',
    '博士の研究': '博士的研究',
    'ジャッジマン': '裁判員',
    'ハイパーボール': '高級球',
    'ネストボール': '巢穴球',
    'ふしぎなアメ': '神奇糖果',
    'カウンターキャッチャー': '反擊捕捉器',
    'すごいつりざお': '厲害釣竿',
    'ポケモンいれかえ': '寶可夢替換',
    'ポケギア3.0': '寶可齒輪3.0',
    'なかよしポフィン': '好友寶芬',
    'エネルギーつけかえ': '能量轉移',
    'エネルギー回収': '能量回收',
    'スーパーエネルギー回収': '超級能量回收',
    'エネルギー転送': '能量輸送',
    'ふうせん': '氣球',
    '勇気のおまもり': '勇氣護符',
    'リーリエの決心': '莉莉艾的決心',
    'ボウルタウン': '寶可夢中心小鎮',
    '夜のタンカ': '夜之擔架',
    'タウンデパート': '城鎮百貨公司',
    'ゼロの大空洞': '零之大空洞',
    'ジェットエネルギー': '噴射能量',
    'ルミナスエネルギー': '光明能量',
    'リバーサルエネルギー': '逆轉能量',
    'ミストエネルギー': '薄霧能量',
    '大地の器': '大地之器',
    
    # Pokemon
    'カルボウ': '炭小侍',
    'ソウブレイズex': '蒼炎刃鬼ex',
    'ヒトカゲ': '小火龍',
    'マシマシラ': '願增猿',
    'サーナイトex': '沙奈朵ex',
    'イキリンコex': '怒鸚哥ex',
    'ラティアスex': '拉帝亞斯ex',
    'ゴルダック': '哥達鴨',
    'コダック': '可達鴨',
    'ドラパルトex': '多龍巴魯托ex',
    'ピカチュウex': '皮卡丘ex',
    'リザードンex': '噴火龍ex',
    'ミュウツーex': '超夢ex',
    'ミライドン': '密勒頓',
    'ハバタクカミ': '振翼髮',
    'ジュラルドン': '鋁鋼龍',
    'ハッサムex': '巨鉗螳螂ex',
    'ミミッキュ': '謎擬Ｑ',
    'クヌギダマ': '榛果球',
    'ビクティニ': '比克提尼',
    'ルチャブル': '摔角鷹人',
    'コレクレー': '索財靈',
    'クレッフィ': '鑰圈兒',
    'メタモン': '百變怪',
    'ヨルノズク': '夜巨鷹',
    
    # ACE SPEC (untranslated)
    'パーフェクトミキサー': 'Perfect Mixer (完美混和器)',
    'つりざおMAX': 'Fishing Rod MAX (最強釣竿)',
    'ミラクルインカム': 'Miracle Income (奇蹟收入)',
    'スクランブルスイッチ': 'Scramble Switch (緊急切換)',
    'トレジャーガジェット': 'Treasure Gadget (寶藏小工具)',
}

print("=" * 120)
print("UNMAPPED CARDS - COMPREHENSIVE TABLE")
print("=" * 120)

# Get all unmapped cards with deck counts
cursor_event.execute("""
    SELECT 
        dc.card_name,
        dc.card_code,
        COUNT(DISTINCT dc.deck_id) as deck_count,
        SUM(dc.quantity) as total_quantity
    FROM deck_cards dc
    LEFT JOIN card_mappings cm ON dc.card_id = cm.event_card_id
    WHERE cm.event_card_id IS NULL
    GROUP BY dc.card_name, dc.card_code
    ORDER BY deck_count DESC
""")

unmapped_cards = cursor_event.fetchall()

print(f"\nTotal Unmapped Card Types: {len(unmapped_cards)}")
print(f"Total Unmapped Card Instances: {sum(row[3] for row in unmapped_cards):,}\n")

# Output to console
print(f"{'Rank':<6}{'Japanese Name':<35}{'Chinese Name':<35}{'Code':<20}{'Decks':<10}{'Qty':<10}")
print("-" * 120)

csv_data = []
csv_data.append(['Rank', 'Japanese Name', 'Chinese Name', 'Card Code', 'Deck Count', 'Total Quantity'])

for rank, (jp_name, code, deck_count, total_qty) in enumerate(unmapped_cards, 1):
    # Try to get Chinese name from common translations
    cn_name = COMMON_TRANSLATIONS.get(jp_name, '')
    
    # If not in common translations, try to find in main database by searching
    if not cn_name and jp_name:
        # Try exact match
        cursor_main.execute("""
            SELECT name FROM cards WHERE name = ? LIMIT 1
        """, (jp_name,))
        result = cursor_main.fetchone()
        if result:
            cn_name = result[0]
    
    # Mark as untranslated if still empty
    if not cn_name:
        cn_name = '(未翻譯)'
    
    code_str = code if code else '(no code)'
    
    print(f"{rank:<6}{jp_name[:34]:<35}{cn_name[:34]:<35}{code_str:<20}{deck_count:<10}{total_qty:<10}")
    csv_data.append([rank, jp_name, cn_name, code_str, deck_count, total_qty])

# Export to CSV
csv_filename = 'unmapped_cards_table.csv'
with open(csv_filename, 'w', encoding='utf-8-sig', newline='') as f:
    writer = csv.writer(f)
    writer.writerows(csv_data)

print("\n" + "=" * 120)
print(f"✅ Exported to: {csv_filename}")
print("=" * 120)

# Summary by category
print("\n" + "=" * 120)
print("SUMMARY BY CATEGORY")
print("=" * 120)

categories = {
    'Basic Energy': [row for row in unmapped_cards if '基本' in row[0] and 'エネルギー' in row[0]],
    'ACE SPEC': [row for row in unmapped_cards if row[1] == 'ACE SPEC'],
    'Promo (SV-P)': [row for row in unmapped_cards if row[1] and 'SV-P' in row[1]],
    'Trainer/Supporter': [row for row in unmapped_cards if row[0] in COMMON_TRANSLATIONS and 'ex' not in row[0]],
    'Pokemon': [row for row in unmapped_cards if 'ex' in row[0] or row[0] in [k for k in COMMON_TRANSLATIONS.keys() if 'ex' in k or k in ['カルボウ', 'ヒトカゲ', 'コダック', 'ゴルダック']]],
}

for category, cards in categories.items():
    if cards:
        total_decks = sum(c[2] for c in cards)
        total_qty = sum(c[3] for c in cards)
        print(f"\n{category}:")
        print(f"  Card Types: {len(cards)}")
        print(f"  Total Deck Usage: {total_decks:,}")
        print(f"  Total Quantity: {total_qty:,}")

conn_event.close()
conn_main.close()

print("\n" + "=" * 120)
print("COMPLETE")
print("=" * 120)
