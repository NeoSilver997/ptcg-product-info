const API_BASE = 'http://localhost:3000/api';

let currentDate = new Date();
let selectedDate = null;
let eventsData = {};

// Initialize
document.addEventListener('DOMContentLoaded', async () => {
    await loadEventStatistics();
    renderCalendar();
    bindCalendarNavigation();
});

// Load event statistics
async function loadEventStatistics() {
    try {
        const response = await fetch(`${API_BASE}/calendar/stats`);
        const data = await response.json();
        
        document.getElementById('totalEvents').textContent = `📊 總賽事: ${data.totalEvents}`;
        document.getElementById('totalDecks').textContent = `🎴 總牌組: ${data.totalDecks}`;
    } catch (error) {
        console.error('Failed to load statistics:', error);
    }
}

// Render calendar
async function renderCalendar() {
    const year = currentDate.getFullYear();
    const month = currentDate.getMonth();
    
    // Update month display
    const monthNames = ['一月', '二月', '三月', '四月', '五月', '六月', 
                        '七月', '八月', '九月', '十月', '十一月', '十二月'];
    document.getElementById('currentMonth').textContent = `${year}年 ${monthNames[month]}`;
    
    // Get events for this month
    const startDate = new Date(year, month, 1);
    const endDate = new Date(year, month + 1, 0);
    
    try {
        const response = await fetch(
            `${API_BASE}/calendar/events?start=${formatDate(startDate)}&end=${formatDate(endDate)}`
        );
        const data = await response.json();
        eventsData = data.eventsByDate;
    } catch (error) {
        console.error('Failed to load events:', error);
        eventsData = {};
    }
    
    // Calculate calendar grid
    const firstDay = startDate.getDay(); // 0 = Sunday
    const daysInMonth = endDate.getDate();
    const prevMonthDays = new Date(year, month, 0).getDate();
    
    const calendarGrid = document.getElementById('calendarGrid');
    calendarGrid.innerHTML = '';
    
    // Add day headers
    const dayHeaders = ['日', '一', '二', '三', '四', '五', '六'];
    dayHeaders.forEach(day => {
        const header = document.createElement('div');
        header.className = 'day-header';
        header.textContent = day;
        header.style.textAlign = 'center';
        header.style.fontWeight = 'bold';
        header.style.padding = '10px';
        header.style.color = '#667eea';
        calendarGrid.appendChild(header);
    });
    
    // Previous month days
    for (let i = firstDay - 1; i >= 0; i--) {
        const day = prevMonthDays - i;
        const dayElement = createDayElement(day, true);
        calendarGrid.appendChild(dayElement);
    }
    
    // Current month days
    for (let day = 1; day <= daysInMonth; day++) {
        const date = new Date(year, month, day);
        const dateStr = formatDate(date);
        const eventCount = eventsData[dateStr] ? eventsData[dateStr].length : 0;
        
        const dayElement = createDayElement(day, false, eventCount, date);
        calendarGrid.appendChild(dayElement);
    }
    
    // Next month days
    const remainingDays = 42 - (firstDay + daysInMonth); // 6 rows * 7 days
    for (let day = 1; day <= remainingDays; day++) {
        const dayElement = createDayElement(day, true);
        calendarGrid.appendChild(dayElement);
    }
}

// Create day element
function createDayElement(day, isOtherMonth, eventCount = 0, date = null) {
    const dayDiv = document.createElement('div');
    dayDiv.className = 'calendar-day';
    
    if (isOtherMonth) {
        dayDiv.classList.add('other-month');
    }
    
    if (eventCount > 0) {
        dayDiv.classList.add('has-events');
    }
    
    const dayNumber = document.createElement('div');
    dayNumber.className = 'day-number';
    dayNumber.textContent = day;
    dayDiv.appendChild(dayNumber);
    
    if (eventCount > 0) {
        const eventBadge = document.createElement('div');
        eventBadge.className = 'event-count';
        eventBadge.textContent = `${eventCount}`;
        dayDiv.appendChild(eventBadge);
    }
    
    if (date && !isOtherMonth) {
        dayDiv.onclick = () => selectDate(date, dayDiv);
    }
    
    return dayDiv;
}

