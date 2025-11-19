const express = require('express');
const fs = require('fs');
const sqlite3 = require('sqlite3').verbose();
const cors = require('cors');
const path = require('path');

const app = express();
const PORT = 3000;

// Database paths
const EVENT_DB = path.join(__dirname, '..', 'ptcg_events.db');
const MAIN_DB = path.join(__dirname, '..', '..', 'PokemonDBByjules', 'PTCG_CardDB_Tc', 'pokemon_cards.db');

let eventDb, mainDb;

// Initialize databases
async function initDatabases() {
    return new Promise((resolve, reject) => {
        eventDb = new sqlite3.Database(EVENT_DB, (err) => {
            if (err) {
                console.error('Failed to open event database:', err.message);
                reject(err);
                return;
            }

            mainDb = new sqlite3.Database(MAIN_DB, (err) => {
                if (err) {
                    console.error('Failed to open main database:', err.message);
                    reject(err);
                    return;
                }

                console.log('✅ 資料庫載入成功');
                resolve();
            });
        });
    });
}// Save event database
function saveEventDb() {
    // SQLite3 automatically saves changes, no need to export/import
}

// Middleware
app.use(cors());
app.use(express.json());
app.use(express.static('public'));

// API: Get unmapped cards
app.get('/api/unmapped', (req, res) => {
    const query = `
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
    `;

    eventDb.all(query, [], (err, rows) => {
        if (err) {
            res.status(500).json({ error: err.message });
            return;
        }

        const countQuery = `
            SELECT COUNT(DISTINCT dc.card_id) as count
            FROM deck_cards dc
            LEFT JOIN card_mappings cm ON dc.card_id = cm.event_card_id
            WHERE cm.event_card_id IS NULL
        `;

        eventDb.get(countQuery, [], (err, countRow) => {
            if (err) {
                res.status(500).json({ error: err.message });
                return;
            }

            const cards = rows.map(row => ({
                card_id: row.card_id,
                card_name: row.card_name,
                card_code: row.card_code,
                deck_count: row.deck_count,
                total_quantity: row.total_quantity
            }));

            const total = countRow ? countRow.count : 0;
            res.json({ cards, total });
        });
    });
});

