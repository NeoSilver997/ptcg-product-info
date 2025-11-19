"""
Two-Method Card Mapping System
================================
Method 1: Map by NAME (basic energy, ACE SPEC, exact name matching)
Method 2: Map by CODE using cache.json (expansion code + collector number, excluding MBD/MBG)

Stores results in card_mappings table with clear match_type distinction
"""

import sqlite3
import json
import re
from datetime import datetime

EVENT_DB = "ptcg_events.db"
MAIN_DB = r"c:\AI_Server\Coding\PokemonDBByjules\PTCG_CardDB_Tc\pokemon_cards.db"
CACHE_FILE = "card_code_cache.json"

# Translation dictionaries
ENERGY_MAP = {
    '基本炎エネルギー': '基本【火】能量',
    '基本水エネルギー': '基本【水】能量',
    '基本雷エネルギー': '基本【雷】能量',
    '基本超エネルギー': '基本【超】能量',
    '基本闘エネルギー': '基本【鬥】能量',
    '基本悪エネルギー': '基本【惡】能量',
    '基本鋼エネルギー': '基本【鋼】能量',
    '基本草エネルギー': '基本【草】能量',
}

ACE_SPEC_MAP = {
    'シークレットボックス': '秘密箱',
    'プライムキャッチャー': '究極捕獲器',
    'マスターボール': '大師球',
    'ヒーローマント': '英雄披風',
    'ネオアッパーエネルギー': 'Neo 上層能量',
    'レガシーエネルギー': '傳承能量',
    '勇気のおまもり': '勇氣守護',
    'ポケストップ': '寶可夢補給站',
    'あわせもの': '湊合',
    'きずなのいし': '牽絆之石',
    'きままなしっぽ': '隨心所欲之尾',
    'ゼイユの選択': '在競賽中選擇',
    'アンフェアスタンプ': '不公平郵票',
    'ポケモンリバース': '寶可夢逆轉',
    '基本悪エネルギー': '基本【惡】能量',
    'エレキジェネレーター': '電力產生器',
    'ガッツのつるはし': '勇氣之鶴嘴鋤',
    'リブートポッド': '重新啟動艙',
}

def load_cache():
    """Load card code cache"""
    try:
        with open(CACHE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"⚠️  Cache file not found: {CACHE_FILE}")
        return {}

def parse_card_code(card_code):
    """Parse card code into expansion and collector number"""
    if not card_code or card_code.strip() == '':
        return None, None
    
    # Pattern: "SV8a 120/187" or "SV8a 120"
    match = re.search(r'^([A-Za-z0-9]+(?:-[A-Za-z0-9]+)?)\s+(\d+)', card_code)
    if match:
        expansion_code = match.group(1)
        collector_number = match.group(2)
        return expansion_code, collector_number
    
    return None, None

def map_by_name(conn_event, conn_main):
    """Method 1: Map cards by NAME matching"""
    print("\n" + "="*70)
    print("METHOD 1: 名稱匹配 (Name Matching)")
    print("="*70)
    
    cursor_event = conn_event.cursor()
    cursor_main = conn_main.cursor()
    
    total_mapped = 0
    
    # 1. Map Basic Energy
    print("\n🔋 步驟 1: 對應基本能量卡...")
    energy_mapped = 0
    
    for jp_energy, cn_energy in ENERGY_MAP.items():
        # Get event cards with this Japanese energy name
        cursor_event.execute("""
            SELECT card_id, card_name FROM deck_cards 
            WHERE card_name = ?
            GROUP BY card_id
        """, (jp_energy,))
        event_cards = cursor_event.fetchall()
        
        if event_cards:
            # Get Chinese card ID
            cursor_main.execute("""
                SELECT id FROM cards WHERE name = ?
            """, (cn_energy,))
            main_card = cursor_main.fetchone()
            
            if main_card:
                main_card_id = main_card[0]
                
                for event_card_id, event_card_name in event_cards:
                    cursor_event.execute("""
                        INSERT OR REPLACE INTO card_mappings 
                        (event_card_id, event_card_name, event_card_code, 
                         main_card_id, main_card_name, match_type, match_confidence)
                        VALUES (?, ?, '', ?, ?, 'name_basic_energy', 1.0)
                    """, (event_card_id, event_card_name, main_card_id, cn_energy))
                    energy_mapped += 1
    
    conn_event.commit()
    print(f"   ✅ 基本能量卡對應: {energy_mapped} 張")
    total_mapped += energy_mapped
    
    # 2. Map ACE SPEC
    print("\n⭐ 步驟 2: 對應 ACE SPEC 卡...")
    ace_mapped = 0
    
    for jp_ace, cn_ace in ACE_SPEC_MAP.items():
        cursor_event.execute("""
            SELECT card_id, card_name FROM deck_cards 
            WHERE card_name = ?
            GROUP BY card_id
        """, (jp_ace,))
        event_cards = cursor_event.fetchall()
        
        if event_cards:
            cursor_main.execute("""
                SELECT id FROM cards WHERE name = ?
            """, (cn_ace,))
            main_card = cursor_main.fetchone()
            
            if main_card:
                main_card_id = main_card[0]
                
                for event_card_id, event_card_name in event_cards:
                    cursor_event.execute("""
                        INSERT OR REPLACE INTO card_mappings 
                        (event_card_id, event_card_name, event_card_code, 
                         main_card_id, main_card_name, match_type, match_confidence)
                        VALUES (?, ?, '', ?, ?, 'name_ace_spec', 1.0)
                    """, (event_card_id, event_card_name, main_card_id, cn_ace))
                    ace_mapped += 1
    
    conn_event.commit()
    print(f"   ✅ ACE SPEC 卡對應: {ace_mapped} 張")
    total_mapped += ace_mapped
    
    # 3. Map by exact name matching (for cards with same name in both databases)
    print("\n📛 步驟 3: 對應同名卡片...")
    name_mapped = 0
    
    cursor_event.execute("""
        SELECT DISTINCT dc.card_id, dc.card_name
        FROM deck_cards dc
        LEFT JOIN card_mappings cm ON dc.card_id = cm.event_card_id
        WHERE cm.event_card_id IS NULL
    """)
    unmapped_cards = cursor_event.fetchall()
    
    for event_card_id, event_card_name in unmapped_cards:
        cursor_main.execute("""
            SELECT id FROM cards WHERE name = ?
        """, (event_card_name,))
        main_card = cursor_main.fetchone()
        
        if main_card:
            main_card_id = main_card[0]
            cursor_event.execute("""
                INSERT OR REPLACE INTO card_mappings 
                (event_card_id, event_card_name, event_card_code, 
                 main_card_id, main_card_name, match_type, match_confidence)
                VALUES (?, ?, '', ?, ?, 'name_exact_match', 0.95)
            """, (event_card_id, event_card_name, main_card_id, event_card_name))
            name_mapped += 1
    
    conn_event.commit()
    print(f"   ✅ 同名卡片對應: {name_mapped} 張")
    total_mapped += name_mapped
    
    print(f"\n📊 METHOD 1 總計: {total_mapped} 張卡片已對應")
    return total_mapped