// Select date
async function selectDate(date, element) {
    selectedDate = date;
    
    // Update selection styling
    document.querySelectorAll('.calendar-day').forEach(day => {
        day.classList.remove('selected');
    });
    element.classList.add('selected');
    
    // Load events for this date
    const dateStr = formatDate(date);
    const events = eventsData[dateStr] || [];
    
    const eventsList = document.getElementById('eventsList');
    const deckEventsList = document.getElementById('deckEventsList');
    
    if (events.length === 0) {
        eventsList.innerHTML = '<div class="no-data">📭 這天沒有賽事</div>';
        deckEventsList.innerHTML = '<div class="no-data">📭 這天沒有賽事</div>';
        return;
    }
    
    eventsList.innerHTML = '<div class="loading">載入賽事...</div>';
    deckEventsList.innerHTML = '<div class="loading">載入賽事...</div>';
    
    try {
        const response = await fetch(`${API_BASE}/calendar/events/${dateStr}`);
        const data = await response.json();
        
        eventsList.innerHTML = '';
        deckEventsList.innerHTML = '';
        data.events.forEach(event => {
            const eventCard = createEventCard(event);
            const deckEventCard = createEventCard(event);
            eventsList.appendChild(eventCard);
            deckEventsList.appendChild(deckEventCard);
        });

        // Auto-load first deck if available
        const firstEventWithDecks = data.events.find(event => event.top_decks && event.top_decks.length > 0);
        if (firstEventWithDecks && firstEventWithDecks.top_decks.length > 0) {
            loadDeckDetails(firstEventWithDecks.top_decks[0].deck_id);
        }
    } catch (error) {
        console.error('Failed to load event details:', error);
        eventsList.innerHTML = '<div class="no-data">❌ 載入失敗</div>';
        deckEventsList.innerHTML = '<div class="no-data">❌ 載入失敗</div>';
    }
}

// Create event card
function createEventCard(event) {
    const card = document.createElement('div');
    card.className = 'event-card';
    
    const title = document.createElement('div');
    title.className = 'event-title';
    title.textContent = event.event_title || `賽事 #${event.event_id}`;
    card.appendChild(title);
    
    if (event.event_location) {
        const location = document.createElement('div');
        location.className = 'event-meta';
        location.textContent = `📍 ${event.event_location}`;
        card.appendChild(location);
    }
    
    const deckCount = document.createElement('div');
    deckCount.className = 'event-meta';
    deckCount.textContent = `🎴 ${event.deck_count} 個牌組`;
    card.appendChild(deckCount);
    
    if (event.top_decks && event.top_decks.length > 0) {
        const deckPreview = document.createElement('div');
        deckPreview.className = 'deck-preview';
        
        event.top_decks.slice(0, 8).forEach(deck => {
            const deckItem = document.createElement('div');
            deckItem.className = 'deck-item';
            deckItem.textContent = `${deck.rank} - ${deck.key_card || deck.deck_id}`;
            deckItem.style.cursor = 'pointer';
            deckItem.style.color = '#2d3436';
            deckItem.onclick = () => {
                loadDeckDetails(deck.deck_id);
            };
            deckPreview.appendChild(deckItem);
        });
        
        card.appendChild(deckPreview);
    }
    
    return card;
}

let currentDeckData = null;

// Load deck details
async function loadDeckDetails(deckId) {
    const deckSection = document.getElementById('deckDetailsSection');
    const deckInfo = document.getElementById('deckInfo');
    const deckCards = document.getElementById('deckCards');
    
    deckSection.style.display = 'block';
    deckInfo.innerHTML = '<div class="loading">載入牌組...</div>';
    deckCards.innerHTML = '';
    
    try {
        const response = await fetch(`${API_BASE}/calendar/deck/${deckId}`);
        const data = await response.json();
        
        currentDeckData = data; // Store for sorting
        
        renderDeckDetails(data);
        
    } catch (error) {
        console.error('Failed to load deck details:', error);
        deckInfo.innerHTML = '<div class="no-data">❌ 載入失敗</div>';
    }
}

