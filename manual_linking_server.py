"""
Manual Card Linking Web Interface
===================================
Simple web server for manually linking unmapped cards
Provides search, preview, and link functionality
"""

from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import sqlite3
import urllib.parse
from datetime import datetime

EVENT_DB = "ptcg_events.db"
MAIN_DB = r"c:\AI_Server\Coding\PokemonDBByjules\PTCG_CardDB_Tc\pokemon_cards.db"

class ManualLinkingHandler(BaseHTTPRequestHandler):
    
    def do_GET(self):
        """Handle GET requests"""
        # Parse path without query parameters
        parsed_path = urllib.parse.urlparse(self.path).path
        
        if parsed_path == '/' or parsed_path == '/index.html':
            self.serve_main_page()
        elif parsed_path.startswith('/api/unmapped'):
            self.get_unmapped_cards()
        elif parsed_path.startswith('/api/search'):
            self.search_chinese_cards()
        elif parsed_path.startswith('/api/card/'):
            self.get_card_details()
        else:
            self.send_error(404)
    
    def do_POST(self):
        """Handle POST requests"""
        if self.path == '/api/link':
            self.create_link()
        elif self.path == '/api/unlink':
            self.remove_link()
        else:
            self.send_error(404)
    
    def serve_main_page(self):
        """Serve the main HTML interface"""
        html = """<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>手動卡片對應系統</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            font-family: 'Microsoft JhengHei', 'PingFang TC', sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 20px;
            min-height: 100vh;
        }
        .container {
            max-width: 1800px;
            margin: 0 auto;
            background: white;
            border-radius: 20px;
            padding: 30px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
        }
        h1 {
            text-align: center;
            color: #4a5568;
            margin-bottom: 10px;
        }
        .subtitle {
            text-align: center;
            color: #718096;
            margin-bottom: 30px;
        }
        .stats {
            display: flex;
            gap: 20px;
            margin-bottom: 30px;
            justify-content: center;
        }
        .stat-box {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px 40px;
            border-radius: 10px;
            text-align: center;
        }
        .stat-value {
            font-size: 2em;
            font-weight: bold;
        }
        .stat-label {
            font-size: 0.9em;
            opacity: 0.9;
        }
        .main-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 30px;
        }
        .panel {
            border: 2px solid #e2e8f0;
            border-radius: 15px;
            overflow: hidden;
        }
        .panel-header {
            background: linear-gradient(135deg, #fc466b 0%, #e74c3c 100%);
            color: white;
            padding: 15px 20px;
            font-size: 1.3em;
            font-weight: 600;
        }
        .panel-header.chinese {
            background: linear-gradient(135deg, #48bb78 0%, #38a169 100%);
        }
        .panel-content {
            padding: 20px;
            max-height: 600px;
            overflow-y: auto;
        }
        .search-box {
            display: flex;
            gap: 10px;
            margin-bottom: 20px;
        }
        .search-box input {
            flex: 1;
            padding: 12px;
            border: 2px solid #e2e8f0;
            border-radius: 8px;
            font-size: 1em;
        }
        .search-box button {
            padding: 12px 30px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            border-radius: 8px;
            font-weight: 600;
            cursor: pointer;
        }
        .search-box button:hover {
            opacity: 0.9;
        }
        .card-item {
            background: #f7fafc;
            border: 2px solid #e2e8f0;
            border-radius: 10px;
            padding: 15px;
            margin-bottom: 15px;
            cursor: pointer;
            transition: all 0.3s;
        }
        .card-item:hover {
            background: #edf2f7;
            border-color: #cbd5e0;
            transform: translateX(5px);
        }
        .card-item.selected {
            background: #bee3f8;
            border-color: #3182ce;
        }
        .card-name {
            font-size: 1.2em;
            font-weight: 600;
            color: #2d3748;
            margin-bottom: 8px;
        }
        .card-name.japanese {
            color: #e53e3e;
        }
        .card-name.chinese {
            color: #38a169;
        }
        .card-code {
            font-family: 'Courier New', monospace;
            background: #edf2f7;
            padding: 4px 10px;
            border-radius: 5px;
            font-size: 0.9em;
            display: inline-block;
            margin-right: 10px;
        }
        .card-stats {
            color: #718096;
            font-size: 0.9em;
            margin-top: 8px;
        }
        .card-details {
            background: #fffbeb;
            border: 2px solid #f6e05e;
            border-radius: 10px;
            padding: 15px;
            margin-top: 10px;
        }
        .detail-row {
            display: flex;
            justify-content: space-between;
            padding: 8px 0;
            border-bottom: 1px solid #faf089;
        }
        .detail-label {
            font-weight: 600;
            color: #744210;
        }
        .detail-value {
            color: #744210;
        }
        .action-buttons {
            display: flex;
            gap: 15px;
            justify-content: center;
            margin-top: 30px;
            padding-top: 30px;
            border-top: 2px solid #e2e8f0;
        }
        .btn {
            padding: 15px 40px;
            font-size: 1.1em;
            font-weight: 600;
            border: none;
            border-radius: 10px;
            cursor: pointer;
            transition: all 0.3s;
        }
        .btn-primary {
            background: linear-gradient(135deg, #48bb78 0%, #38a169 100%);
            color: white;
        }
        .btn-primary:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 20px rgba(72, 187, 120, 0.4);
        }
        .btn-primary:disabled {
            background: #cbd5e0;
            cursor: not-allowed;
            transform: none;
        }
        .btn-secondary {
            background: linear-gradient(135deg, #fc466b 0%, #e74c3c 100%);
            color: white;
        }
        .btn-secondary:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 20px rgba(252, 70, 107, 0.4);
        }
        .message {
            padding: 15px;
            border-radius: 10px;
            margin: 20px 0;
            text-align: center;
            font-weight: 600;
        }
        .message.success {
            background: #c6f6d5;
            color: #22543d;
            border: 2px solid #48bb78;
        }
        .message.error {
            background: #fed7d7;
            color: #742a2a;
            border: 2px solid #e53e3e;
        }
        .loading {
            text-align: center;
            padding: 40px;
            color: #718096;
            font-size: 1.2em;
        }
        .empty {
            text-align: center;
            padding: 40px;
            color: #a0aec0;
            font-size: 1.1em;
        }
        .filter-buttons {
            display: flex;
            gap: 10px;
            margin-bottom: 20px;
        }
        .filter-btn {
            padding: 8px 16px;
            background: #edf2f7;
            border: 2px solid #e2e8f0;
            border-radius: 8px;
            cursor: pointer;
            font-size: 0.9em;
        }
        .filter-btn.active {
            background: #667eea;
            color: white;
            border-color: #667eea;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🔗 手動卡片對應系統</h1>
        <p class="subtitle">日文錦標賽卡片 ↔ 中文資料庫對應</p>
        
        <div class="stats">
            <div class="stat-box">
                <div class="stat-value" id="totalUnmapped">-</div>
                <div class="stat-label">待對應卡片</div>
            </div>
            <div class="stat-box">
                <div class="stat-value" id="sessionLinked">0</div>
                <div class="stat-label">本次已對應</div>
            </div>
        </div>
        
        <div id="message"></div>
        
        <div class="main-grid">
            <!-- Left Panel: Unmapped Japanese Cards -->
            <div class="panel">
                <div class="panel-header">
                    🇯🇵 未對應日文卡片
                </div>
                <div class="panel-content">
                    <div class="filter-buttons">
                        <button class="filter-btn active" onclick="filterUnmapped('all')">全部</button>
                        <button class="filter-btn" onclick="filterUnmapped('high')">高優先級 (500+)</button>
                        <button class="filter-btn" onclick="filterUnmapped('medium')">中優先級 (100-499)</button>
                        <button class="filter-btn" onclick="filterUnmapped('low')">低優先級 (<100)</button>
                    </div>
                    <div id="unmappedList" class="loading">載入中...</div>
                </div>
            </div>
            
            <!-- Right Panel: Chinese Card Search -->
            <div class="panel">
                <div class="panel-header chinese">
                    🇨🇳 中文卡片搜尋
                </div>
                <div class="panel-content">
                    <div class="search-box">
                        <input type="text" id="searchInput" placeholder="輸入卡片名稱、擴充包代碼或編號..." onkeypress="handleSearchKey(event)">
                        <button onclick="searchChineseCards()">🔍 搜尋</button>
                    </div>
                    <div id="searchResults" class="empty">請輸入搜尋條件...</div>
                </div>
            </div>
        </div>
        
        <div class="action-buttons">
            <button class="btn btn-primary" id="linkButton" onclick="linkCards()" disabled>
                ✅ 建立對應連結
            </button>
            <button class="btn btn-secondary" onclick="clearSelection()">
                🔄 清除選擇
            </button>
        </div>
    </div>
    
    <script>
        let unmappedCards = [];
        let selectedJapanese = null;
        let selectedChinese = null;
        let sessionLinked = 0;
        let currentFilter = 'all';
        
        // Load unmapped cards on page load
        window.onload = () => {
            loadUnmappedCards();
        };
        
        function loadUnmappedCards() {
            fetch('/api/unmapped')
                .then(res => res.json())
                .then(data => {
                    unmappedCards = data.cards;
                    document.getElementById('totalUnmapped').textContent = data.total;
                    renderUnmappedCards();
                })
                .catch(err => {
                    showMessage('載入失敗: ' + err.message, 'error');
                });
        }
        
        function filterUnmapped(priority) {
            currentFilter = priority;
            // Update button states
            document.querySelectorAll('.filter-btn').forEach(btn => {
                btn.classList.remove('active');
            });
            event.target.classList.add('active');
            renderUnmappedCards();
        }
        
        function renderUnmappedCards() {
            const container = document.getElementById('unmappedList');
            
            let filtered = unmappedCards;
            if (currentFilter === 'high') {
                filtered = unmappedCards.filter(c => c.deck_count >= 500);
            } else if (currentFilter === 'medium') {
                filtered = unmappedCards.filter(c => c.deck_count >= 100 && c.deck_count < 500);
            } else if (currentFilter === 'low') {
                filtered = unmappedCards.filter(c => c.deck_count < 100);
            }
            
            if (filtered.length === 0) {
                container.innerHTML = '<div class="empty">無符合條件的卡片</div>';
                return;
            }
            
            container.innerHTML = filtered.map(card => `
                <div class="card-item ${selectedJapanese?.card_id === card.card_id ? 'selected' : ''}" 
                     onclick="selectJapanese(${card.card_id})">
                    <div class="card-name japanese">${card.card_name}</div>
                    <div>
                        ${card.card_code ? `<span class="card-code">${card.card_code}</span>` : '<span class="card-code">無代碼</span>'}
                    </div>
                    <div class="card-stats">
                        📊 使用於 ${card.deck_count} 套牌 | 總計 ${card.total_quantity} 張
                    </div>
                </div>
            `).join('');
        }
        
        function selectJapanese(cardId) {
            selectedJapanese = unmappedCards.find(c => c.card_id === cardId);
            renderUnmappedCards();
            updateLinkButton();
        }
        
        function handleSearchKey(event) {
            if (event.key === 'Enter') {
                searchChineseCards();
            }
        }
        
        function searchChineseCards() {
            const query = document.getElementById('searchInput').value.trim();
            if (!query) {
                showMessage('請輸入搜尋條件', 'error');
                return;
            }
            
            const container = document.getElementById('searchResults');
            container.innerHTML = '<div class="loading">搜尋中...</div>';
            
            fetch(`/api/search?q=${encodeURIComponent(query)}`)
                .then(res => res.json())
                .then(data => {
                    if (data.cards.length === 0) {
                        container.innerHTML = '<div class="empty">未找到符合的卡片</div>';
                        return;
                    }
                    
                    container.innerHTML = data.cards.map(card => `
                        <div class="card-item ${selectedChinese?.id === card.id ? 'selected' : ''}" 
                             onclick="selectChinese(${card.id})">
                            <div class="card-name chinese">${card.name}</div>
                            <div>
                                ${card.expansion_code ? `<span class="card-code">${card.expansion_code} ${card.collector_number}</span>` : ''}
                                ${card.card_type ? `<span class="card-code">${card.card_type}</span>` : ''}
                            </div>
                            <div class="card-stats">
                                ${card.hp ? `HP: ${card.hp} | ` : ''}
                                ${card.attribute ? `屬性: ${card.attribute} | ` : ''}
                                ${card.rarity ? `稀有度: ${card.rarity}` : ''}
                            </div>
                        </div>
                    `).join('');
                })
                .catch(err => {
                    showMessage('搜尋失敗: ' + err.message, 'error');
                });
        }
        
        function selectChinese(cardId) {
            fetch(`/api/card/${cardId}`)
                .then(res => res.json())
                .then(data => {
                    selectedChinese = data;
                    updateLinkButton();
                    
                    // Highlight selected card
                    document.querySelectorAll('#searchResults .card-item').forEach(item => {
                        item.classList.remove('selected');
                    });
                    event.currentTarget.classList.add('selected');
                })
                .catch(err => {
                    showMessage('載入卡片詳情失敗: ' + err.message, 'error');
                });
        }
        
        function updateLinkButton() {
            const btn = document.getElementById('linkButton');
            if (selectedJapanese && selectedChinese) {
                btn.disabled = false;
                btn.textContent = `✅ 連結: ${selectedJapanese.card_name} → ${selectedChinese.name}`;
            } else {
                btn.disabled = true;
                btn.textContent = '✅ 建立對應連結';
            }
        }
        
        function linkCards() {
            if (!selectedJapanese || !selectedChinese) {
                showMessage('請選擇要連結的卡片', 'error');
                return;
            }
            
            fetch('/api/link', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    event_card_id: selectedJapanese.card_id,
                    event_card_name: selectedJapanese.card_name,
                    event_card_code: selectedJapanese.card_code || '',
                    main_card_id: selectedChinese.id,
                    main_card_name: selectedChinese.name,
                    main_expansion_code: selectedChinese.expansion_code || '',
                    main_collector_number: selectedChinese.collector_number || ''
                })
            })
            .then(res => res.json())
            .then(data => {
                if (data.success) {
                    showMessage(`✅ 成功連結: ${selectedJapanese.card_name} → ${selectedChinese.name}`, 'success');
                    sessionLinked++;
                    document.getElementById('sessionLinked').textContent = sessionLinked;
                    
                    // Remove from unmapped list
                    unmappedCards = unmappedCards.filter(c => c.card_id !== selectedJapanese.card_id);
                    document.getElementById('totalUnmapped').textContent = unmappedCards.length;
                    
                    clearSelection();
                    renderUnmappedCards();
                } else {
                    showMessage('連結失敗: ' + data.error, 'error');
                }
            })
            .catch(err => {
                showMessage('連結失敗: ' + err.message, 'error');
            });
        }
        
        function clearSelection() {
            selectedJapanese = null;
            selectedChinese = null;
            renderUnmappedCards();
            document.querySelectorAll('#searchResults .card-item').forEach(item => {
                item.classList.remove('selected');
            });
            updateLinkButton();
            document.getElementById('searchInput').value = '';
        }
        
        function showMessage(text, type) {
            const msgDiv = document.getElementById('message');
            msgDiv.innerHTML = `<div class="message ${type}">${text}</div>`;
            setTimeout(() => {
                msgDiv.innerHTML = '';
            }, 5000);
        }
    </script>
</body>
</html>"""
        
        self.send_response(200)
        self.send_header('Content-type', 'text/html; charset=utf-8')
        self.end_headers()
        self.wfile.write(html.encode('utf-8'))
    
    def get_unmapped_cards(self):
        """Get list of unmapped cards"""
        conn = sqlite3.connect(EVENT_DB)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                dc.card_id,
                dc.card_name,
                dc.card_code,
                COUNT(DISTINCT dc.deck_id) as deck_count,
                SUM(dc.quantity) as total_quantity
            FROM deck_cards dc
            LEFT JOIN card_mappings cm ON dc.card_id = cm.event_card_id
            WHERE cm.event_card_id IS NULL
            GROUP BY dc.card_id
            ORDER BY deck_count DESC, total_quantity DESC
            LIMIT 500
        """)
        
        cards = []
        for row in cursor.fetchall():
            cards.append({
                'card_id': row[0],
                'card_name': row[1],
                'card_code': row[2],
                'deck_count': row[3],
                'total_quantity': row[4]
            })
        
        cursor.execute("""
            SELECT COUNT(DISTINCT dc.card_id)
            FROM deck_cards dc
            LEFT JOIN card_mappings cm ON dc.card_id = cm.event_card_id
            WHERE cm.event_card_id IS NULL
        """)
        total = cursor.fetchone()[0]
        
        conn.close()
        
        self.send_json({'cards': cards, 'total': total})
    
    def search_chinese_cards(self):
        """Search Chinese card database"""
        query = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query).get('q', [''])[0]
        
        if not query:
            self.send_json({'cards': []})
            return
        
        conn = sqlite3.connect(MAIN_DB)
        cursor = conn.cursor()
        
        # Search by name, expansion code, or collector number
        cursor.execute("""
            SELECT DISTINCT
                c.id,
                c.name,
                c.card_type,
                c.hp,
                c.attribute,
                c.collector_number,
                c.rarity,
                e.code as expansion_code,
                e.name as expansion_name
            FROM cards c
            LEFT JOIN expansions e ON c.expansion_id = e.id
            WHERE c.name LIKE ? 
                OR e.code LIKE ?
                OR c.collector_number LIKE ?
            ORDER BY c.name
            LIMIT 50
        """, (f'%{query}%', f'%{query}%', f'%{query}%'))
        
        cards = []
        for row in cursor.fetchall():
            cards.append({
                'id': row[0],
                'name': row[1],
                'card_type': row[2],
                'hp': row[3],
                'attribute': row[4],
                'collector_number': row[5],
                'rarity': row[6],
                'expansion_code': row[7],
                'expansion_name': row[8]
            })
        
        conn.close()
        
        self.send_json({'cards': cards})
    
    def get_card_details(self):
        """Get detailed card information"""
        card_id = self.path.split('/')[-1]
        
        conn = sqlite3.connect(MAIN_DB)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                c.id,
                c.name,
                c.card_type,
                c.hp,
                c.attribute,
                c.collector_number,
                c.rarity,
                c.evolution_stage,
                e.code as expansion_code,
                e.name as expansion_name,
                i.name as illustrator
            FROM cards c
            LEFT JOIN expansions e ON c.expansion_id = e.id
            LEFT JOIN illustrators i ON c.illustrator_id = i.id
            WHERE c.id = ?
        """, (card_id,))
        
        row = cursor.fetchone()
        if row:
            card = {
                'id': row[0],
                'name': row[1],
                'card_type': row[2],
                'hp': row[3],
                'attribute': row[4],
                'collector_number': row[5],
                'rarity': row[6],
                'evolution_stage': row[7],
                'expansion_code': row[8],
                'expansion_name': row[9],
                'illustrator': row[10]
            }
        else:
            card = {}
        
        conn.close()
        
        self.send_json(card)
    
    def create_link(self):
        """Create manual card link"""
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        data = json.loads(post_data.decode('utf-8'))
        
        conn = sqlite3.connect(EVENT_DB)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT OR REPLACE INTO card_mappings 
                (event_card_id, event_card_name, event_card_code, 
                 main_card_id, main_card_name, main_expansion_code, 
                 main_collector_number, match_type, match_confidence)
                VALUES (?, ?, ?, ?, ?, ?, ?, 'manual_link', 1.0)
            """, (
                data['event_card_id'],
                data['event_card_name'],
                data['event_card_code'],
                data['main_card_id'],
                data['main_card_name'],
                data['main_expansion_code'],
                data['main_collector_number']
            ))
            
            conn.commit()
            self.send_json({'success': True})
        except Exception as e:
            conn.rollback()
            self.send_json({'success': False, 'error': str(e)})
        finally:
            conn.close()
    
    def remove_link(self):
        """Remove card link"""
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        data = json.loads(post_data.decode('utf-8'))
        
        conn = sqlite3.connect(EVENT_DB)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                DELETE FROM card_mappings 
                WHERE event_card_id = ?
            """, (data['event_card_id'],))
            
            conn.commit()
            self.send_json({'success': True})
        except Exception as e:
            conn.rollback()
            self.send_json({'success': False, 'error': str(e)})
        finally:
            conn.close()
    
    def send_json(self, data):
        """Send JSON response"""
        self.send_response(200)
        self.send_header('Content-type', 'application/json; charset=utf-8')
        self.end_headers()
        response = json.dumps(data, ensure_ascii=False)
        self.wfile.write(response.encode('utf-8'))
    
    def log_message(self, format, *args):
        """Custom log format"""
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {format % args}")

def run_server(port=8080):
    """Run the manual linking server"""
    server_address = ('', port)
    httpd = HTTPServer(server_address, ManualLinkingHandler)
    
    print("="*70)
    print("🔗 手動卡片對應系統")
    print("="*70)
    print(f"\n✅ 伺服器啟動成功!")
    print(f"🌐 請在瀏覽器開啟: http://localhost:{port}")
    print(f"\n💡 使用說明:")
    print("   1. 左側選擇未對應的日文卡片")
    print("   2. 右側搜尋並選擇對應的中文卡片")
    print("   3. 點擊「建立對應連結」完成配對")
    print(f"\n⌨️  按 Ctrl+C 停止伺服器")
    print("="*70)
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n\n⏹️  伺服器已停止")
        httpd.shutdown()

if __name__ == "__main__":
    run_server(8080)
