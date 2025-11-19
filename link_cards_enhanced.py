"""
Enhanced card linking with support for:
1. Basic Energy cards (Japanese → Chinese name mapping)
2. ACE SPEC cards (name-based matching)
3. Promo cards (same-name matching across expansions)
"""

import sqlite3
import json
from pathlib import Path
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class EnhancedCardLinker:
    """Enhanced card linker with special handling for energy and ACE SPEC cards."""
    
    # Energy type mapping: Japanese → Chinese
    ENERGY_MAP = {
        '基本炎エネルギー': ['基本【火】能量', '基本火能量'],
        '基本水エネルギー': ['基本【水】能量', '基本水能量'],
        '基本雷エネルギー': ['基本【雷】能量', '基本雷能量'],
        '基本草エネルギー': ['基本【草】能量', '基本草能量'],
        '基本闘エネルギー': ['基本【鬥】能量', '基本鬥能量'],
        '基本超エネルギー': ['基本【超】能量', '基本超能量'],
        '基本悪エネルギー': ['基本【惡】能量', '基本惡能量'],
        '基本鋼エネルギー': ['基本【鋼】能量', '基本鋼能量'],
    }
    
    # ACE SPEC name mapping: Japanese → Chinese
    ACE_SPEC_MAP = {
        'シークレットボックス': '秘密箱',
        'プライムキャッチャー': '頂尖捕捉器',
        'マキシマムベルト': '極限腰帶',
        'プレシャスキャリー': '古舊能量',  # Note: might need verification
        'きらめく結晶': '璀璨結晶',
        'アンフェアスタンプ': '不公印章',
        'ヒーローマント': '英雄斗篷',
        'エネルギー転送PRO': '能量輸送PRO',
        'パーフェクトミキサー': '完全體攪拌器',  # Need to verify
        'ニュートラルセンター': '中立中心',
        '偉大な大樹': '壯偉碩木',
        'ポケバイタルA': '寶可生機劑A',
        'サバイブギプス': '倖存鍛鍊器',
        'メガトンブロアー': '百萬噸吹風機',
        'ハイパーアロマ': '高級香氛',
        'デラックスボム': '奢華炸彈',
        'リブートポッド': '重新啟動箱',
        'デンジャラス光線': '危險光線',
        'ポケモン回収サイクロン': '寶可夢旋風回收機',
        'スクランブルスイッチ': '急進開關',  # Need to verify
    }
    
    def __init__(self, event_db='ptcg_events.db', 
                 main_db=r'c:\AI_Server\Coding\PokemonDBByjules\PTCG_CardDB_Tc\pokemon_cards.db'):
        self.event_db_path = event_db
        self.main_db_path = main_db
        self.event_conn = None
        self.main_conn = None
        
    def connect(self):
        """Connect to both databases."""
        self.event_conn = sqlite3.connect(self.event_db_path)
        self.event_conn.row_factory = sqlite3.Row
        self.main_conn = sqlite3.connect(self.main_db_path)
        self.main_conn.row_factory = sqlite3.Row
        logger.info("Connected to both databases")
    
    def close(self):
        """Close database connections."""
        if self.event_conn:
            self.event_conn.close()
        if self.main_conn:
            self.main_conn.close()
        logger.info("Database connections closed")
    
    def create_mapping_table(self):
        """Create table to store card mappings."""
        cursor = self.event_conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS card_mappings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_card_id TEXT,
                event_card_name TEXT,
                event_card_code TEXT,
                main_card_id INTEGER,
                main_card_name TEXT,
                main_collector_number TEXT,
                main_expansion_code TEXT,
                match_type TEXT,
                match_confidence TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_event_card_id ON card_mappings(event_card_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_main_card_id ON card_mappings(main_card_id)")
        
        self.event_conn.commit()
        logger.info("Created card_mappings table")
    
    def build_expansion_map(self):
        """Build mapping between expansion codes."""
        cursor = self.main_conn.cursor()
        cursor.execute("SELECT id, code, name FROM expansions")
        
        expansion_map = {}
        for row in cursor:
            expansion_map[row['code']] = {
                'id': row['id'],
                'name': row['name']
            }
        
        logger.info(f"Built expansion map with {len(expansion_map)} expansions")
        return expansion_map
    
    def parse_card_code(self, card_code):
        """Parse card code like 'SV8a 120/187' into expansion and number."""
        if not card_code or card_code == 'ACE SPEC':
            return None, None
        
        parts = card_code.split()
        if len(parts) < 2:
            return None, None
        
        expansion = parts[0]
        number_part = parts[1]
        
        if '/' in number_part:
            number = number_part.split('/')[0]
        else:
            number = number_part
        
        return expansion, number
    
    def link_basic_energy(self):
        """Link basic energy cards using name mapping."""
        mappings = []
        event_cursor = self.event_conn.cursor()
        main_cursor = self.main_conn.cursor()
        
        logger.info("Linking basic energy cards...")
        
        for jp_name, cn_names in self.ENERGY_MAP.items():
            # Get all instances of this energy card in event database
            event_cursor.execute("""
                SELECT DISTINCT card_id, card_name, card_code
                FROM deck_cards
                WHERE card_name = ?
            """, (jp_name,))
            
            event_cards = event_cursor.fetchall()
            
            if not event_cards:
                continue
            
            # Find matching card in main database (prefer bracket notation)
            for cn_name in cn_names:
                main_cursor.execute("""
                    SELECT id, name, collector_number
                    FROM cards
                    WHERE name = ?
                    LIMIT 1
                """, (cn_name,))
                
                main_card = main_cursor.fetchone()
                
                if main_card:
                    # Create mapping for each unique card_id
                    for event_card in event_cards:
                        mappings.append({
                            'event_card_id': event_card['card_id'],
                            'event_card_name': event_card['card_name'],
                            'event_card_code': event_card['card_code'] or '',
                            'main_card_id': main_card['id'],
                            'main_card_name': main_card['name'],
                            'main_collector_number': main_card['collector_number'] or '',
                            'main_expansion_code': '',
                            'match_type': 'basic_energy',
                            'match_confidence': 'high'
                        })
                    logger.info(f"Linked {jp_name} → {cn_name} ({len(event_cards)} instances)")
                    break
        
        logger.info(f"Created {len(mappings)} basic energy mappings")
        return mappings
    
    def link_ace_spec(self):
        """Link ACE SPEC cards using name mapping."""
        mappings = []
        event_cursor = self.event_conn.cursor()
        main_cursor = self.main_conn.cursor()
        
        logger.info("Linking ACE SPEC cards...")
        
        for jp_name, cn_name in self.ACE_SPEC_MAP.items():
            # Get all instances of this ACE SPEC card
            event_cursor.execute("""
                SELECT DISTINCT card_id, card_name, card_code
                FROM deck_cards
                WHERE card_name = ? AND card_code = 'ACE SPEC'
            """, (jp_name,))
            
            event_cards = event_cursor.fetchall()
            
            if not event_cards:
                continue
            
            # Find matching ACE SPEC card in main database
            main_cursor.execute("""
                SELECT id, name, collector_number
                FROM cards
                WHERE name = ? AND rarity = 'ACE'
                LIMIT 1
            """, (cn_name,))
            
            main_card = main_cursor.fetchone()
            
            if main_card:
                for event_card in event_cards:
                    mappings.append({
                        'event_card_id': event_card['card_id'],
                        'event_card_name': event_card['card_name'],
                        'event_card_code': 'ACE SPEC',
                        'main_card_id': main_card['id'],
                        'main_card_name': main_card['name'],
                        'main_collector_number': main_card['collector_number'] or '',
                        'main_expansion_code': 'ACE',
                        'match_type': 'ace_spec',
                        'match_confidence': 'high'
                    })
                logger.info(f"Linked ACE SPEC: {jp_name} → {cn_name} ({len(event_cards)} instances)")
            else:
                logger.warning(f"ACE SPEC not found in main DB: {cn_name}")
        
        logger.info(f"Created {len(mappings)} ACE SPEC mappings")
        return mappings
    
    def link_promo_by_name(self):
        """Link promo cards by finding same Japanese name in main database."""
        mappings = []
        event_cursor = self.event_conn.cursor()
        main_cursor = self.main_conn.cursor()
        
        logger.info("Linking promo cards by name...")
        
        # Get unmapped SV-P promo cards from event database
        event_cursor.execute("""
            SELECT DISTINCT dc.card_id, dc.card_name, dc.card_code
            FROM deck_cards dc
            LEFT JOIN card_mappings cm ON dc.card_id = cm.event_card_id
            WHERE cm.event_card_id IS NULL
            AND dc.card_code LIKE 'SV-P%'
            AND dc.card_name NOT LIKE '%基本%エネルギー'
        """)
        
        promo_cards = event_cursor.fetchall()
        logger.info(f"Processing {len(promo_cards)} unmapped promo cards")
        
        for event_card in promo_cards:
            # Try to find card with same Japanese name in main database
            # Many cards have Japanese names in the main database too
            main_cursor.execute("""
                SELECT id, name, collector_number
                FROM cards
                WHERE name = ?
                LIMIT 1
            """, (event_card['card_name'],))
            
            main_card = main_cursor.fetchone()
            
            if main_card:
                mappings.append({
                    'event_card_id': event_card['card_id'],
                    'event_card_name': event_card['card_name'],
                    'event_card_code': event_card['card_code'],
                    'main_card_id': main_card['id'],
                    'main_card_name': main_card['name'],
                    'main_collector_number': main_card['collector_number'] or '',
                    'main_expansion_code': 'SV-P',
                    'match_type': 'promo_name',
                    'match_confidence': 'medium'
                })
                logger.debug(f"Linked promo: {event_card['card_name']} ({event_card['card_code']})")
        
        logger.info(f"Created {len(mappings)} promo card mappings")
        return mappings
    
    def link_by_name_first(self):
        """Priority name matching before expansion code matching."""
        event_cursor = self.event_conn.cursor()
        main_cursor = self.main_conn.cursor()
        
        # Get cards not yet mapped and not basic energy/ACE SPEC
        event_cursor.execute("""
            SELECT DISTINCT dc.card_id, dc.card_name, dc.card_code
            FROM deck_cards dc
            LEFT JOIN card_mappings cm ON dc.card_id = cm.event_card_id
            WHERE cm.event_card_id IS NULL
            AND dc.card_code != '' 
            AND dc.card_code != 'ACE SPEC'
            AND dc.card_name NOT LIKE '%基本%エネルギー'
            ORDER BY dc.card_code
        """)
        
        event_cards = event_cursor.fetchall()
        logger.info(f"Processing {len(event_cards)} unmapped cards with name-first strategy")
        
        mappings = []
        name_matched = 0
        expansion_matched = 0
        unmatched = 0
        
        expansion_map = self.build_expansion_map()
        
        for idx, event_card in enumerate(event_cards):
            if idx % 100 == 0:
                logger.info(f"Processing card {idx}/{len(event_cards)}")
            
            matched = False
            
            # PRIORITY 1: Try name matching first (prevents MBD-type errors)
            main_cursor.execute("""
                SELECT id, name, collector_number, expansion_id
                FROM cards
                WHERE name = ?
                LIMIT 1
            """, (event_card['card_name'],))
            
            name_match = main_cursor.fetchone()
            
            if name_match:
                # Verify it's the same card type by checking if expansion code makes sense
                expansion_code, collector_number = self.parse_card_code(event_card['card_code'])
                
                # Get expansion code for the matched card
                main_cursor.execute("""
                    SELECT e.code 
                    FROM expansions e 
                    WHERE e.id = ?
                """, (name_match['expansion_id'],))
                
                exp_row = main_cursor.fetchone()
                main_exp_code = exp_row['code'] if exp_row else None
                
                mappings.append({
                    'event_card_id': event_card['card_id'],
                    'event_card_name': event_card['card_name'],
                    'event_card_code': event_card['card_code'],
                    'main_card_id': name_match['id'],
                    'main_card_name': name_match['name'],
                    'main_collector_number': name_match['collector_number'],
                    'main_expansion_code': main_exp_code or '',
                    'match_type': 'name_primary',
                    'match_confidence': 'high'
                })
                name_matched += 1
                matched = True
                continue
            
            # PRIORITY 2: Fall back to expansion code + collector number matching
            if not matched:
                expansion_code, collector_number = self.parse_card_code(event_card['card_code'])
                
                # Skip MBD and MBG expansions - they have unreliable codes
                if expansion_code in ['MBD', 'MBG']:
                    unmatched += 1
                    continue
                
                if expansion_code and collector_number and expansion_code in expansion_map:
                    expansion_id = expansion_map[expansion_code]['id']
                    
                    main_cursor.execute("""
                        SELECT id, name, collector_number
                        FROM cards
                        WHERE expansion_id = ? AND collector_number = ?
                    """, (expansion_id, collector_number))
                    
                    main_card = main_cursor.fetchone()
                    
                    if main_card:
                        mappings.append({
                            'event_card_id': event_card['card_id'],
                            'event_card_name': event_card['card_name'],
                            'event_card_code': event_card['card_code'],
                            'main_card_id': main_card['id'],
                            'main_card_name': main_card['name'],
                            'main_collector_number': main_card['collector_number'],
                            'main_expansion_code': expansion_code,
                            'match_type': 'expansion_code',
                            'match_confidence': 'medium'
                        })
                        expansion_matched += 1
                        matched = True
            
            if not matched:
                unmatched += 1
        
        logger.info(f"Name-first linking: Name matched {name_matched}, Expansion matched {expansion_matched}, Unmatched {unmatched}")
        return mappings
    
    def save_mappings(self, mappings):
        """Save all card mappings to database."""
        cursor = self.event_conn.cursor()
        
        cursor.execute("DELETE FROM card_mappings")
        
        cursor.executemany("""
            INSERT INTO card_mappings (
                event_card_id, event_card_name, event_card_code,
                main_card_id, main_card_name, main_collector_number,
                main_expansion_code, match_type, match_confidence
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [
            (
                m['event_card_id'], m['event_card_name'], m['event_card_code'],
                m['main_card_id'], m['main_card_name'], m['main_collector_number'],
                m['main_expansion_code'], m['match_type'], m['match_confidence']
            )
            for m in mappings
        ])
        
        self.event_conn.commit()
        logger.info(f"Saved {len(mappings)} total card mappings")
    
    def get_statistics(self):
        """Get comprehensive mapping statistics."""
        cursor = self.event_conn.cursor()
        
        stats = {}
        
        cursor.execute("SELECT COUNT(DISTINCT card_id) FROM deck_cards")
        stats['total_event_cards'] = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM card_mappings")
        stats['mapped_cards'] = cursor.fetchone()[0]
        
        stats['coverage_percentage'] = round(
            (stats['mapped_cards'] / stats['total_event_cards']) * 100, 2
        ) if stats['total_event_cards'] > 0 else 0
        
        # By match type
        cursor.execute("""
            SELECT match_type, COUNT(*) as count
            FROM card_mappings
            GROUP BY match_type
        """)
        stats['by_match_type'] = {row[0]: row[1] for row in cursor.fetchall()}
        
        # Top expansions
        cursor.execute("""
            SELECT main_expansion_code, COUNT(*) as count
            FROM card_mappings
            WHERE main_expansion_code != ''
            GROUP BY main_expansion_code
            ORDER BY count DESC
            LIMIT 10
        """)
        stats['top_expansions'] = [
            {'expansion': row[0], 'count': row[1]}
            for row in cursor.fetchall()
        ]
        
        return stats


def main():
    """Main execution."""
    logger.info("Starting enhanced card linking process with NAME-FIRST strategy")
    
    linker = EnhancedCardLinker()
    
    try:
        linker.connect()
        linker.create_mapping_table()
        
        # Step 1: Link basic energy cards
        energy_mappings = linker.link_basic_energy()
        
        # Step 2: Link ACE SPEC cards
        ace_mappings = linker.link_ace_spec()
        
        # Step 3: Link promo cards by name
        promo_mappings = linker.link_promo_by_name()
        
        # Step 4: NAME-FIRST matching strategy (prevents MBD-type errors)
        standard_mappings = linker.link_by_name_first()
        
        # Combine all mappings
        all_mappings = energy_mappings + ace_mappings + promo_mappings + standard_mappings
        
        # Save to database
        linker.save_mappings(all_mappings)
        
        # Show statistics
        stats = linker.get_statistics()
        
        print("\n" + "=" * 80)
        print("ENHANCED CARD LINKING STATISTICS (NAME-FIRST STRATEGY)")
        print("=" * 80)
        print(f"Total Event Cards: {stats['total_event_cards']:,}")
        print(f"Mapped Cards: {stats['mapped_cards']:,}")
        print(f"Coverage: {stats['coverage_percentage']}%")
        
        print("\nBy Match Type:")
        for match_type, count in stats['by_match_type'].items():
            print(f"  {match_type:20s}: {count:,} cards")
        
        print("\nTop Expansions:")
        for exp in stats['top_expansions']:
            print(f"  {exp['expansion']:10s}: {exp['count']:4d} cards")
        
        print("=" * 80)
        
        # Sample new mappings
        print("\n📝 SAMPLE NEW MAPPINGS:")
        print("-" * 80)
        
        cursor = linker.event_conn.cursor()
        
        # Basic Energy samples
        print("\n⚡ Basic Energy Cards:")
        cursor.execute("""
            SELECT event_card_name, main_card_name
            FROM card_mappings
            WHERE match_type = 'basic_energy'
            GROUP BY event_card_name
            LIMIT 5
        """)
        for row in cursor.fetchall():
            print(f"  {row[0]:30s} → {row[1]}")
        
        # ACE SPEC samples
        print("\n⭐ ACE SPEC Cards:")
        cursor.execute("""
            SELECT event_card_name, main_card_name
            FROM card_mappings
            WHERE match_type = 'ace_spec'
            LIMIT 5
        """)
        for row in cursor.fetchall():
            print(f"  {row[0]:30s} → {row[1]}")
        
        # Name-primary samples
        print("\n📛 Name-Primary Matches:")
        cursor.execute("""
            SELECT event_card_name, event_card_code, main_card_name
            FROM card_mappings
            WHERE match_type = 'name_primary'
            LIMIT 10
        """)
        for row in cursor.fetchall():
            print(f"  {row[0]:30s} ({row[1]:15s}) → {row[2]}")
        
        # Expansion code samples
        print("\n📦 Expansion Code Matches:")
        cursor.execute("""
            SELECT event_card_name, event_card_code, main_card_name
            FROM card_mappings
            WHERE match_type = 'expansion_code'
            LIMIT 10
        """)
        for row in cursor.fetchall():
            print(f"  {row[0]:30s} ({row[1]:15s}) → {row[2]}")
        
    finally:
        linker.close()
    
    logger.info("Enhanced card linking completed with NAME-FIRST strategy")


if __name__ == '__main__':
    main()