def map_by_code_with_cache(conn_event, conn_main, cache):
    """Method 2: Map cards by CODE using cache.json (excluding MBD/MBG)"""
    print("\n" + "="*70)
    print("METHOD 2: 代碼匹配 (Code Matching with Cache)")
    print("="*70)
    
    cursor_event = conn_event.cursor()
    cursor_main = conn_main.cursor()
    
    # Build expansion code map
    cursor_main.execute("SELECT id, code FROM expansions")
    expansion_map = {code: exp_id for exp_id, code in cursor_main.fetchall()}
    
    print(f"\n📦 載入擴充包對照表: {len(expansion_map)} 個擴充包")
    print(f"💾 載入快取資料: {len(cache)} 筆記錄")
    
    # Get unmapped cards with codes
    cursor_event.execute("""
        SELECT DISTINCT dc.card_id, dc.card_name, dc.card_code
        FROM deck_cards dc
        LEFT JOIN card_mappings cm ON dc.card_id = cm.event_card_id
        WHERE cm.event_card_id IS NULL 
            AND dc.card_code IS NOT NULL 
            AND dc.card_code != ''
    """)
    unmapped_cards = cursor_event.fetchall()
    
    print(f"\n🔍 處理 {len(unmapped_cards)} 張未對應卡片...")
    
    code_mapped = 0
    cache_used = 0
    direct_match = 0
    excluded_mbd_mbg = 0
    no_match = 0
    
    for event_card_id, event_card_name, event_card_code in unmapped_cards:
        # Parse expansion code and collector number
        expansion_code, collector_number = parse_card_code(event_card_code)
        
        if not expansion_code or not collector_number:
            no_match += 1
            continue
        
        # EXCLUDE MBD and MBG expansions
        if expansion_code in ['MBD', 'MBG']:
            excluded_mbd_mbg += 1
            continue
        
        # Try direct match first
        expansion_id = expansion_map.get(expansion_code)
        if expansion_id:
            cursor_main.execute("""
                SELECT id, name FROM cards 
                WHERE expansion_id = ? AND collector_number = ?
            """, (expansion_id, collector_number))
            main_card = cursor_main.fetchone()
            
            if main_card:
                main_card_id, main_card_name = main_card
                cursor_event.execute("""
                    INSERT OR REPLACE INTO card_mappings 
                    (event_card_id, event_card_name, event_card_code, 
                     main_card_id, main_card_name, main_collector_number, 
                     main_expansion_code, match_type, match_confidence)
                    VALUES (?, ?, ?, ?, ?, ?, ?, 'code_direct_match', 0.90)
                """, (event_card_id, event_card_name, event_card_code, 
                      main_card_id, main_card_name, collector_number, expansion_code))
                code_mapped += 1
                direct_match += 1
                continue
        
        # Try cache match
        cache_code = cache.get(str(event_card_id))
        if cache_code:
            cache_expansion, cache_number = parse_card_code(cache_code)
            
            if cache_expansion and cache_number:
                # Skip MBD/MBG even from cache
                if cache_expansion in ['MBD', 'MBG']:
                    excluded_mbd_mbg += 1
                    continue
                
                cache_expansion_id = expansion_map.get(cache_expansion)
                if cache_expansion_id:
                    cursor_main.execute("""
                        SELECT id, name FROM cards 
                        WHERE expansion_id = ? AND collector_number = ?
                    """, (cache_expansion_id, cache_number))
                    main_card = cursor_main.fetchone()
                    
                    if main_card:
                        main_card_id, main_card_name = main_card
                        cursor_event.execute("""
                            INSERT OR REPLACE INTO card_mappings 
                            (event_card_id, event_card_name, event_card_code, 
                             main_card_id, main_card_name, main_collector_number, 
                             main_expansion_code, match_type, match_confidence)
                            VALUES (?, ?, ?, ?, ?, ?, ?, 'code_cache_match', 0.85)
                        """, (event_card_id, event_card_name, event_card_code, 
                              main_card_id, main_card_name, cache_number, cache_expansion))
                        code_mapped += 1
                        cache_used += 1
                        continue
        
        no_match += 1
    
    conn_event.commit()
    
    print(f"\n📊 METHOD 2 結果:")
    print(f"   ✅ 直接代碼匹配: {direct_match} 張")
    print(f"   ✅ 快取代碼匹配: {cache_used} 張")
    print(f"   🚫 排除 MBD/MBG: {excluded_mbd_mbg} 張")
    print(f"   ❌ 無法匹配: {no_match} 張")
    print(f"   📊 METHOD 2 總計: {code_mapped} 張卡片已對應")
    
    return code_mapped