// API: Search Chinese cards
app.get('/api/search', (req, res) => {
    const query = req.query.q || '';

    if (!query) {
        return res.json({ cards: [] });
    }

    // Escape single quotes for SQL
    const safeQuery = query.replace(/'/g, "''");

    const searchQuery = `
        SELECT DISTINCT
            c.id,
            c.name,
            c.card_type,
            c.hp,
            c.attribute,
            c.collector_number,
            c.rarity,
            c.evolution_stage,
            e.code as expansion_code,
            e.name as expansion_name
        FROM cards c
        LEFT JOIN expansions e ON c.expansion_id = e.id
        WHERE c.name LIKE '%${safeQuery}%'
            OR e.code LIKE '%${safeQuery}%'
            OR c.collector_number LIKE '%${safeQuery}%'
        ORDER BY c.name
        LIMIT 50
    `;

    mainDb.all(searchQuery, [], (err, rows) => {
        if (err) {
            console.error('Search error:', err);
            res.status(500).json({ error: err.message, cards: [] });
            return;
        }

        const cards = rows.map(row => ({
            id: row.id,
            name: row.name,
            card_type: row.card_type,
            hp: row.hp,
            attribute: row.attribute,
            collector_number: row.collector_number,
            rarity: row.rarity,
            evolution_stage: row.evolution_stage,
            expansion_code: row.expansion_code,
            expansion_name: row.expansion_name
        }));

        res.json({ cards });
    });
});

// API: Get card details
app.get('/api/card/:id', (req, res) => {
    const cardId = parseInt(req.params.id);

    const query = `
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
    `;

    mainDb.get(query, [cardId], (err, row) => {
        if (err) {
            res.status(500).json({ error: err.message });
            return;
        }

        const card = row ? {
            id: row.id,
            name: row.name,
            card_type: row.card_type,
            hp: row.hp,
            attribute: row.attribute,
            collector_number: row.collector_number,
            rarity: row.rarity,
            evolution_stage: row.evolution_stage,
            expansion_code: row.expansion_code,
            expansion_name: row.expansion_name,
            illustrator: row.illustrator
        } : {};

        res.json(card);
    });
});

// API: Create manual link
app.post('/api/link', (req, res) => {
    let {
        event_card_id,
        event_card_name,
        event_card_code,
        main_card_id,
        main_card_name,
        main_expansion_code,
        main_collector_number,
        user_chinese_name
    } = req.body;

    // Smart fallback: verify card exists in expansion with collector number
    if (main_expansion_code && main_collector_number) {
        const verifyQuery = `
            SELECT c.id, c.name, c.collector_number, e.code as expansion_code
            FROM cards c
            JOIN expansions e ON c.expansion_id = e.id
            WHERE c.id = ?
            AND e.code = ?
            AND c.collector_number = ?
        `;

        mainDb.get(verifyQuery, [main_card_id, main_expansion_code, main_collector_number], (err, row) => {
            if (err) {
                console.error('Verification error:', err);
                res.status(500).json({ success: false, error: err.message });
                return;
            }

            // If card not found with that collector number, try to find same name in same expansion
            if (!row) {
                console.log(`Card ID ${main_card_id} not found with collector ${main_collector_number} in expansion ${main_expansion_code}`);
                console.log(`Searching for alternative card with name "${main_card_name}" in expansion ${main_expansion_code}...`);

                const fallbackQuery = `
                    SELECT c.id, c.name, c.collector_number, e.code as expansion_code
                    FROM cards c
                    JOIN expansions e ON c.expansion_id = e.id
                    WHERE c.name = ?
                    AND e.code = ?
                    LIMIT 1
                `;

                mainDb.get(fallbackQuery, [main_card_name, main_expansion_code], (err, fallbackRow) => {
                    if (err) {
                        console.error('Fallback error:', err);
                        res.status(500).json({ success: false, error: err.message });
                        return;
                    }

                    if (fallbackRow) {
                        const oldId = main_card_id;
                        const oldCollector = main_collector_number;

                        main_card_id = fallbackRow.id;
                        main_collector_number = fallbackRow.collector_number;

                        console.log(`✓ Found fallback card: ID ${main_card_id}, collector ${main_collector_number}`);
                        console.log(`  (Original: ID ${oldId}, collector ${oldCollector})`);
                    } else {
                        console.log(`✗ No fallback card found for "${main_card_name}" in expansion ${main_expansion_code}`);
                    }

                    insertMapping();
                });
            } else {
                console.log(`✓ Card verified: ID ${main_card_id}, ${main_expansion_code} ${main_collector_number}`);
                insertMapping();
            }
        });
    } else {
        insertMapping();
    }

    function insertMapping() {
        // Escape single quotes
        const safeName = (event_card_name || '').replace(/'/g, "''");
        const safeCode = (event_card_code || '').replace(/'/g, "''");
        const safeMainName = (main_card_name || '').replace(/'/g, "''");
        const safeExpCode = (main_expansion_code || '').replace(/'/g, "''");
        const safeCollNum = (main_collector_number || '').replace(/'/g, "''");
        const safeUserName = (user_chinese_name || '').replace(/'/g, "''");

        const insertQuery = `
            INSERT OR REPLACE INTO card_mappings
            (event_card_id, event_card_name, event_card_code,
             main_card_id, main_card_name, main_expansion_code,
             main_collector_number, match_type, match_confidence)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'manual_link', 1.0)
        `;

        eventDb.run(insertQuery, [event_card_id, safeName, safeCode, main_card_id, safeMainName, safeExpCode, safeCollNum], function(err) {
            if (err) {
                console.error('Insert error:', err);
                res.status(500).json({ success: false, error: err.message });
                return;
            }

            // Save user's Chinese translation if provided
            if (user_chinese_name && user_chinese_name.trim()) {
                // Create table if not exists
                eventDb.run(`
                    CREATE TABLE IF NOT EXISTS user_translations (
                        japanese_name TEXT PRIMARY KEY,
                        chinese_name TEXT NOT NULL,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                `, [], (err) => {
                    if (err) {
                        console.error('Create table error:', err);
                        res.status(500).json({ success: false, error: err.message });
                        return;
                    }

                    eventDb.run(`
                        INSERT OR REPLACE INTO user_translations (japanese_name, chinese_name, updated_at)
                        VALUES (?, ?, CURRENT_TIMESTAMP)
                    `, [safeName, safeUserName], (err) => {
                        if (err) {
                            console.error('Translation insert error:', err);
                            res.status(500).json({ success: false, error: err.message });
                            return;
                        }

                        res.json({ success: true });
                    });
                });
            } else {
                res.json({ success: true });
            }
        });
    }
});

// API: Remove link
app.post('/api/unlink', (req, res) => {
    const { event_card_id } = req.body;

    const query = `
        DELETE FROM card_mappings
        WHERE event_card_id = ?
    `;

    eventDb.run(query, [event_card_id], function(err) {
        if (err) {
            res.status(500).json({ success: false, error: err.message });
            return;
        }

        res.json({ success: true });
    });
});

// API: Get statistics
app.get('/api/stats', (req, res) => {
    const totalQuery = 'SELECT COUNT(DISTINCT card_id) as count FROM deck_cards';
    const mappedQuery = 'SELECT COUNT(DISTINCT event_card_id) as count FROM card_mappings';
    const manualQuery = 'SELECT COUNT(*) as count FROM card_mappings WHERE match_type = \'manual_link\'';

    eventDb.get(totalQuery, [], (err, totalRow) => {
        if (err) {
            res.status(500).json({ error: err.message });
            return;
        }

        eventDb.get(mappedQuery, [], (err, mappedRow) => {
            if (err) {
                res.status(500).json({ error: err.message });
                return;
            }

            eventDb.get(manualQuery, [], (err, manualRow) => {
                if (err) {
                    res.status(500).json({ error: err.message });
                    return;
                }

                const totalCards = totalRow ? totalRow.count : 0;
                const mappedCards = mappedRow ? mappedRow.count : 0;
                const manualLinks = manualRow ? manualRow.count : 0;

                res.json({
                    total: totalCards,
                    mapped: mappedCards,
                    unmapped: totalCards - mappedCards,
                    manual: manualLinks,
                    coverage: totalCards > 0 ? ((mappedCards / totalCards) * 100).toFixed(1) : '0.0'
                });
            });
        });
    });
});

// Calendar API: Get statistics
app.get('/api/calendar/stats', (req, res) => {
    const eventQuery = 'SELECT COUNT(*) as count FROM events';
    const deckQuery = 'SELECT COUNT(*) as count FROM decks';

    eventDb.get(eventQuery, [], (err, eventRow) => {
        if (err) {
            res.status(500).json({ error: err.message });
            return;
        }

        eventDb.get(deckQuery, [], (err, deckRow) => {
            if (err) {
                res.status(500).json({ error: err.message });
                return;
            }

            const totalEvents = eventRow ? eventRow.count : 0;
            const totalDecks = deckRow ? deckRow.count : 0;

            res.json({ totalEvents, totalDecks });
        });
    });
});

// Calendar API: Get events by date range
app.get('/api/calendar/events', (req, res) => {
    const { start, end } = req.query;

    const query = `
        SELECT event_id, event_date, event_title, event_location,
               (SELECT COUNT(*) FROM decks WHERE decks.event_id = events.event_id) as deck_count
        FROM events
        WHERE event_date BETWEEN ? AND ?
        ORDER BY event_date
    `;

    eventDb.all(query, [start, end], (err, rows) => {
        if (err) {
            res.status(500).json({ error: err.message });
            return;
        }

        const eventsByDate = {};

        rows.forEach(row => {
            const event_date = row.event_date;

            if (!eventsByDate[event_date]) {
                eventsByDate[event_date] = [];
            }

            eventsByDate[event_date].push({
                event_id: row.event_id,
                event_date: row.event_date,
                event_title: row.event_title,
                event_location: row.event_location,
                deck_count: row.deck_count
            });
        });

        res.json({ eventsByDate });
    });
});

// Calendar API: Get events for specific date
app.get('/api/calendar/events/:date', (req, res) => {
    const { date } = req.params;

    const eventQuery = `
        SELECT e.event_id, e.event_date, e.event_title, e.event_location, e.event_url,
               COUNT(d.deck_id) as deck_count
        FROM events e
        LEFT JOIN decks d ON e.event_id = d.event_id
        WHERE e.event_date = ?
        GROUP BY e.event_id
    `;

    eventDb.all(eventQuery, [date], (err, eventRows) => {
        if (err) {
            res.status(500).json({ error: err.message });
            return;
        }

        const events = [];
        let processedEvents = 0;

        if (eventRows.length === 0) {
            return res.json({ events: [] });
        }

        eventRows.forEach(eventRow => {
            const event_id = eventRow.event_id;

            // Get top decks for this event
            const deckQuery = `
                SELECT d.deck_id, d.rank,
                       COALESCE(
                           (SELECT dc.card_name
                            FROM deck_cards dc
                            LEFT JOIN card_mappings cm ON dc.card_id = cm.event_card_id
                            WHERE dc.deck_id = d.deck_id
                            AND dc.card_name NOT LIKE '%エネルギー%'
                            AND dc.card_name NOT LIKE '%Energy%'
                            AND cm.main_card_name IS NOT NULL
                            ORDER BY dc.quantity DESC LIMIT 1),
                           (SELECT dc.card_name
                            FROM deck_cards dc
                            WHERE dc.deck_id = d.deck_id
                            AND dc.card_name NOT LIKE '%エネルギー%'
                            AND dc.card_name NOT LIKE '%Energy%'
                            ORDER BY dc.quantity DESC LIMIT 1),
                           (SELECT dc.card_name FROM deck_cards dc WHERE dc.deck_id = d.deck_id ORDER BY dc.quantity DESC LIMIT 1)
                       ) as key_card,
                       COALESCE(
                           (SELECT cm.main_card_id
                            FROM deck_cards dc
                            LEFT JOIN card_mappings cm ON dc.card_id = cm.event_card_id
                            WHERE dc.deck_id = d.deck_id
                            AND dc.card_name NOT LIKE '%エネルギー%'
                            AND dc.card_name NOT LIKE '%Energy%'
                            AND cm.main_card_name IS NOT NULL
                            ORDER BY dc.quantity DESC LIMIT 1),
                           (SELECT cm.main_card_id
                            FROM deck_cards dc
                            LEFT JOIN card_mappings cm ON dc.card_id = cm.event_card_id
                            WHERE dc.deck_id = d.deck_id
                            ORDER BY dc.quantity DESC LIMIT 1)
                       ) as main_card_id
                FROM decks d
                WHERE event_id = ?
                ORDER BY rank
                LIMIT 8
            `;

            eventDb.all(deckQuery, [event_id], (err, deckRows) => {
                if (err) {
                    console.error('Deck query error:', err);
                    return;
                }

                const top_decks = [];

                // Process decks and get images
                let processedDecks = 0;

                if (deckRows.length === 0) {
                    // No decks for this event
                    events.push({
                        event_id: eventRow.event_id,
                        event_date: eventRow.event_date,
                        event_title: eventRow.event_title,
                        event_location: eventRow.event_location,
                        event_url: eventRow.event_url,
                        deck_count: eventRow.deck_count,
                        top_decks: []
                    });
                    checkComplete();
                    return;
                }

                deckRows.forEach(deckRow => {
                    const main_card_id = deckRow.main_card_id;

                    if (main_card_id) {
                        // Get image URL
                        const imageQuery = 'SELECT c.image_url FROM cards c WHERE c.id = ?';

                        mainDb.get(imageQuery, [main_card_id], (err, imageRow) => {
                            let key_card_image = null;

                            if (!err && imageRow && imageRow.image_url) {
                                const image_url = imageRow.image_url;
                                if (image_url && image_url.startsWith('https://')) {
                                    key_card_image = `/cards/${image_url.split('/').pop()}`;
                                } else {
                                    key_card_image = image_url;
                                }
                            }

                            top_decks.push({
                                deck_id: deckRow.deck_id,
                                rank: deckRow.rank,
                                key_card: deckRow.key_card,
                                key_card_image
                            });

                            processedDecks++;
                            if (processedDecks === deckRows.length) {
                                finishEvent();
                            }
                        });
                    } else {
                        top_decks.push({
                            deck_id: deckRow.deck_id,
                            rank: deckRow.rank,
                            key_card: deckRow.key_card,
                            key_card_image: null
                        });

                        processedDecks++;
                        if (processedDecks === deckRows.length) {
                            finishEvent();
                        }
                    }
                });

                function finishEvent() {
                    events.push({
                        event_id: eventRow.event_id,
                        event_date: eventRow.event_date,
                        event_title: eventRow.event_title,
                        event_location: eventRow.event_location,
                        event_url: eventRow.event_url,
                        deck_count: eventRow.deck_count,
                        top_decks
                    });
                    checkComplete();
                }
            });
        });

        function checkComplete() {
            processedEvents++;
            if (processedEvents === eventRows.length) {
                res.json({ events });
            }
        }
    });
});

// Calendar API: Get deck details with cards
app.get('/api/calendar/deck/:deckId', (req, res) => {
    const { deckId } = req.params;

    // Get deck info with total card count
    const deckQuery = `
        SELECT d.deck_id, d.rank, d.deck_url, e.event_date,
               (SELECT SUM(quantity) FROM deck_cards WHERE deck_id = d.deck_id) as total_cards
        FROM decks d
        LEFT JOIN events e ON d.event_id = e.event_id
        WHERE d.deck_id = ?
    `;

    eventDb.get(deckQuery, [deckId], (err, deckRow) => {
        if (err) {
            res.status(500).json({ error: err.message });
            return;
        }

        if (!deckRow) {
            return res.status(404).json({ error: 'Deck not found' });
        }

        // Get cards with Chinese names and images
        const cardQuery = `
            SELECT
                dc.card_name,
                dc.card_code,
                dc.quantity,
                cm.main_card_name as chinese_name,
                cm.main_card_id
            FROM deck_cards dc
            LEFT JOIN card_mappings cm ON dc.card_id = cm.event_card_id
            WHERE dc.deck_id = ?
            ORDER BY dc.card_name
        `;

        eventDb.all(cardQuery, [deckId], (err, cardRows) => {
            if (err) {
                res.status(500).json({ error: err.message });
                return;
            }

            const cards = [];
            let processedCards = 0;

            if (cardRows.length === 0) {
                return res.json({
                    deck: {
                        deck_id: deckRow.deck_id,
                        rank: deckRow.rank,
                        deck_url: deckRow.deck_url,
                        event_date: deckRow.event_date,
                        total_cards: deckRow.total_cards
                    },
                    cards: []
                });
            }

            cardRows.forEach(cardRow => {
                const main_card_id = cardRow.main_card_id;

                let card_type = null;
                let image_url = null;

                if (main_card_id) {
                    // Get card details from main database
                    const mainCardQuery = 'SELECT c.card_type, c.image_url, c.name FROM cards c WHERE c.id = ?';

                    mainDb.get(mainCardQuery, [main_card_id], (err, mainCardRow) => {
                        if (!err && mainCardRow) {
                            card_type = mainCardRow.card_type;
                            image_url = mainCardRow.image_url;
                            // Convert external URL to local path if needed
                            if (image_url && image_url.startsWith('https://')) {
                                const filename = image_url.split('/').pop();
                                image_url = `/cards/${filename}`;
                            }
                        }

                        cards.push({
                            card_name: cardRow.card_name,
                            card_code: cardRow.card_code,
                            quantity: cardRow.quantity,
                            chinese_name: cardRow.chinese_name,
                            card_type,
                            image_url
                        });

                        processedCards++;
                        if (processedCards === cardRows.length) {
                            finishResponse();
                        }
                    });
                } else {
                    // Determine card type from card name if not mapped
                    if (cardRow.card_name.includes('エネルギー')) {
                        // Check if it's basic energy (contains '基本') or special energy
                        if (cardRow.card_name.includes('基本') || cardRow.card_code?.includes('基本')) {
                            card_type = '基本能量';
                        } else {
                            card_type = '特殊能量';
                        }
                    } else if (cardRow.card_name.includes('博士') || cardRow.card_name.includes('サポート')) {
                        card_type = '支援者';
                    } else if (cardRow.card_name.includes('スタジアム')) {
                        card_type = '競技場';
                    } else {
                        card_type = '其他';
                    }

                    cards.push({
                        card_name: cardRow.card_name,
                        card_code: cardRow.card_code,
                        quantity: cardRow.quantity,
                        chinese_name: cardRow.chinese_name,
                        card_type,
                        image_url
                    });

                    processedCards++;
                    if (processedCards === cardRows.length) {
                        finishResponse();
                    }
                }
            });

            function finishResponse() {
                res.json({
                    deck: {
                        deck_id: deckRow.deck_id,
                        rank: deckRow.rank,
                        deck_url: deckRow.deck_url,
                        event_date: deckRow.event_date,
                        total_cards: deckRow.total_cards
                    },
                    cards
                });
            }
        });
    });
});

// Start server
initDatabases().then(() => {
    app.listen(PORT, () => {
        console.log('='.repeat(70));
        console.log('🔗 手動卡片對應系統 (Node.js)');
        console.log('='.repeat(70));
        console.log(`\n✅ 伺服器啟動成功!`);
        console.log(`🌐 請在瀏覽器開啟: http://localhost:${PORT}`);
        console.log(`\n💡 使用說明:`);
        console.log('   1. 左側選擇未對應的日文卡片');
        console.log('   2. 右側搜尋並選擇對應的中文卡片');
        console.log('   3. 點擊「建立對應連結」完成配對');
        console.log(`\n⌨️  按 Ctrl+C 停止伺服器`);
        console.log('='.repeat(70));
    });
}).catch(err => {
    console.error('❌ 資料庫載入失敗:', err.message);
    process.exit(1);
});

// Graceful shutdown
process.on('SIGINT', () => {
    console.log('\n\n⏹️  正在關閉伺服器...');
    saveEventDb();
    eventDb.close();
    mainDb.close();
    process.exit(0);
});
