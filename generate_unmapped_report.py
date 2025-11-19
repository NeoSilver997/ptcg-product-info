"""
Generate Unmapped Cards Report
================================
Creates detailed HTML report for cards that are NOT yet mapped
Shows which cards need attention for mapping work
"""

import sqlite3
from datetime import datetime

EVENT_DB = "ptcg_events.db"

def generate_unmapped_report():
    conn = sqlite3.connect(EVENT_DB)
    cursor = conn.cursor()
    
    # Get overall statistics
    cursor.execute("SELECT COUNT(DISTINCT card_id) FROM deck_cards")
    total_cards = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(DISTINCT event_card_id) FROM card_mappings")
    mapped_cards = cursor.fetchone()[0]
    
    unmapped_cards = total_cards - mapped_cards
    unmapped_pct = (unmapped_cards / total_cards * 100) if total_cards > 0 else 0
    
    # Get total usage statistics
    cursor.execute("SELECT SUM(quantity) FROM deck_cards")
    total_usage = cursor.fetchone()[0]
    
    cursor.execute("""
        SELECT SUM(dc.quantity) 
        FROM deck_cards dc
        JOIN card_mappings cm ON dc.card_id = cm.event_card_id
    """)
    mapped_usage = cursor.fetchone()[0] or 0
    
    unmapped_usage = total_usage - mapped_usage
    usage_pct = (unmapped_usage / total_usage * 100) if total_usage > 0 else 0
    
    # Get unmapped cards with usage statistics
    cursor.execute("""
        SELECT 
            dc.card_name,
            dc.card_code,
            COUNT(DISTINCT dc.deck_id) as deck_count,
            SUM(dc.quantity) as total_quantity,
            ROUND(COUNT(DISTINCT dc.deck_id) * 100.0 / 
                (SELECT COUNT(DISTINCT deck_id) FROM decks), 2) as deck_percentage
        FROM deck_cards dc
        LEFT JOIN card_mappings cm ON dc.card_id = cm.event_card_id
        WHERE cm.event_card_id IS NULL
        GROUP BY dc.card_id
        ORDER BY deck_count DESC, total_quantity DESC
    """)
    unmapped_list = cursor.fetchall()
    
    # Analyze unmapped card types
    cursor.execute("""
        SELECT 
            CASE 
                WHEN card_name LIKE '%エネルギー%' OR card_name LIKE '%Energy%' THEN 'Basic Energy'
                WHEN card_name LIKE '%ex' OR card_name LIKE '%V%' OR card_name LIKE '%VSTAR%' 
                    OR card_name LIKE '%VMAX%' OR card_name LIKE '%GX%' THEN 'Special Pokemon'
                WHEN card_code LIKE '%/%' THEN 'Regular Card'
                ELSE 'Unknown Type'
            END as card_type,
            COUNT(DISTINCT dc.card_id) as type_count,
            SUM(dc.quantity) as type_usage
        FROM deck_cards dc
        LEFT JOIN card_mappings cm ON dc.card_id = cm.event_card_id
        WHERE cm.event_card_id IS NULL
        GROUP BY card_type
        ORDER BY type_count DESC
    """)
    type_breakdown = cursor.fetchall()
    
    # Get top unmapped expansion codes
    cursor.execute("""
        SELECT 
            SUBSTR(card_code, 1, INSTR(card_code || ' ', ' ') - 1) as expansion,
            COUNT(DISTINCT dc.card_id) as card_count,
            SUM(dc.quantity) as usage_count
        FROM deck_cards dc
        LEFT JOIN card_mappings cm ON dc.card_id = cm.event_card_id
        WHERE cm.event_card_id IS NULL 
            AND card_code IS NOT NULL 
            AND card_code != ''
        GROUP BY expansion
        ORDER BY card_count DESC
        LIMIT 20
    """)
    expansion_breakdown = cursor.fetchall()
    
    # Generate HTML
    html = f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>未對應卡片分析報告</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: 'Microsoft JhengHei', 'PingFang TC', 'Noto Sans TC', sans-serif;
            background: linear-gradient(135deg, #fc466b 0%, #3f5efb 100%);
            padding: 20px;
            min-height: 100vh;
        }}
        .container {{
            max-width: 1800px;
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
        .warning-badge {{
            display: inline-block;
            background: linear-gradient(135deg, #fc466b 0%, #e74c3c 100%);
            color: white;
            padding: 8px 20px;
            border-radius: 20px;
            font-size: 0.9em;
            margin-left: 15px;
        }}
        .subtitle {{
            text-align: center;
            color: #718096;
            font-size: 1.2em;
            margin-bottom: 40px;
        }}
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 25px;
            margin: 40px 0;
        }}
        .stat-card {{
            padding: 30px;
            border-radius: 15px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            transition: transform 0.3s ease;
        }}
        .stat-card:hover {{
            transform: translateY(-5px);
        }}
        .stat-card.warning {{
            background: linear-gradient(135deg, #fc466b 0%, #e74c3c 100%);
        }}
        .stat-card.info {{
            background: linear-gradient(135deg, #4299e1 0%, #3182ce 100%);
        }}
        .stat-value {{
            font-size: 3em;
            font-weight: bold;
            margin: 15px 0;
        }}
        .stat-label {{
            font-size: 1.1em;
            opacity: 0.9;
        }}
        .section {{
            margin: 50px 0;
        }}
        .section-header {{
            background: linear-gradient(135deg, #fc466b 0%, #e74c3c 100%);
            color: white;
            padding: 20px 30px;
            border-radius: 10px 10px 0 0;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .section-header.breakdown {{
            background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        }}
        .section-header.expansion {{
            background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
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
            background-color: #fff5f5;
        }}
        .rank {{
            font-weight: bold;
            color: #e53e3e;
            text-align: center;
            width: 60px;
        }}
        .card-name {{
            color: #2d3748;
            font-weight: 600;
            min-width: 200px;
        }}
        .card-code {{
            font-family: 'Courier New', monospace;
            background: #fed7d7;
            color: #c53030;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 0.9em;
            white-space: nowrap;
        }}
        .count {{
            text-align: center;
            font-weight: 600;
            color: #4a5568;
        }}
        .percentage {{
            text-align: center;
            font-weight: 600;
            color: #e53e3e;
        }}
        .priority-high {{
            background: linear-gradient(90deg, #fee 0%, #fff 100%);
        }}
        .priority-high .rank {{
            color: #c53030;
            font-size: 1.3em;
        }}
        .priority-medium {{
            background: linear-gradient(90deg, #fffbeb 0%, #fff 100%);
        }}
        .breakdown-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
            gap: 30px;
            margin: 30px 0;
        }}
        .breakdown-card {{
            background: white;
            border-radius: 15px;
            padding: 25px;
            border: 2px solid #e2e8f0;
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
        }}
        .breakdown-title {{
            font-size: 1.5em;
            font-weight: 600;
            color: #2d3748;
            margin-bottom: 20px;
            padding-bottom: 15px;
            border-bottom: 2px solid #e2e8f0;
        }}
        .breakdown-item {{
            display: flex;
            justify-content: space-between;
            padding: 12px;
            margin: 8px 0;
            background: #f7fafc;
            border-radius: 8px;
            transition: background 0.2s;
        }}
        .breakdown-item:hover {{
            background: #edf2f7;
        }}
        .breakdown-label {{
            font-weight: 500;
            color: #4a5568;
        }}
        .breakdown-value {{
            font-weight: 600;
            color: #e53e3e;
        }}
        .alert-box {{
            background: linear-gradient(135deg, #fff5f5 0%, #fed7d7 100%);
            border-left: 5px solid #e53e3e;
            padding: 20px;
            margin: 30px 0;
            border-radius: 10px;
        }}
        .alert-title {{
            font-size: 1.3em;
            font-weight: 600;
            color: #c53030;
            margin-bottom: 10px;
        }}
        .alert-text {{
            color: #742a2a;
            line-height: 1.6;
        }}
        .footer {{
            text-align: center;
            margin-top: 50px;
            padding-top: 30px;
            border-top: 2px solid #e2e8f0;
            color: #718096;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>
            ⚠️ 未對應卡片分析報告
            <span class="warning-badge">需要處理</span>
        </h1>
        <p class="subtitle">
            日文錦標賽卡片 - 尚未對應至中文資料庫<br>
            生成時間: {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}
        </p>
        
        <div class="stats-grid">
            <div class="stat-card warning">
                <div class="stat-label">未對應卡片種類</div>
                <div class="stat-value">{unmapped_cards:,}</div>
                <div class="stat-label">佔總卡片 {unmapped_pct:.1f}%</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">已對應卡片種類</div>
                <div class="stat-value">{mapped_cards:,}</div>
                <div class="stat-label">佔總卡片 {100-unmapped_pct:.1f}%</div>
            </div>
            <div class="stat-card warning">
                <div class="stat-label">未對應使用次數</div>
                <div class="stat-value">{unmapped_usage:,}</div>
                <div class="stat-label">佔總使用 {usage_pct:.1f}%</div>
            </div>
            <div class="stat-card info">
                <div class="stat-label">總卡片種類</div>
                <div class="stat-value">{total_cards:,}</div>
                <div class="stat-label">全部錦標賽卡片</div>
            </div>
        </div>
        
        <div class="alert-box">
            <div class="alert-title">📋 優先處理建議</div>
            <div class="alert-text">
                <strong>高優先級 (Top 50):</strong> 在 500+ 套牌中出現的卡片，對競技環境影響最大<br>
                <strong>中優先級 (51-200):</strong> 在 100-499 套牌中出現的卡片，常見於特定構築<br>
                <strong>低優先級 (201+):</strong> 較少使用的卡片，可以稍後處理
            </div>
        </div>
        
        <!-- TYPE BREAKDOWN -->
        <div class="section">
            <div class="section-header breakdown">
                <div class="section-title">📊 卡片類型分佈</div>
            </div>
            <div class="breakdown-grid">
"""
    
    for card_type, type_count, type_usage in type_breakdown:
        pct = (type_count / unmapped_cards * 100) if unmapped_cards > 0 else 0
        html += f"""                <div class="breakdown-card">
                    <div class="breakdown-title">{card_type}</div>
                    <div class="breakdown-item">
                        <span class="breakdown-label">卡片種類數</span>
                        <span class="breakdown-value">{type_count:,} 種 ({pct:.1f}%)</span>
                    </div>
                    <div class="breakdown-item">
                        <span class="breakdown-label">總使用次數</span>
                        <span class="breakdown-value">{type_usage:,} 次</span>
                    </div>
                    <div class="breakdown-item">
                        <span class="breakdown-label">平均使用</span>
                        <span class="breakdown-value">{type_usage/type_count:.1f} 次/卡</span>
                    </div>
                </div>
"""
    
    html += f"""            </div>
        </div>
        
        <!-- EXPANSION BREAKDOWN -->
        <div class="section">
            <div class="section-header expansion">
                <div class="section-title">📦 擴充包分佈 (Top 20)</div>
            </div>
            <div class="table-container">
                <table>
                    <thead>
                        <tr>
                            <th class="rank">#</th>
                            <th>擴充包代碼</th>
                            <th class="count">卡片種類數</th>
                            <th class="count">總使用次數</th>
                            <th class="percentage">平均使用</th>
                        </tr>
                    </thead>
                    <tbody>
"""
    
    for i, (expansion, card_count, usage_count) in enumerate(expansion_breakdown, 1):
        avg_usage = usage_count / card_count if card_count > 0 else 0
        html += f"""                        <tr>
                            <td class="rank">{i}</td>
                            <td class="card-name">{expansion}</td>
                            <td class="count">{card_count:,}</td>
                            <td class="count">{usage_count:,}</td>
                            <td class="percentage">{avg_usage:.1f}</td>
                        </tr>
"""
    
    html += f"""                    </tbody>
                </table>
            </div>
        </div>
        
        <!-- UNMAPPED CARDS LIST -->
        <div class="section">
            <div class="section-header">
                <div class="section-title">🔍 未對應卡片清單 (全部 {len(unmapped_list):,} 張)</div>
                <div class="section-count">{unmapped_cards:,} 種</div>
            </div>
            <div class="table-container">
                <table>
                    <thead>
                        <tr>
                            <th class="rank">#</th>
                            <th>卡片名稱 (日文)</th>
                            <th>卡片代碼</th>
                            <th class="count">套牌數</th>
                            <th class="count">總數量</th>
                            <th class="percentage">套牌占比</th>
                        </tr>
                    </thead>
                    <tbody>
"""
    
    for i, (card_name, card_code, deck_count, quantity, deck_pct) in enumerate(unmapped_list, 1):
        if deck_count >= 500:
            row_class = "priority-high"
        elif deck_count >= 100:
            row_class = "priority-medium"
        else:
            row_class = ""
        
        code_display = card_code if card_code else "無代碼"
        
        html += f"""                        <tr class="{row_class}">
                            <td class="rank">{i}</td>
                            <td class="card-name">{card_name}</td>
                            <td><span class="card-code">{code_display}</span></td>
                            <td class="count">{deck_count:,}</td>
                            <td class="count">{quantity:,}</td>
                            <td class="percentage">{deck_pct:.2f}%</td>
                        </tr>
"""
    
    html += f"""                    </tbody>
                </table>
            </div>
        </div>
        
        <div class="footer">
            <p><strong>未對應卡片分析系統</strong></p>
            <p style="margin: 10px 0;">
                <strong>未對應:</strong> {unmapped_cards:,} 種卡片 ({unmapped_pct:.1f}%)<br>
                <strong>未對應使用:</strong> {unmapped_usage:,} 次 ({usage_pct:.1f}%)
            </p>
            <p style="font-size: 0.9em; margin-top: 15px; color: #a0aec0;">
                資料庫: ptcg_events.db<br>
                優先處理高使用率卡片以提升覆蓋率
            </p>
        </div>
    </div>
</body>
</html>"""
    
    # Write HTML file
    output_file = "unmapped_cards_report.html"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f"✅ 未對應卡片報告已生成: {output_file}")
    print(f"\n📊 統計摘要:")
    print(f"   總卡片種類: {total_cards:,}")
    print(f"   未對應種類: {unmapped_cards:,} ({unmapped_pct:.1f}%)")
    print(f"   已對應種類: {mapped_cards:,} ({100-unmapped_pct:.1f}%)")
    print(f"\n💡 使用統計:")
    print(f"   總使用次數: {total_usage:,}")
    print(f"   未對應使用: {unmapped_usage:,} ({usage_pct:.1f}%)")
    print(f"   已對應使用: {mapped_usage:,} ({100-usage_pct:.1f}%)")
    print(f"\n🎯 優先級:")
    high_priority = sum(1 for _, _, deck_count, _, _ in unmapped_list if deck_count >= 500)
    medium_priority = sum(1 for _, _, deck_count, _, _ in unmapped_list if 100 <= deck_count < 500)
    low_priority = sum(1 for _, _, deck_count, _, _ in unmapped_list if deck_count < 100)
    print(f"   高優先級 (500+ 套牌): {high_priority} 種")
    print(f"   中優先級 (100-499 套牌): {medium_priority} 種")
    print(f"   低優先級 (<100 套牌): {low_priority} 種")
    
    conn.close()

if __name__ == "__main__":
    generate_unmapped_report()