// Render deck details
function renderDeckDetails(data) {
    const deckInfo = document.getElementById('deckInfo');
    const deckCards = document.getElementById('deckCards');
    
    // Deck info in 2 rows
    const totalCards = data.deck.total_cards || data.cards.reduce((sum, c) => sum + c.quantity, 0);
    const isStandard = totalCards === 60;
    
    deckInfo.innerHTML = `
        <div class="deck-info-row">
            <div><strong>🏆 名次:</strong> ${data.deck.rank || 'N/A'}</div>
            <div><strong>📅 賽事日期:</strong> ${data.deck.event_date || 'N/A'}</div>
            <div><strong>🃏 不重複卡片:</strong> ${data.cards.length}種</div>
        </div>
        <div class="deck-info-row">
            <div style="display: flex; align-items: center; gap: 10px;">
                <strong>🎴 總卡片數量:</strong> 
                <span style="font-size: 1.2em; font-weight: bold; color: ${isStandard ? '#00b894' : '#d63031'};">
                    ${totalCards}
                </span>
                ${!isStandard ? '<span style="color: #d63031; font-size: 0.9em;">(⚠️ 非標準60張)</span>' : '<span style="color: #00b894;">✓</span>'}
            </div>
            ${data.deck.deck_url ? `<div><a href="${data.deck.deck_url}" target="_blank" style="color: #667eea; text-decoration: none;">🔗 查看原始牌組</a></div>` : '<div></div>'}
        </div>
    `;
    
    // Group cards by type
    const cardsByType = {};
    data.cards.forEach(card => {
        const type = card.card_type || '其他';
        if (!cardsByType[type]) cardsByType[type] = [];
        cardsByType[type].push(card);
    });
    
    // Render cards by type
    const typeOrder = ['寶可夢', '支援者', '物品卡', '競技場', '基本能量', '特殊能量', '其他'];
    typeOrder.forEach(type => {
        if (!cardsByType[type] || cardsByType[type].length === 0) return;
        
        const typeSection = document.createElement('div');
        typeSection.style.marginBottom = '20px';
        
        // Calculate total cards for this type
        const totalInType = cardsByType[type].reduce((sum, c) => sum + c.quantity, 0);
        
        const typeHeader = document.createElement('h4');
        typeHeader.textContent = `${getTypeIcon(type)} ${type} (${cardsByType[type].length}種 / ${totalInType}張)`;
        typeHeader.style.color = '#667eea';
        typeHeader.style.marginBottom = '10px';
        typeSection.appendChild(typeHeader);
        
        cardsByType[type].forEach(card => {
            const cardEntry = createCardEntry(card);
            typeSection.appendChild(cardEntry);
        });
        
        deckCards.appendChild(typeSection);
    });
}

// Filter deck cards
function filterDeckCards() {
    if (!currentDeckData) return;
    
    const searchTerm = document.getElementById('cardSearch').value.toLowerCase();
    const cardEntries = document.querySelectorAll('.card-entry');
    
    cardEntries.forEach(entry => {
        const cardName = entry.querySelector('.card-name')?.textContent.toLowerCase() || '';
        const cardNameJp = entry.querySelector('.card-name-jp')?.textContent.toLowerCase() || '';
        const cardMeta = entry.querySelector('.card-meta')?.textContent.toLowerCase() || '';
        
        const matches = cardName.includes(searchTerm) || 
                       cardNameJp.includes(searchTerm) || 
                       cardMeta.includes(searchTerm);
        
        entry.style.display = matches ? 'flex' : 'none';
    });
}

// Sort deck cards
function sortDeckCards() {
    if (!currentDeckData) return;
    
    const sortBy = document.getElementById('sortSelect').value;
    
    // Reset search when sorting
    document.getElementById('cardSearch').value = '';
    
    // Sort the cards array
    const sortedCards = [...currentDeckData.cards];
    
    switch (sortBy) {
        case 'name':
            sortedCards.sort((a, b) => (a.chinese_name || a.card_name).localeCompare(b.chinese_name || b.card_name));
            break;
        case 'quantity':
            sortedCards.sort((a, b) => b.quantity - a.quantity);
            break;
        case 'rarity':
            const rarityOrder = { 'C': 1, 'R': 2, 'U': 3, 'S': 4, 'SR': 5, 'AR': 6, 'RR': 7, 'MUR': 8, 'BWR': 9, 'ACE': 10, 'SSR': 11, 'UR': 12, 'SAR': 13 };
            sortedCards.sort((a, b) => (rarityOrder[b.rarity] || 0) - (rarityOrder[a.rarity] || 0));
            break;
        case 'type':
        default:
            // Default sorting by type is already handled in renderDeckDetails
            renderDeckDetails(currentDeckData);
            return;
    }
    
    // Update the data with sorted cards
    const sortedData = { ...currentDeckData, cards: sortedCards };
    
    // Re-render with sorted cards
    renderSortedDeck(sortedData);
}

