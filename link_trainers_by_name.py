import sqlite3
import shutil
from datetime import datetime

# 日文→中文訓練家卡翻譯對照表（擴充版）
TRAINER_TRANSLATIONS = {
    # 支援者卡
    'ナンジャモ': '奇樹',
    'ボスの指令': '老大的指令',
    'ペパー': '派帕',
    '博士の研究': '博士的研究',
    'シマボシ': '璀璨',
    'クラベル': '克拉韋爾',
    'サカキのカリスマ': '坂木的魅力',
    'キバナ': '奇巴納',
    'ジャッジマン': '裁判員',
    'アクロマの実験': '阿克羅瑪的實驗',
    'リーリエの決心': '莉莉艾的決心',
    'スグリ': '斯古利',
    'ともだちてちょう': '好朋友手冊',
    'フトゥー博士のシナリオ': '芙図博士的劇本',
    'ミツルの思いやり': '米茲露的體貼',
    'ゼイユ': '澤宇',
    
    # 物品卡
    'ネストボール': '巢穴球',
    'ハイパーボール': '高級球',
    'ポケモンいれかえ': '寶可夢替換',
    'バトルVIPパス': '對戰VIP通行證',
    'ヒーローマント': '英雄披風',
    'カウンターキャッチャー': '反擊捕獲器',
    'ふしぎなアメ': '神奇糖果',
    'すごいつりざお': '厲害的釣竿',
    'しんかのおこう': '進化的薰香',
    'エネルギーつけかえ': '能量轉移',
    'エネルギーリサイクル': '能量回收',
    'ポケモンリバース': '寶可夢逆轉',
    'キャンセルコロン': '取消香水',
    'ポケギア3.0': '寶可夢裝置3.0',
    'トレッキングシューズ': '登山鞋',
    '勇気のおまもり': '勇氣守護',
    'なかよしポフィン': '友好泡芙',
    'ふうせん': '氣球',
    'ツールスクラッパー': '道具刮刀',
    'むしとりセット': '捕蟲組',
    'カウンターゲイン': '反擊增益',
    'ワザマシン エヴォリューション': '招式機器 進化',
    'ワザマシン デヴォリューション': '招式機器 退化',
    '夜のタンカ': '夜之擔架',
    '大地の器': '大地的容器',
    'ロトりぼう': '洛托姆手機',
    'ガチガチバンド': '堅固腰帶',
    'ジャミングタワー': '干擾塔',
    'スーパーエネルギー回収': '超級能量回收',
    'テラスタルオーブ': '太晶珠',
    '緊急ボード': '緊急滑板',
    '改造ハンマー': '改造槌',
    'エレキジェネレーター': '電力產生器',
    'エネルギー転送': '能量轉移',
    'エネルギー転送PRO': '能量轉送PRO',
    
    # 競技場卡
    'タウンデパート': '城鎮百貨公司',
    'ポケモンリーグ本部': '寶可夢聯盟總部',
    'エイチ湖': 'H湖',
    'ボウルタウン': '深缽鎮',
    
    # ACE SPEC 卡
    'プライムキャッチャー': '頂尖捕捉器',
    'マスターボール': '大師球',
    'シークレットボックス': '秘密箱',
    'ネオアッパーエネルギー': '新衝天能量',
    'ポケストップ': '寶可夢補給站',
    'マキシマムベルト': '極限腰帶',
    'プレシャスキャリー': '貴重手推車',
    'アンフェアスタンプ': '不公印章',
    'きらめく結晶': '璀璨結晶',
    
    # 特殊能量
    'ダブルターボエネルギー': '雙倍Turbo能量',
    'ジェットエネルギー': 'Jet能量',
    'リバーサルエネルギー': '逆轉能量',
    'ギフトエネルギー': '禮物能量',
    'レガシーエネルギー': '傳承能量',
    'ルミナスエネルギー': '光輝能量',
    'セラピーエネルギー': '治療能量',
    'ブーストエナジー古代': 'Boost能量【古代】',
    'ブーストエナジー未来': 'Boost能量【未來】',
    'イグニッションエネルギー': '點火能量',
    'プリズムエネルギー': '棱鏡能量',
    'ミストエネルギー': '薄霧能量',
}

