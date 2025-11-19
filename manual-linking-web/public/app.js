// API Base URL
const API_BASE = 'http://localhost:3000/api';

// Common translations dictionary
const TRANSLATIONS = {
    // Trainers
    'ナンジャモ': '奇樹',
    'ボスの指令': '老大的指令',
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
    'ブーストエナジー古代': 'Boost能量【古代】',
    'ブーストエナジー未来': 'Boost能量【未來】',
    'ポケモンリバース': '寶可夢逆轉',
    'ペパー': '派帕',
    'ボウルタウン': '寶可夢中心小鎮',
    'ともだちてちょう': '好朋友手冊',
    'シマボシ': '璀璨',
    'タウンデパート': '城鎮百貨公司',
    'サカキのカリスマ': '坂木的魅力',
    'キャンセルコロン': '取消香水',
    'ポケモンリーグ本部': '寶可夢聯盟總部',
    'カウンターゲイン': '反擊增益',
    'エイチ湖': 'H湖',
    'クラベル': '克拉韋爾',
    'ポケギア3.0': '寶可夢裝置3.0',
    'トレッキングシューズ': '登山鞋',
    'アクロマの実験': '阿克羅瑪的實驗',
    'キバナ': '奇巴納',
    'ジャッジマン': '裁判員',
    '勇気のおまもり': '勇氣守護',
    'ダブルターボエネルギー': '雙倍Turbo能量',
    'ジェットエネルギー': 'Jet能量',
    'リバーサルエネルギー': '逆轉能量',
    'ギフトエネルギー': '禮物能量',
    'レガシーエネルギー': '傳承能量',
    'ルミナスエネルギー': '光輝能量',
    'セラピーエネルギー': '治療能量',
    
    // ACE SPEC cards
    'プライムキャッチャー': '頂尖捕捉器',
    'マスターボール': '大師球',
    'シークレットボックス': '秘密箱',
    'ネオアッパーエネルギー': '新衝天能量',
    'ポケストップ': '寶可夢補給站',
    'マキシマムベルト': '極限腰帶',
    'プレシャスキャリー': '貴重手推車',
    'ヒーローマント': '英雄斗篷',
    'アンフェアスタンプ': '不公印章',
    'エネルギー転送PRO': '能量輸送PRO',
    'きらめく結晶': '璀璨結晶',
    
    // Pokemon
    'リザードンex': '噴火龍ex',
    'ピカチュウex': '皮卡丘ex',
    'ミュウツーex': '超夢ex',
    'レジドラゴ': '雷吉鐸拉戈',
    'アルセウスVSTAR': '阿爾宙斯VSTAR',
    'ゲンガーex': '耿鬼ex',
    'サーナイトex': '沙奈朵ex',
    'ロトムV': '洛托姆V',
    'テツノカイナex': '鐵武者ex',
    'イキリンコex': '怒鸚哥ex',
    'レジエレキ': '雷吉艾勒奇',
    'ブリジュラスex': '凍原熊ex',
    'ミライドンex': '密勒頓ex',
    'コライドンex': '故勒頓ex',
    'ドラパルトex': '多龍巴魯托ex',
    'かがやくゲッコウガ': '閃耀甲賀忍蛙',
    'ルギアVSTAR': '洛奇亞VSTAR',
    'ギラティナVSTAR': '騎拉帝納VSTAR',
    'レントラー': '倫琴貓',
};

// State
let unmappedCards = [];
let selectedJapanese = null;
let selectedJapaneseGroup = null; // Store entire group for batch linking
let selectedChinese = null;
let currentFilter = 'all';

// Initialize
window.addEventListener('DOMContentLoaded', () => {
    loadStatistics();
    loadUnmappedCards();
    
    // Make functions globally accessible for inline onclick handlers
    window.selectJapaneseGroup = selectJapaneseGroup;
    window.selectJapanese = selectJapanese;
    window.toggleVariants = toggleVariants;
    window.filterUnmapped = filterUnmapped;
    window.handleSearchKey = handleSearchKey;
    window.searchChineseCards = searchChineseCards;
    window.selectChinese = selectChinese;
    window.linkCards = linkCards;
    window.clearSelection = clearSelection;
    window.loadUnmappedCards = loadUnmappedCards;
});

// Load statistics
async function loadStatistics() {
    try {
        const response = await fetch(`${API_BASE}/stats`);
        const data = await response.json();
        
        document.getElementById('totalCards').textContent = data.total.toLocaleString();
        document.getElementById('mappedCards').textContent = data.mapped.toLocaleString();
        document.getElementById('unmappedCards').textContent = data.unmapped.toLocaleString();
        document.getElementById('manualLinks').textContent = data.manual.toLocaleString();
        document.getElementById('coverage').textContent = data.coverage + '%';
    } catch (error) {
        console.error('Failed to load statistics:', error);
    }
}

