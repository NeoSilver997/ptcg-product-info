# PTCG Event Scraper - Summary

## Features Implemented

### ✅ Enhanced Event Scraper (`event_scraper_enhanced.py`)

1. **Event Data Extraction**
   - Event ID from URL
   - Event title
   - Event date (format: YYYY-MM-DD)
   - Event location/venue
   - Tournament results with rankings

2. **Deck Scraping**
   - Scrape by deck ID: `scraper.scrape_deck_by_id("deck_id_here")`
   - Extract complete card list (60 cards)
   - Card names, quantities, images
   - Deck code for sharing

3. **Organized Output**
   - Creates folder per event: `event_data/event_{id}_{date}/`
   - Saves event info: `event_info.json`
   - Saves all decks: `deck_{deck_id}.json`

## File Structure

```
event_data/
└── event_848638_2025-11-11/
    ├── event_info.json          # Event details + all results
    ├── deck_pMMyyp-Bj58oH-M2MpyS.json  # 1st place deck
    ├── deck_DcY884-4mRFyP-Y8x4xx.json  # 2nd place deck
    ├── deck_yMXp2p-lh12TR-M2Sy3y.json  # 3rd place deck
    └── ... (5 more decks)
```

## Usage Examples

### 1. Scrape Complete Event with All Decks

```python
from event_scraper_enhanced import EventDeckScraper

scraper = EventDeckScraper(output_dir="event_data")

# Scrape event and all participating decks
event_url = "https://players.pokemon-card.com/event/detail/848638/result"
folder = scraper.scrape_event_with_decks(event_url)

print(f"Data saved to: {folder}")
```

### 2. Scrape Individual Deck by ID

```python
scraper = EventDeckScraper()

# Scrape specific deck
deck_id = "pMMyyp-Bj58oH-M2MpyS"
deck_data = scraper.scrape_deck_by_id(deck_id)

# Save to file
scraper.save_deck_data(deck_data)
```

### 3. Scrape Only Event Info (No Decks)

```python
scraper = EventDeckScraper()

# Get event data
event_data = scraper.scrape_event(event_url)

# Save event info
scraper.save_event_data(event_data)
```

## Data Format

### Event Info JSON

```json
{
  "event_url": "https://players.pokemon-card.com/event/detail/848638/result",
  "event_id": "848638",
  "event_title": "シティリーグ2026 シーズン2 オープンリーグ",
  "event_date": "2025-11-11",
  "event_location": "",
  "results": [
    {
      "rank": "1位",
      "points": "100pt",
      "username": "あぼろっぷ",
      "area": "兵庫県",
      "deck_url": "https://www.pokemon-card.com/deck/confirm.html/deckID/...",
      "deck_id": "pMMyyp-Bj58oH-M2MpyS"
    }
  ]
}
```

### Deck JSON

```json
{
  "deck_url": "https://www.pokemon-card.com/deck/confirm.html/deckID/pMMyyp-Bj58oH-M2MpyS",
  "deck_id": "pMMyyp-Bj58oH-M2MpyS",
  "deck_code": "pMMyyp-Bj58oH-M2MpyS",
  "cards": [
    {
      "card_id": "47259",
      "name": "マリィのオーロンゲex(SVOM 007/019)",
      "quantity": 2,
      "image_url": "https://www.pokemon-card.com/assets/images/card_images/large/SVOM/047259_P_MARIINOORONGEEX.jpg"
    }
  ]
}
```

## Current Results

### Event 848638 (2025-11-11)
- **Event**: シティリーグ2026 シーズン2 オープンリーグ
- **Date**: November 11, 2025
- **Results**: 8 participants
- **Decks Scraped**: 8 complete decks (60 cards each)

## Next Steps (Future Enhancements)

### Date Range Filtering
To scrape events by date range, you would need to:
1. Find the event list API endpoint
2. Filter events by date
3. Loop through and scrape each event

### Batch Processing
```python
# Pseudo-code for batch processing
event_ids = ["848638", "848639", "848640"]
for event_id in event_ids:
    event_url = f"https://players.pokemon-card.com/event/detail/{event_id}/result"
    scraper.scrape_event_with_decks(event_url)
    time.sleep(5)  # Be respectful to server
```

## Notes

- The event list page uses JavaScript (Vue.js), so Selenium is required
- Each deck scrape takes ~5-8 seconds
- Event with 8 decks takes ~1-2 minutes total
- Rate limiting: 2 second delay between deck scrapes
- All output uses UTF-8 encoding for Japanese text