def generate_summary(conn_event):
    """Generate mapping summary"""
    cursor = conn_event.cursor()
    
    print("\n" + "="*70)
    print("最終統計摘要")
    print("="*70)
    
    # Total cards
    cursor.execute("SELECT COUNT(DISTINCT card_id) FROM deck_cards")
    total_cards = cursor.fetchone()[0]
    
    # Total mapped
    cursor.execute("SELECT COUNT(DISTINCT event_card_id) FROM card_mappings")
    total_mapped = cursor.fetchone()[0]
    
    # By method
    cursor.execute("""
        SELECT match_type, COUNT(*) 
        FROM card_mappings 
        GROUP BY match_type 
        ORDER BY COUNT(*) DESC
    """)
    methods = cursor.fetchall()
    
    coverage = (total_mapped / total_cards * 100) if total_cards > 0 else 0
    
    print(f"\n📊 整體統計:")
    print(f"   總卡片種類: {total_cards:,}")
    print(f"   已對應卡片: {total_mapped:,}")
    print(f"   覆蓋率: {coverage:.1f}%")
    
    print(f"\n📋 對應方法分佈:")
    method_names = {
        'name_basic_energy': '名稱匹配 - 基本能量',
        'name_ace_spec': '名稱匹配 - ACE SPEC',
        'name_exact_match': '名稱匹配 - 同名卡片',
        'code_direct_match': '代碼匹配 - 直接匹配',
        'code_cache_match': '代碼匹配 - 快取匹配',
    }
    
    for match_type, count in methods:
        method_label = method_names.get(match_type, match_type)
        print(f"   {method_label}: {count:,} 張")
    
    # Usage coverage
    cursor.execute("""
        SELECT SUM(dc.quantity) 
        FROM deck_cards dc
        JOIN card_mappings cm ON dc.card_id = cm.event_card_id
    """)
    mapped_usage = cursor.fetchone()[0] or 0
    
    cursor.execute("SELECT SUM(quantity) FROM deck_cards")
    total_usage = cursor.fetchone()[0]
    
    usage_coverage = (mapped_usage / total_usage * 100) if total_usage > 0 else 0
    
    print(f"\n💡 使用率統計:")
    print(f"   總使用次數: {total_usage:,}")
    print(f"   已對應使用: {mapped_usage:,}")
    print(f"   使用率覆蓋: {usage_coverage:.1f}%")

def main():
    print("="*70)
    print("🎴 Pokemon TCG 雙方法卡片對應系統")
    print("="*70)
    print(f"開始時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Load cache
    cache = load_cache()
    
    # Connect to databases
    conn_event = sqlite3.connect(EVENT_DB)
    conn_main = sqlite3.connect(MAIN_DB)
    
    # Clear existing mappings
    print("\n🗑️  清除舊的對應資料...")
    cursor_event = conn_event.cursor()
    cursor_event.execute("DELETE FROM card_mappings")
    conn_event.commit()
    print("   ✅ 已清除")
    
    # Method 1: Map by name
    name_count = map_by_name(conn_event, conn_main)
    
    # Method 2: Map by code with cache
    code_count = map_by_code_with_cache(conn_event, conn_main, cache)
    
    # Generate summary
    generate_summary(conn_event)
    
    # Close connections
    conn_event.close()
    conn_main.close()
    
    print("\n" + "="*70)
    print(f"✅ 對應完成!")
    print(f"完成時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*70)

if __name__ == "__main__":
    main()