// Load unmapped cards
async function loadUnmappedCards() {
    const container = document.getElementById('unmappedList');
    container.innerHTML = '<div class="loading">載入中</div>';
    
    try {
        const response = await fetch(`${API_BASE}/unmapped`);
        const data = await response.json();
        
        unmappedCards = data.cards;
        renderUnmappedCards();
    } catch (error) {
        container.innerHTML = '<div class="empty">載入失敗: ' + error.message + '</div>';
    }
}

// Filter unmapped cards
function filterUnmapped(priority) {
    currentFilter = priority;
    
    // Update button states
    document.querySelectorAll('.filter-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    event.target.classList.add('active');
    
    renderUnmappedCards();
}

// Render unmapped cards
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
    
    // Group by card name
    const grouped = {};
    filtered.forEach(card => {
        if (!grouped[card.card_name]) {
            grouped[card.card_name] = {
                name: card.card_name,
                cards: [],
                totalDecks: 0,
                totalQuantity: 0
            };
        }
        grouped[card.card_name].cards.push(card);
        grouped[card.card_name].totalDecks += card.deck_count;
        grouped[card.card_name].totalQuantity += card.total_quantity;
    });
    
    // Convert to array and sort by total decks
    const groupedArray = Object.values(grouped).sort((a, b) => b.totalDecks - a.totalDecks);
    
    container.innerHTML = groupedArray.map(group => {
        const chineseName = TRANSLATIONS[group.name] || '';
        const primaryCode = group.cards[0].card_code || '無代碼';
        const nameDisplay = chineseName 
            ? `<div class="card-name japanese">${escapeHtml(group.name)} <span class="primary-code">${escapeHtml(primaryCode)}</span></div>
               <div class="card-name chinese">${escapeHtml(chineseName)}</div>`
            : `<div class="card-name japanese">${escapeHtml(group.name)} <span class="primary-code">${escapeHtml(primaryCode)}</span></div>`;
        
        const safeId = createSafeId(group.name);
        const variantsHtml = group.cards.length > 1 ? `
            <div class="card-variants">
                <div class="variants-header" onclick="toggleVariants(event, '${safeId}')">
                    📦 ${group.cards.length} 個版本 <span class="toggle-icon">▼</span>
                </div>
                <div class="variants-list" id="variants-${safeId}" style="display: none;">
                    ${group.cards.map(card => `
                        <div class="variant-item ${selectedJapanese?.card_id === card.card_id ? 'selected' : ''}" 
                             onclick="event.stopPropagation(); selectJapanese(${card.card_id})">
                            <span class="card-code">${card.card_code || '無代碼'}</span>
                            <span class="variant-stats">
                                ${card.deck_count.toLocaleString()} 套牌 | ${card.total_quantity.toLocaleString()} 張
                            </span>
                        </div>
                    `).join('')}
                </div>
            </div>
        ` : ``;
        
        const isSelected = selectedJapaneseGroup && group.cards.some(card => 
            selectedJapaneseGroup.some(sg => sg.card_id === card.card_id)
        );
        const firstCardId = group.cards[0].card_id;
        
        return `
        <div class="card-group ${isSelected ? 'selected' : ''}" data-card-id="${firstCardId}">
            <div class="card-group-header" onclick="selectJapaneseGroup(${firstCardId})">
                ${nameDisplay}
                <div class="card-stats">
                    📊 使用於 ${group.totalDecks.toLocaleString()} 套牌 | 總計 ${group.totalQuantity.toLocaleString()} 張
                </div>
            </div>
            ${variantsHtml}
        </div>
    `;
    }).join('');
}

// Toggle variants display
function toggleVariants(event, safeId) {
    event.stopPropagation();
    
    // Close all other open variants first
    document.querySelectorAll('.variants-list').forEach(list => {
        if (list.id !== `variants-${safeId}` && list.style.display === 'block') {
            list.style.display = 'none';
            const header = list.previousElementSibling;
            if (header) {
                const icon = header.querySelector('.toggle-icon');
                if (icon) icon.textContent = '▼';
            }
        }
    });
    
    // Toggle current variant
    const variantsList = document.getElementById(`variants-${safeId}`);
    const toggleIcon = event.currentTarget.querySelector('.toggle-icon');
    
    if (variantsList && toggleIcon) {
        if (variantsList.style.display === 'none') {
            variantsList.style.display = 'block';
            toggleIcon.textContent = '▲';
        } else {
            variantsList.style.display = 'none';
            toggleIcon.textContent = '▼';
        }
    }
}