// Render sorted deck (single section)
function renderSortedDeck(data) {
    const deckCards = document.getElementById('deckCards');
    deckCards.innerHTML = '';
    
    const typeSection = document.createElement('div');
    typeSection.style.marginBottom = '20px';
    
    const totalCards = data.cards.reduce((sum, c) => sum + c.quantity, 0);
    const typeHeader = document.createElement('h4');
    typeHeader.textContent = `🎴 所有卡片 (${data.cards.length}種 / ${totalCards}張)`;
    typeHeader.style.color = '#667eea';
    typeHeader.style.marginBottom = '10px';
    typeSection.appendChild(typeHeader);
    
    data.cards.forEach(card => {
        const cardEntry = createCardEntry(card);
        typeSection.appendChild(cardEntry);
    });
    
    deckCards.appendChild(typeSection);
}

// Create card entry
function createCardEntry(card) {
    const entry = document.createElement('div');
    entry.className = 'card-entry';
    
    // Card image
    const imageDiv = document.createElement('div');
    if (card.image_url) {
        const img = document.createElement('img');
        img.className = 'card-image';
        img.src = card.image_url;
        img.alt = card.chinese_name || card.card_name;
        img.style.cursor = 'pointer';
        img.onclick = () => window.open(card.image_url, '_blank');
        img.onerror = () => {
            img.style.display = 'none';
            const placeholder = document.createElement('div');
            placeholder.className = 'card-image no-image';
            placeholder.textContent = '無圖片';
            placeholder.style.cursor = 'default';
            imageDiv.innerHTML = '';
            imageDiv.appendChild(placeholder);
        };
        imageDiv.appendChild(img);
    } else {
        const placeholder = document.createElement('div');
        placeholder.className = 'card-image no-image';
        placeholder.textContent = '無圖片';
        placeholder.style.cursor = 'default';
        imageDiv.appendChild(placeholder);
    }
    entry.appendChild(imageDiv);
    
    // Card info
    const info = document.createElement('div');
    info.className = 'card-info';
    
    const chineseName = document.createElement('div');
    chineseName.className = 'card-name';
    chineseName.textContent = card.chinese_name || '⚠️ 未對應中文名';
    chineseName.style.color = card.chinese_name ? '#2d3436' : '#d63031';
    info.appendChild(chineseName);
    
    const japaneseName = document.createElement('div');
    japaneseName.className = 'card-name-jp';
    japaneseName.textContent = `${getTypeIcon(card.card_type || '其他')} ${card.card_name}`;
    info.appendChild(japaneseName);
    
    const meta = document.createElement('div');
    meta.className = 'card-meta';
    meta.textContent = card.card_code || '無代碼';
    
    // Add rarity badge if available
    if (card.rarity) {
        const rarityBadge = document.createElement('span');
        rarityBadge.className = `card-rarity ${card.rarity}`;
        rarityBadge.textContent = card.rarity;
        meta.appendChild(rarityBadge);
    }
    
    info.appendChild(meta);
    
    entry.appendChild(info);
    
    // Quantity
    const quantity = document.createElement('div');
    quantity.className = 'card-quantity';
    quantity.textContent = `×${card.quantity}`;
    entry.appendChild(quantity);
    
    return entry;
}

// Close deck details
function closeDeckDetails() {
    document.getElementById('deckDetailsSection').style.display = 'none';
}

// Navigation
function previousMonth() {
    currentDate.setMonth(currentDate.getMonth() - 1);
    renderCalendar();
}

function nextMonth() {
    currentDate.setMonth(currentDate.getMonth() + 1);
    renderCalendar();
}

function bindCalendarNavigation() {
    window.previousMonth = previousMonth;
    window.nextMonth = nextMonth;
    window.closeDeckDetails = closeDeckDetails;
}

// Helper functions
function formatDate(date) {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
}

function getTypeIcon(type) {
    const icons = {
        '寶可夢': '⚡',
        '支援者': '👤',
        '物品卡': '🎒',
        '競技場': '🏟️',
        '基本能量': '💎',
        '特殊能量': '✨',
        '其他': '📦'
    };
    return icons[type] || '📋';
}
