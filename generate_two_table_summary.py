"""
Generate HTML Summary with Two Mapping Tables
==============================================
Creates separate tables for:
1. Cards mapped by NAME matching
2. Cards mapped by EXPANSION CODE matching (using cache)
"""

import sqlite3
import json
from datetime import datetime

EVENT_DB = "ptcg_events.db"
MAIN_DB = r"c:\AI_Server\Coding\PokemonDBByjules\PTCG_CardDB_Tc\pokemon_cards.db"
CACHE_FILE = "card_code_cache.json"

def load_cache():
    """Load card code cache"""
    try:
        with open(CACHE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def generate_two_table_html():
    conn_event = sqlite3.connect(EVENT_DB)
    conn_main = sqlite3.connect(MAIN_DB)
    
    cursor_event = conn_event.cursor()
    cursor_main = conn_main.cursor()
    
    # Load cache
    cache = load_cache()
    
    # Get overall statistics
    cursor_event.execute("SELECT COUNT(DISTINCT event_card_id) FROM card_mappings")
    total_mapped = cursor_event.fetchone()[0]
    
    cursor_event.execute("SELECT COUNT(DISTINCT card_id) FROM deck_cards")
    total_cards = cursor_event.fetchone()[0]
    
    # Get NAME-matched cards
    cursor_event.execute("""
        SELECT 
            cm.event_card_name as japanese,
            cm.main_card_name as chinese,
            cm.event_card_code,
            cm.main_expansion_code,
            COUNT(DISTINCT dc.deck_id) as deck_count,
            SUM(dc.quantity) as total_quantity
        FROM card_mappings cm
        JOIN deck_cards dc ON cm.event_card_id = dc.card_id
        WHERE cm.match_type IN ('name_basic_energy', 'name_ace_spec', 'name_exact_match')
        GROUP BY cm.event_card_id
        ORDER BY deck_count DESC
    """)
    name_matched = cursor_event.fetchall()
    
    # Get CODE-matched cards with cache info
    cursor_event.execute("""
        SELECT 
            cm.event_card_name as japanese,
            cm.main_card_name as chinese,
            cm.event_card_code,
            cm.main_expansion_code,
            cm.main_card_id,
            COUNT(DISTINCT dc.deck_id) as deck_count,
            SUM(dc.quantity) as total_quantity
        FROM card_mappings cm
        JOIN deck_cards dc ON cm.event_card_id = dc.card_id
        WHERE cm.match_type IN ('code_direct_match', 'code_cache_match')
        GROUP BY cm.event_card_id
        ORDER BY deck_count DESC
    """)
    code_matched_raw = cursor_event.fetchall()
    
    # Enhance with cache info
    code_matched = []
    for jp_name, cn_name, jp_code, cn_code, card_id, deck_count, quantity in code_matched_raw:
        cache_code = cache.get(str(card_id), "")
        code_matched.append((jp_name, cn_name, jp_code, cn_code, cache_code, deck_count, quantity))
    
    coverage = (total_mapped / total_cards * 100) if total_cards > 0 else 0
    
    # Generate HTML
    html = f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Pokemon TCG 卡片對應分析 - 雙表格模式</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: 'Microsoft JhengHei', 'PingFang TC', 'Noto Sans TC', sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 20px;
            min-height: 100vh;
        }}
        .container {{
            max-width: 1600px;
            margin: 0 auto;
            background: white;
            border-radius: 20px;
            padding: 40px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
        }}
        h1 {{
            text-align: center;
            color: #4a5568;
            font-size: 2.8em;
            margin-bottom: 15px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.1);
        }}
        .subtitle {{
            text-align: center;
            color: #718096;
            font-size: 1.2em;
            margin-bottom: 40px;
        }}
        .stats-bar {{
            display: flex;
            justify-content: space-around;
            margin: 30px 0;
            padding: 25px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border-radius: 15px;
            color: white;
        }}
        .stat-item {{
            text-align: center;
        }}
        .stat-value {{
            font-size: 2.5em;
            font-weight: bold;
            margin: 10px 0;
        }}
        .stat-label {{
            font-size: 1.1em;
            opacity: 0.9;
        }}
        .section {{
            margin: 50px 0;
        }}
        .section-header {{
            background: linear-gradient(135deg, #48bb78 0%, #38a169 100%);
            color: white;
            padding: 20px 30px;
            border-radius: 10px 10px 0 0;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .section-header.code-match {{
            background: linear-gradient(135deg, #4299e1 0%, #3182ce 100%);
        }}
        .section-title {{
            font-size: 1.8em;
            font-weight: 600;
        }}
        .section-count {{
            font-size: 1.5em;
            background: rgba(255,255,255,0.2);
            padding: 5px 20px;
            border-radius: 20px;
        }}
        .table-container {{
            overflow-x: auto;
            border: 2px solid #e2e8f0;
            border-top: none;
            border-radius: 0 0 10px 10px;
            max-height: 600px;
            overflow-y: auto;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            background: white;
        }}
        thead {{
            position: sticky;
            top: 0;
            z-index: 10;
        }}
        th {{
            background: #2d3748;
            color: white;
            padding: 15px 12px;
            text-align: left;
            font-weight: 600;
            font-size: 0.95em;
            border-bottom: 2px solid #4a5568;
        }}
        td {{
            padding: 12px;
            border-bottom: 1px solid #e2e8f0;
            font-size: 0.95em;
        }}
        tr:hover td {{
            background-color: #f7fafc;
        }}
        .rank {{
            font-weight: bold;
            color: #805ad5;
            text-align: center;
            width: 60px;
        }}
        .japanese {{
            color: #e53e3e;
            font-weight: 500;
            min-width: 180px;
        }}
        .chinese {{
            color: #38a169;
            font-weight: 600;
            font-size: 1.05em;
            min-width: 180px;
        }}
        .code {{
            font-family: 'Courier New', monospace;
            background: #edf2f7;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 0.9em;
            white-space: nowrap;
        }}
        .code.cache {{
            background: #bee3f8;
            color: #2c5282;
        }}
        .arrow {{
            color: #cbd5e0;
            margin: 0 8px;
        }}
        .count {{
            text-align: center;
            font-weight: 600;
            color: #4a5568;
        }}
        .legend {{
            display: flex;
            gap: 30px;
            justify-content: center;
            margin: 20px 0;
            padding: 15px;
            background: #f7fafc;
            border-radius: 10px;
        }}
        .legend-item {{
            display: flex;
            align-items: center;
            gap: 10px;
        }}
        .legend-color {{
            width: 20px;
            height: 20px;
            border-radius: 4px;
        }}
        .legend-color.name {{
            background: linear-gradient(135deg, #48bb78 0%, #38a169 100%);
        }}
        .legend-color.code {{
            background: linear-gradient(135deg, #4299e1 0%, #3182ce 100%);
        }}
        .footer {{
            text-align: center;
            margin-top: 50px;
            padding-top: 30px;
            border-top: 2px solid #e2e8f0;
            color: #718096;
        }}
        .highlight-top {{
            background: linear-gradient(90deg, #fef5e7 0%, #fff 100%);
        }}
        .highlight-top .rank {{
            color: #d69e2e;
            font-size: 1.2em;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🎴 Pokemon TCG 卡片對應分析報告</h1>
        <p class="subtitle">
            日文錦標賽卡片 → 中文資料庫對應<br>
            生成時間: {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}
        </p>
        
        <div class="stats-bar">
            <div class="stat-item">
                <div class="stat-label">總卡片種類</div>
                <div class="stat-value">{total_cards:,}</div>
            </div>
            <div class="stat-item">
                <div class="stat-label">已對應卡片</div>
                <div class="stat-value">{total_mapped:,}</div>
            </div>
            <div class="stat-item">
                <div class="stat-label">覆蓋率</div>
                <div class="stat-value">{coverage:.1f}%</div>
            </div>
        </div>
        
        <div class="legend">
            <div class="legend-item">
                <div class="legend-color name"></div>
                <span><strong>名稱匹配:</strong> 基本能量卡、ACE SPEC卡、同名卡片</span>
            </div>
            <div class="legend-item">
                <div class="legend-color code"></div>
                <span><strong>代碼匹配:</strong> 擴充包代碼 + 收藏編號（含快取資料）</span>
            </div>
        </div>
        
        <!-- NAME MATCHING TABLE -->
        <div class="section">
            <div class="section-header">
                <div class="section-title">🎯 名稱匹配卡片</div>
                <div class="section-count">{len(name_matched):,} 張</div>
            </div>
            <div class="table-container">
                <table>
                    <thead>
                        <tr>
                            <th class="rank">#</th>
                            <th>日文名稱</th>
                            <th>中文名稱</th>
                            <th>事件代碼</th>
                            <th>資料庫代碼</th>
                            <th class="count">套牌數</th>
                            <th class="count">總數量</th>
                        </tr>
                    </thead>
                    <tbody>
"""
    
    # Name-matched cards
    for i, (jp_name, cn_name, jp_code, cn_code, deck_count, quantity) in enumerate(name_matched, 1):
        row_class = "highlight-top" if i <= 3 else ""
        jp_code_display = jp_code if jp_code else "無代碼"
        cn_code_display = cn_code if cn_code else "無代碼"
        
        html += f"""                        <tr class="{row_class}">
                            <td class="rank">{i}</td>
                            <td class="japanese">{jp_name}</td>
                            <td class="chinese">{cn_name}</td>
                            <td><span class="code">{jp_code_display}</span></td>
                            <td><span class="code">{cn_code_display}</span></td>
                            <td class="count">{deck_count:,}</td>
                            <td class="count">{quantity:,}</td>
                        </tr>
"""
    
    html += f"""                    </tbody>
                </table>
            </div>
        </div>
        
        <!-- CODE MATCHING TABLE -->
        <div class="section">
            <div class="section-header code-match">
                <div class="section-title">📦 代碼匹配卡片（含快取）</div>
                <div class="section-count">{len(code_matched):,} 張</div>
            </div>
            <div class="table-container">
                <table>
                    <thead>
                        <tr>
                            <th class="rank">#</th>
                            <th>日文名稱</th>
                            <th>中文名稱</th>
                            <th>事件代碼</th>
                            <th>快取代碼</th>
                            <th>資料庫代碼</th>
                            <th class="count">套牌數</th>
                            <th class="count">總數量</th>
                        </tr>
                    </thead>
                    <tbody>
"""
    
    # Code-matched cards with cache
    for i, (jp_name, cn_name, jp_code, cn_code, cache_code, deck_count, quantity) in enumerate(code_matched, 1):
        row_class = "highlight-top" if i <= 3 else ""
        jp_code_display = jp_code if jp_code else "無代碼"
        cache_code_display = cache_code if cache_code else "無快取"
        cn_code_display = cn_code if cn_code else "無代碼"
        
        html += f"""                        <tr class="{row_class}">
                            <td class="rank">{i}</td>
                            <td class="japanese">{jp_name}</td>
                            <td class="chinese">{cn_name}</td>
                            <td><span class="code">{jp_code_display}</span></td>
                            <td><span class="code cache">{cache_code_display}</span></td>
                            <td><span class="code">{cn_code_display}</span></td>
                            <td class="count">{deck_count:,}</td>
                            <td class="count">{quantity:,}</td>
                        </tr>
"""
    
    html += f"""                    </tbody>
                </table>
            </div>
        </div>
        
        <div class="footer">
            <p><strong>Pokemon TCG 雙表格卡片對應系統</strong></p>
            <p style="margin: 10px 0;">
                <strong>名稱匹配:</strong> {len(name_matched):,} 張卡片<br>
                <strong>代碼匹配:</strong> {len(code_matched):,} 張卡片<br>
                <strong>總計對應:</strong> {total_mapped:,} 張卡片
            </p>
            <p style="font-size: 0.9em; margin-top: 15px; color: #a0aec0;">
                資料庫: ptcg_events.db | pokemon_cards.db | card_code_cache.json<br>
                排除擴充包: MBD, MBG (編號不可靠)
            </p>
        </div>
    </div>
</body>
</html>"""
    
    # Write HTML file
    output_file = "card_mapping_two_tables.html"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f"✅ 雙表格HTML報告已生成: {output_file}")
    print(f"\n📊 統計摘要:")
    print(f"   總卡片種類: {total_cards:,}")
    print(f"   已對應總數: {total_mapped:,} ({coverage:.1f}%)")
    print(f"\n📋 分類統計:")
    print(f"   🎯 名稱匹配: {len(name_matched):,} 張")
    print(f"   📦 代碼匹配: {len(code_matched):,} 張")
    print(f"\n💾 快取資料:")
    print(f"   快取記錄數: {len(cache):,}")
    
    conn_event.close()
    conn_main.close()

if __name__ == "__main__":
    generate_two_table_html()
