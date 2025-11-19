"""
Generate HTML Summary Report with Chinese Names
==============================================
Creates a comprehensive HTML report showing:
- Card mapping statistics
- Top mapped cards with Chinese names
- Unmapped cards with translations
- Category breakdowns
"""

import sqlite3
from datetime import datetime

EVENT_DB = "ptcg_events.db"
MAIN_DB = r"c:\AI_Server\Coding\PokemonDBByjules\PTCG_CardDB_Tc\pokemon_cards.db"

def generate_html_summary():
    conn_event = sqlite3.connect(EVENT_DB)
    conn_main = sqlite3.connect(MAIN_DB)
    
    cursor_event = conn_event.cursor()
    cursor_main = conn_main.cursor()
    
    # Get mapping statistics
    cursor_event.execute("SELECT COUNT(DISTINCT event_card_id) FROM card_mappings")
    total_mapped = cursor_event.fetchone()[0]
    
    cursor_event.execute("SELECT COUNT(DISTINCT card_id) FROM deck_cards")
    total_cards = cursor_event.fetchone()[0]
    
    cursor_event.execute("SELECT COUNT(*) FROM deck_cards")
    total_instances = cursor_event.fetchone()[0]
    
    cursor_event.execute("""
        SELECT COUNT(*)
        FROM deck_cards dc
        JOIN card_mappings cm ON dc.card_id = cm.event_card_id
    """)
    mapped_instances = cursor_event.fetchone()[0]
    
    coverage = (total_mapped / total_cards * 100) if total_cards > 0 else 0
    usage_coverage = (mapped_instances / total_instances * 100) if total_instances > 0 else 0
    
    # Get mapping breakdown by type
    cursor_event.execute("""
        SELECT match_type, COUNT(*) as count
        FROM card_mappings
        GROUP BY match_type
        ORDER BY count DESC
    """)
    mapping_types = cursor_event.fetchall()
    
    # Get top 50 mapped cards with Chinese names
    cursor_event.execute("""
        SELECT 
            cm.event_card_name as japanese,
            cm.main_card_name as chinese,
            cm.event_card_code,
            cm.main_expansion_code,
            COUNT(DISTINCT dc.deck_id) as deck_count,
            SUM(dc.quantity) as total_quantity,
            cm.match_type
        FROM card_mappings cm
        JOIN deck_cards dc ON cm.event_card_id = dc.card_id
        GROUP BY cm.event_card_id
        ORDER BY deck_count DESC
        LIMIT 50
    """)
    top_mapped = cursor_event.fetchall()
    
    # Get top 50 unmapped cards
    cursor_event.execute("""
        SELECT 
            dc.card_name as japanese,
            dc.card_code,
            COUNT(DISTINCT dc.deck_id) as deck_count,
            SUM(dc.quantity) as total_quantity
        FROM deck_cards dc
        LEFT JOIN card_mappings cm ON dc.card_id = cm.event_card_id
        WHERE cm.event_card_id IS NULL
        GROUP BY dc.card_name, dc.card_code
        ORDER BY deck_count DESC
        LIMIT 50
    """)
    top_unmapped = cursor_event.fetchall()
    
    # Common translations for unmapped cards
    COMMON_TRANSLATIONS = {
        'ナンジャモ': '奇樹',
        'ボウルタウン': '寶可夢中心小鎮',
        'ペパー': '派帕',
        'なかよしポフィン': '好友寶芬',
        'カウンターキャッチャー': '反擊捕捉器',
        'ボスの指令': '老大的指令',
        'カルボウ': '炭小侍',
        '夜のタンカ': '夜之擔架',
        'すごいつりざお': '厲害釣竿',
        'ヒトカゲ': '小火龍',
        'ハイパーボール': '高級球',
        'ネストボール': '巢穴球',
        'ふしぎなアメ': '神奇糖果',
        'マシマシラ': '願增猿',
        'ソウブレイズex': '蒼炎刃鬼ex',
        '勇気のおまもり': '勇氣護符',
        'ルミナスエネルギー': '光明能量',
        'スーパーエネルギー回収': '超級能量回收',
        'ふうせん': '氣球',
        'ゼロの大空洞': '零之大空洞',
        'サーナイトex': '沙奈朵ex',
        '博士の研究': '博士的研究',
        'イキリンコex': '怒鸚哥ex',
        'ラティアスex': '拉帝亞斯ex',
        '大地の器': '大地之器',
        'ポケギア3.0': '寶可齒輪3.0',
        'エネルギーつけかえ': '能量轉移',
        'ポケモンいれかえ': '寶可夢替換',
        'リバーサルエネルギー': '逆轉能量',
        'リザードンex': '噴火龍ex',
        'ジェットエネルギー': '噴射能量',
        'エネルギー転送': '能量輸送',
        'ともだちてちょう': '朋友筆記本',
        'げんきのハチマキ': '元氣頭帶',
        'オーリム博士の気迫': '奧琳博士的氣魄',
        'ストライク': '飛天螳螂',
        'リザード': '火恐龍',
        'ミライドンex': '密勒頓ex',
        '改造ハンマー': '改造錘',
        'ボタン': '佩帕',
    }
    
    # Generate HTML
    html = f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Pokemon TCG 卡片對應統計報告</title>
    <style>
        body {{
            font-family: 'Microsoft JhengHei', 'PingFang TC', 'Noto Sans TC', sans-serif;
            max-width: 1400px;
            margin: 0 auto;
            padding: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: #333;
        }}
        .container {{
            background: white;
            border-radius: 15px;
            padding: 30px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.3);
        }}
        h1 {{
            text-align: center;
            color: #4a5568;
            font-size: 2.5em;
            margin-bottom: 10px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.1);
        }}
        .subtitle {{
            text-align: center;
            color: #718096;
            font-size: 1.1em;
            margin-bottom: 30px;
        }}
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin: 30px 0;
        }}
        .stat-card {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 25px;
            border-radius: 10px;
            text-align: center;
            box-shadow: 0 4px 15px rgba(0,0,0,0.2);
            transition: transform 0.3s;
        }}
        .stat-card:hover {{
            transform: translateY(-5px);
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
            margin: 40px 0;
        }}
        .section-title {{
            font-size: 1.8em;
            color: #4a5568;
            border-bottom: 3px solid #667eea;
            padding-bottom: 10px;
            margin-bottom: 20px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        th {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 15px;
            text-align: left;
            font-weight: 600;
        }}
        td {{
            padding: 12px 15px;
            border-bottom: 1px solid #e2e8f0;
        }}
        tr:hover {{
            background-color: #f7fafc;
        }}
        .japanese {{
            color: #e53e3e;
            font-weight: 500;
        }}
        .chinese {{
            color: #38a169;
            font-weight: 600;
            font-size: 1.1em;
        }}
        .code {{
            color: #805ad5;
            font-family: 'Courier New', monospace;
            background: #f7fafc;
            padding: 2px 6px;
            border-radius: 3px;
        }}
        .match-type {{
            display: inline-block;
            padding: 4px 12px;
            border-radius: 15px;
            font-size: 0.85em;
            font-weight: 600;
        }}
        .match-type.expansion_code {{
            background: #bee3f8;
            color: #2c5282;
        }}
        .match-type.basic_energy {{
            background: #fbd38d;
            color: #7c2d12;
        }}
        .match-type.ace_spec {{
            background: #f687b3;
            color: #702459;
        }}
        .match-type.name_primary {{
            background: #9ae6b4;
            color: #22543d;
        }}
        .badge {{
            display: inline-block;
            padding: 5px 12px;
            border-radius: 20px;
            font-size: 0.9em;
            font-weight: 600;
            margin-left: 10px;
        }}
        .badge.mapped {{
            background: #c6f6d5;
            color: #22543d;
        }}
        .badge.unmapped {{
            background: #fed7d7;
            color: #742a2a;
        }}
        .footer {{
            text-align: center;
            margin-top: 40px;
            padding-top: 20px;
            border-top: 2px solid #e2e8f0;
            color: #718096;
        }}
        .progress-bar {{
            width: 100%;
            height: 30px;
            background: #e2e8f0;
            border-radius: 15px;
            overflow: hidden;
            margin: 20px 0;
        }}
        .progress-fill {{
            height: 100%;
            background: linear-gradient(90deg, #48bb78 0%, #38a169 100%);
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-weight: 600;
            transition: width 1s ease-out;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🎴 Pokemon TCG 卡片對應統計報告</h1>
        <p class="subtitle">日文錦標賽卡片 → 中文資料庫對應分析<br>
        生成時間: {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}</p>
        
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-label">總卡片種類</div>
                <div class="stat-value">{total_cards:,}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">已對應卡片</div>
                <div class="stat-value">{total_mapped:,}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">對應覆蓋率</div>
                <div class="stat-value">{coverage:.1f}%</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">使用率覆蓋</div>
                <div class="stat-value">{usage_coverage:.1f}%</div>
            </div>
        </div>
        
        <div class="section">
            <h2 class="section-title">📊 對應進度</h2>
            <div class="progress-bar">
                <div class="progress-fill" style="width: {coverage}%">
                    {total_mapped:,} / {total_cards:,} 卡片
                </div>
            </div>
        </div>
        
        <div class="section">
            <h2 class="section-title">🎯 對應方式統計</h2>
            <table>
                <thead>
                    <tr>
                        <th>對應方式</th>
                        <th>數量</th>
                        <th>百分比</th>
                    </tr>
                </thead>
                <tbody>
"""
    
    match_type_names = {
        'expansion_code': '擴充包代碼匹配',
        'basic_energy': '基本能量卡',
        'ace_spec': 'ACE SPEC卡',
        'name_primary': '卡名優先匹配'
    }
    
    for match_type, count in mapping_types:
        percentage = (count / total_mapped * 100) if total_mapped > 0 else 0
        type_name = match_type_names.get(match_type, match_type)
        html += f"""                    <tr>
                        <td><span class="match-type {match_type}">{type_name}</span></td>
                        <td>{count:,}</td>
                        <td>{percentage:.1f}%</td>
                    </tr>
"""
    
    html += """                </tbody>
            </table>
        </div>
        
        <div class="section">
            <h2 class="section-title">🏆 前50名最常用已對應卡片 <span class="badge mapped">已對應</span></h2>
            <table>
                <thead>
                    <tr>
                        <th>#</th>
                        <th>日文名稱</th>
                        <th>中文名稱</th>
                        <th>卡片代碼</th>
                        <th>使用套牌數</th>
                        <th>總數量</th>
                        <th>對應方式</th>
                    </tr>
                </thead>
                <tbody>
"""
    
    for i, (jp_name, cn_name, jp_code, cn_code, deck_count, quantity, match_type) in enumerate(top_mapped, 1):
        jp_code_display = jp_code if jp_code else "無代碼"
        cn_code_display = cn_code if cn_code else ""
        type_name = match_type_names.get(match_type, match_type)
        
        html += f"""                    <tr>
                        <td><strong>{i}</strong></td>
                        <td class="japanese">{jp_name}</td>
                        <td class="chinese">{cn_name}</td>
                        <td><span class="code">{jp_code_display}</span> → <span class="code">{cn_code_display}</span></td>
                        <td>{deck_count:,}</td>
                        <td>{quantity:,}</td>
                        <td><span class="match-type {match_type}">{type_name}</span></td>
                    </tr>
"""
    
    html += """                </tbody>
            </table>
        </div>
        
        <div class="section">
            <h2 class="section-title">⚠️ 前50名最常用未對應卡片 <span class="badge unmapped">未對應</span></h2>
            <table>
                <thead>
                    <tr>
                        <th>#</th>
                        <th>日文名稱</th>
                        <th>中文翻譯</th>
                        <th>卡片代碼</th>
                        <th>使用套牌數</th>
                        <th>總數量</th>
                    </tr>
                </thead>
                <tbody>
"""
    
    for i, (jp_name, jp_code, deck_count, quantity) in enumerate(top_unmapped, 1):
        cn_translation = COMMON_TRANSLATIONS.get(jp_name, '(未翻譯)')
        jp_code_display = jp_code if jp_code else "無代碼"
        
        html += f"""                    <tr>
                        <td><strong>{i}</strong></td>
                        <td class="japanese">{jp_name}</td>
                        <td class="chinese">{cn_translation}</td>
                        <td><span class="code">{jp_code_display}</span></td>
                        <td>{deck_count:,}</td>
                        <td>{quantity:,}</td>
                    </tr>
"""
    
    html += f"""                </tbody>
            </table>
        </div>
        
        <div class="section">
            <h2 class="section-title">📈 資料摘要</h2>
            <table>
                <thead>
                    <tr>
                        <th>項目</th>
                        <th>數值</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td>總卡片種類數</td>
                        <td><strong>{total_cards:,}</strong></td>
                    </tr>
                    <tr>
                        <td>已對應卡片種類</td>
                        <td><strong>{total_mapped:,}</strong></td>
                    </tr>
                    <tr>
                        <td>未對應卡片種類</td>
                        <td><strong>{total_cards - total_mapped:,}</strong></td>
                    </tr>
                    <tr>
                        <td>卡片總實例數</td>
                        <td><strong>{total_instances:,}</strong></td>
                    </tr>
                    <tr>
                        <td>已對應實例數</td>
                        <td><strong>{mapped_instances:,}</strong></td>
                    </tr>
                    <tr>
                        <td>未對應實例數</td>
                        <td><strong>{total_instances - mapped_instances:,}</strong></td>
                    </tr>
                    <tr>
                        <td>卡片種類覆蓋率</td>
                        <td><strong>{coverage:.2f}%</strong></td>
                    </tr>
                    <tr>
                        <td>套牌使用率覆蓋</td>
                        <td><strong>{usage_coverage:.2f}%</strong></td>
                    </tr>
                </tbody>
            </table>
        </div>
        
        <div class="footer">
            <p><strong>Pokemon TCG 卡片對應系統</strong></p>
            <p>日文錦標賽資料 × 中文卡片資料庫整合分析</p>
            <p style="font-size: 0.9em; margin-top: 10px;">
                資料庫: ptcg_events.db | pokemon_cards.db<br>
                排除擴充包: MBD, MBG (編號不可靠)
            </p>
        </div>
    </div>
</body>
</html>"""
    
    # Write HTML file
    output_file = "card_mapping_summary.html"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f"✅ HTML報告已生成: {output_file}")
    print(f"\n📊 統計摘要:")
    print(f"   總卡片種類: {total_cards:,}")
    print(f"   已對應: {total_mapped:,} ({coverage:.1f}%)")
    print(f"   未對應: {total_cards - total_mapped:,}")
    print(f"   使用率覆蓋: {usage_coverage:.1f}%")
    
    conn_event.close()
    conn_main.close()

if __name__ == "__main__":
    generate_html_summary()