# 連接資料庫
event_db_path = r"c:\AI_Server\Coding\ptcg-product-info\ptcg_events.db"
chinese_db_path = r"c:\AI_Server\Coding\PokemonDBByjules\PTCG_CardDB_Tc\pokemon_cards.db"

# 備份資料庫
backup_path = event_db_path.replace('.db', f'_backup_before_trainer_link_{datetime.now().strftime("%Y%m%d_%H%M%S")}.db')
shutil.copy2(event_db_path, backup_path)
print(f"✅ 資料庫已備份: {backup_path}\n")

event_conn = sqlite3.connect(event_db_path)
event_cursor = event_conn.cursor()

chinese_conn = sqlite3.connect(chinese_db_path)
chinese_cursor = chinese_conn.cursor()

print("=== 自動對應訓練家卡（按名稱） ===\n")

linked_count = 0
skipped_count = 0
not_found_count = 0

for japanese_name, chinese_name in TRAINER_TRANSLATIONS.items():
    print(f"\n處理: {japanese_name} → {chinese_name}")
    
    # 1. 在賽事資料庫中查找所有使用此日文名稱的卡片ID
    event_cursor.execute("""
        SELECT DISTINCT card_id, card_name
        FROM deck_cards
        WHERE card_name = ?
    """, (japanese_name,))
    
    event_cards = event_cursor.fetchall()
    
    if not event_cards:
        print(f"  ⚠️  未找到日文卡片: {japanese_name}")
        continue
    
    print(f"  找到 {len(event_cards)} 個日文卡片ID")
    
    # 2. 在中文資料庫中查找對應的中文卡片
    chinese_cursor.execute("""
        SELECT id, name, card_type
        FROM cards
        WHERE name = ?
        LIMIT 1
    """, (chinese_name,))
    
    chinese_card = chinese_cursor.fetchone()
    
    if not chinese_card:
        print(f"  ❌ 中文資料庫中未找到: {chinese_name}")
        not_found_count += 1
        continue
    
    chinese_id, chinese_card_name, card_type = chinese_card
    print(f"  ✅ 找到中文卡片: ID {chinese_id}, {chinese_card_name} ({card_type})")
    
    # 3. 為每個日文卡片ID建立對應
    for event_card_id, event_card_name in event_cards:
        # 檢查是否已經對應
        event_cursor.execute("""
            SELECT event_card_id FROM card_mappings
            WHERE event_card_id = ?
        """, (event_card_id,))
        
        if event_cursor.fetchone():
            print(f"     跳過 ID {event_card_id} (已對應)")
            skipped_count += 1
            continue
        
        # 插入新對應
        event_cursor.execute("""
            INSERT INTO card_mappings (
                event_card_id,
                event_card_name,
                main_card_id,
                main_card_name,
                match_type
            ) VALUES (?, ?, ?, ?, ?)
        """, (event_card_id, japanese_name, chinese_id, chinese_card_name, 'name_trainer_match'))
        
        linked_count += 1
        print(f"     ✅ 對應 ID {event_card_id}")

# 提交更改
event_conn.commit()

print(f"\n{'='*60}")
print(f"對應完成統計:")
print(f"  ✅ 新增對應: {linked_count} 個")
print(f"  ⏭️  已存在跳過: {skipped_count} 個")
print(f"  ❌ 中文未找到: {not_found_count} 個")
print(f"{'='*60}")

# 驗證結果
event_cursor.execute("""
    SELECT COUNT(*) 
    FROM card_mappings 
    WHERE match_type = 'name_trainer_match'
""")
total_trainer_mappings = event_cursor.fetchone()[0]
print(f"\n總訓練家卡對應數: {total_trainer_mappings}")

# 檢查整體對應率
event_cursor.execute("""
    SELECT 
        COUNT(DISTINCT dc.card_id) as total,
        COUNT(DISTINCT CASE WHEN cm.main_card_id IS NOT NULL THEN dc.card_id END) as mapped
    FROM deck_cards dc
    LEFT JOIN card_mappings cm ON dc.card_id = cm.event_card_id
""")

total, mapped = event_cursor.fetchone()
coverage = mapped * 100 / total if total > 0 else 0
print(f"\n整體對應率: {mapped}/{total} ({coverage:.2f}%)")

event_conn.close()
chinese_conn.close()

print(f"\n✅ 所有訓練家卡已自動對應完成！")
print(f"📊 備份檔案: {backup_path}")