// Select Japanese card group (all variants)
function selectJapaneseGroup(cardId) {
    console.log('selectJapaneseGroup called with cardId:', cardId);
    
    // Find the card to get its name
    const card = unmappedCards.find(c => c.card_id == cardId);
    if (!card) {
        console.error('Card not found with id:', cardId);
        return;
    }
    
    // Find all cards with the same name (entire group)
    selectedJapaneseGroup = unmappedCards.filter(c => c.card_name === card.card_name);
    selectedJapanese = card; // Keep for backwards compatibility
    
    console.log('Selected group:', selectedJapaneseGroup.length, 'variants');
    renderUnmappedCards();
    updatePreview();
}

// Select Japanese card
function selectJapanese(cardId) {
    console.log('selectJapanese called with cardId:', cardId, 'type:', typeof cardId);
    console.log('unmappedCards sample:', unmappedCards.slice(0, 2));
    
    // Convert cardId to number if it's a string
    const numericCardId = typeof cardId === 'string' ? parseInt(cardId, 10) : cardId;
    
    selectedJapanese = unmappedCards.find(c => {
        const match = c.card_id == numericCardId; // Use == for loose comparison
        if (match) {
            console.log('Found match:', c);
        }
        return match;
    });
    
    console.log('Selected card:', selectedJapanese);
    
    if (!selectedJapanese) {
        console.error('Card not found! Looking for card_id:', numericCardId);
        console.log('Available card_ids:', unmappedCards.map(c => c.card_id).slice(0, 10));
        return;
    }
    
    renderUnmappedCards();
    updatePreview();
}

// Handle search key press
function handleSearchKey(event) {
    if (event.key === 'Enter') {
        searchChineseCards();
    }
}

// Search Chinese cards
async function searchChineseCards() {
    const query = document.getElementById('searchInput').value.trim();
    if (!query) {
        showMessage('請輸入搜尋條件', 'error');
        return;
    }
    
    const container = document.getElementById('searchResults');
    container.innerHTML = '<div class="loading">搜尋中</div>';
    
    try {
        const response = await fetch(`${API_BASE}/search?q=${encodeURIComponent(query)}`);
        const data = await response.json();
        
        if (data.cards.length === 0) {
            container.innerHTML = '<div class="empty">未找到符合的卡片</div>';
            return;
        }
        
        container.innerHTML = data.cards.map(card => `
            <div class="card-item ${selectedChinese?.id === card.id ? 'selected' : ''}" 
                 onclick="selectChinese(${card.id}, event)">
                <div class="card-name chinese">${escapeHtml(card.name)}</div>
                <div>
                    ${card.expansion_code ? `<span class="card-code">${escapeHtml(card.expansion_code)} ${escapeHtml(card.collector_number || '')}</span>` : ''}
                    ${card.card_type ? `<span class="card-code">${escapeHtml(card.card_type)}</span>` : ''}
                </div>
                <div class="card-stats">
                    ${card.hp ? `HP: ${card.hp} | ` : ''}
                    ${card.attribute ? `屬性: ${escapeHtml(card.attribute)} | ` : ''}
                    ${card.rarity ? `稀有度: ${escapeHtml(card.rarity)}` : ''}
                </div>
            </div>
        `).join('');
    } catch (error) {
        container.innerHTML = '<div class="empty">搜尋失敗: ' + error.message + '</div>';
    }
}

// Select Chinese card
async function selectChinese(cardId, event) {
    try {
        const response = await fetch(`${API_BASE}/card/${cardId}`);
        selectedChinese = await response.json();
        
        // Highlight selected card
        document.querySelectorAll('#searchResults .card-item').forEach(item => {
            item.classList.remove('selected');
        });
        
        // Add selected class to the clicked element
        if (event && event.currentTarget) {
            event.currentTarget.classList.add('selected');
        } else {
            // Fallback: find the element by iterating through results
            const items = document.querySelectorAll('#searchResults .card-item');
            items.forEach((item, index) => {
                if (item.onclick && item.onclick.toString().includes(cardId)) {
                    item.classList.add('selected');
                }
            });
        }
        
        updatePreview();
    } catch (error) {
        showMessage('載入卡片詳情失敗: ' + error.message, 'error');
    }
}

// Update preview
function updatePreview() {
    const preview = document.getElementById('selectionPreview');
    const btn = document.getElementById('linkButton');
    
    if (selectedJapaneseGroup && selectedChinese) {
        preview.style.display = 'block';
        const groupSize = selectedJapaneseGroup.length;
        const groupName = selectedJapaneseGroup[0].card_name;
        document.getElementById('previewJapanese').textContent = `${groupName} (${groupSize}個版本)`;
        document.getElementById('previewChinese').textContent = selectedChinese.name;
        
        // Set default Chinese name translation if available
        const chineseNameInput = document.getElementById('chineseNameInput');
        if (chineseNameInput && TRANSLATIONS[groupName]) {
            chineseNameInput.value = TRANSLATIONS[groupName];
        }
        
        btn.disabled = false;
        btn.textContent = `✅ 批量連結 ${groupSize} 個版本: ${groupName} → ${selectedChinese.name}`;
    } else {
        preview.style.display = 'none';
        btn.disabled = true;
        btn.textContent = '✅ 建立對應連結';
    }
}

// Link cards
async function linkCards() {
    if (!selectedJapaneseGroup || !selectedChinese) {
        showMessage('請選擇要連結的卡片', 'error');
        return;
    }
    
    try {
        // Get user-input Chinese name if provided
        const chineseNameInput = document.getElementById('chineseNameInput');
        const userChineseName = chineseNameInput ? chineseNameInput.value.trim() : '';
        
        let successCount = 0;
        let failCount = 0;
        
        // Link all variants in the group
        for (const japaneseCard of selectedJapaneseGroup) {
            try {
                // Try to find better match based on expansion code
                let targetCard = selectedChinese;
                
                // Extract expansion code from Japanese card
                if (japaneseCard.card_code) {
                    const codeMatch = japaneseCard.card_code.match(/^([A-Za-z0-9]+)/);
                    if (codeMatch) {
                        const japaneseExpCode = codeMatch[1];
                        
                        // Search for card with same name in same expansion
                        const searchResponse = await fetch(`${API_BASE}/search?q=${encodeURIComponent(selectedChinese.name)}`);
                        const searchData = await searchResponse.json();
                        
                        // Find card in same expansion
                        const sameExpansionCard = searchData.cards.find(c => 
                            c.expansion_code === japaneseExpCode && c.name === selectedChinese.name
                        );
                        
                        if (sameExpansionCard) {
                            console.log(`Found better match for ${japaneseCard.card_code}: ${sameExpansionCard.expansion_code} ${sameExpansionCard.collector_number}`);
                            targetCard = sameExpansionCard;
                        }
                    }
                }
                
                const response = await fetch(`${API_BASE}/link`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        event_card_id: japaneseCard.card_id,
                        event_card_name: japaneseCard.card_name,
                        event_card_code: japaneseCard.card_code || '',
                        main_card_id: targetCard.id,
                        main_card_name: targetCard.name,
                        main_expansion_code: targetCard.expansion_code || '',
                        main_collector_number: targetCard.collector_number || '',
                        user_chinese_name: userChineseName
                    })
                });
                
                const data = await response.json();
                if (data.success) {
                    successCount++;
                } else {
                    failCount++;
                    console.error('Link failed for card:', japaneseCard.card_id, data.error);
                }
            } catch (error) {
                failCount++;
                console.error('Link error for card:', japaneseCard.card_id, error);
            }
        }
        
        
        // Show results
        if (successCount > 0) {
            const groupName = selectedJapaneseGroup[0].card_name;
            showMessage(`✅ 成功連結 ${successCount}/${selectedJapaneseGroup.length} 個版本: ${groupName} → ${selectedChinese.name}`, 'success');
            
            // Update statistics
            loadStatistics();
            
            // Remove successfully linked cards from unmapped list
            const linkedIds = selectedJapaneseGroup.map(c => c.card_id);
            unmappedCards = unmappedCards.filter(c => !linkedIds.includes(c.card_id));
            
            // Clear selection and refresh
            clearSelection();
            renderUnmappedCards();
        }
        
        if (failCount > 0) {
            showMessage(`⚠️ ${failCount} 個連結失敗`, 'error');
        }
    } catch (error) {
        showMessage('連結失敗: ' + error.message, 'error');
    }
}

// Clear selection
function clearSelection() {
    selectedJapanese = null;
    selectedJapaneseGroup = null;
    selectedChinese = null;
    renderUnmappedCards();
    
    document.querySelectorAll('#searchResults .card-item').forEach(item => {
        item.classList.remove('selected');
    });
    
    document.getElementById('searchInput').value = '';
    updatePreview();
}

// Show message
function showMessage(text, type) {
    const msgDiv = document.getElementById('message');
    msgDiv.innerHTML = `<div class="message ${type}">${escapeHtml(text)}</div>`;
    setTimeout(() => {
        msgDiv.innerHTML = '';
    }, 5000);
}

// Escape HTML
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Create safe ID for DOM elements
function createSafeId(text) {
    return 'card-' + text.replace(/[^a-zA-Z0-9]/g, '-');
}
