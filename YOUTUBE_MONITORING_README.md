# YouTube PTCG Deck Video Monitoring

Monitor YouTube for Pokemon TCG deck-related videos and store deck information in the database.

## Overview

This feature allows you to:
- Search YouTube for PTCG deck videos using keywords
- Extract deck codes from video titles and descriptions
- Link YouTube videos to existing tournament decks
- Import new decks from deck codes found in videos
- Monitor specific YouTube channels for new deck content

## Requirements

### Python Dependencies

Install the required packages:

```bash
pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib
```

Or install all requirements:

```bash
pip install -r requirements.txt
```

### YouTube API Key

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the **YouTube Data API v3**
4. Create an API key under **APIs & Services > Credentials**
5. Set your API key:

```bash
# Option 1: Environment variable
export YOUTUBE_API_KEY="your-api-key-here"

# Option 2: In config.py
YOUTUBE_API_KEY = "your-api-key-here"
```

## Usage

### Basic Monitoring Cycle

Run a monitoring cycle to search for new deck videos:

```bash
python youtube_scraper.py --api-key YOUR_API_KEY --days 7
```

This will:
1. Search YouTube for PTCG deck videos from the last 7 days
2. Extract deck codes from titles and descriptions
3. Save video information to the database
4. Create links between videos and existing decks

### Initialize Database Tables Only

```bash
python youtube_scraper.py --init-only --db ptcg_events.db
```

### View Statistics

```bash
python youtube_scraper.py --stats
```

### Add a Channel to Monitor

```bash
python youtube_scraper.py --add-channel CHANNEL_ID
```

## Importing Deck Data

### Link Videos to Existing Decks

```bash
python import_youtube_decks.py --link-existing
```

### Import New Decks from YouTube Videos

```bash
python import_youtube_decks.py --import-decks --max-imports 50
```

### View Summary

```bash
python import_youtube_decks.py --summary
```

## Configuration

Edit `config.py` to customize behavior:

```python
# YouTube Scraper Settings
YOUTUBE_API_KEY = None  # Or set your API key directly
YOUTUBE_ENABLED = False  # Set to True to enable
YOUTUBE_SEARCH_KEYWORDS = [
    'ポケカ デッキ',
    'ポケモンカード デッキ紹介',
    'ポケカ 環境デッキ',
    'ポケカ デッキレシピ',
    'PTCG deck profile',
]
YOUTUBE_DAYS_BACK = 7
YOUTUBE_MAX_RESULTS_PER_KEYWORD = 25
```

## Database Schema

### youtube_videos

Stores video metadata:

| Column | Type | Description |
|--------|------|-------------|
| video_id | TEXT | YouTube video ID (primary key) |
| channel_id | TEXT | YouTube channel ID |
| channel_name | TEXT | Channel display name |
| title | TEXT | Video title |
| description | TEXT | Video description |
| published_at | TIMESTAMP | Publication date |
| thumbnail_url | TEXT | Thumbnail image URL |
| view_count | INTEGER | Number of views |
| like_count | INTEGER | Number of likes |
| comment_count | INTEGER | Number of comments |
| deck_code | TEXT | Extracted deck code |
| import_timestamp | TIMESTAMP | When video was saved |
| last_updated | TIMESTAMP | Last update time |

### youtube_deck_links

Links videos to decks:

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| video_id | TEXT | YouTube video ID |
| deck_id | TEXT | Linked deck ID |
| deck_code | TEXT | Deck code |
| source_type | TEXT | 'youtube' or 'youtube_imported' |
| created_at | TIMESTAMP | Creation time |

### youtube_channels

Monitored channels:

| Column | Type | Description |
|--------|------|-------------|
| channel_id | TEXT | YouTube channel ID (primary key) |
| channel_name | TEXT | Channel display name |
| channel_url | TEXT | Channel URL |
| subscriber_count | INTEGER | Number of subscribers |
| video_count | INTEGER | Number of videos |
| is_monitored | BOOLEAN | Whether to monitor this channel |
| last_checked | TIMESTAMP | Last check time |

## Web API Endpoints

The web server provides YouTube-related endpoints:

### GET /api/youtube/stats

Get YouTube monitoring statistics.

**Response:**
```json
{
  "totalVideos": 150,
  "videosWithDecks": 45,
  "linkedDecks": 30,
  "uniqueChannels": 25
}
```

### GET /api/youtube/videos

Get recent videos.

**Parameters:**
- `limit` (optional): Maximum results (default: 50, max: 100)
- `offset` (optional): Offset for pagination

**Response:**
```json
{
  "videos": [
    {
      "video_id": "abc123",
      "channel_name": "ポケカチャンネル",
      "title": "最強デッキ紹介！",
      "published_at": "2025-11-25T10:00:00Z",
      "deck_code": "XXXXXX-YYYYYY-ZZZZZZ",
      "video_url": "https://www.youtube.com/watch?v=abc123"
    }
  ],
  "count": 50,
  "offset": 0
}
```

### GET /api/youtube/videos/with-decks

Get videos that have deck codes.

### GET /api/youtube/video/:videoId/deck

Get deck details for a specific video.

### GET /api/youtube/channels

Get list of monitored channels.

## Deck Code Pattern

The scraper extracts deck codes in the format:

```
XXXXXX-YYYYYY-ZZZZZZ
```

Where each part is 6 alphanumeric characters.

Example: `pMMyyp-Bj58oH-M2MpyS`

## Python API

### Using YouTubeDeckScraper

```python
from youtube_scraper import YouTubeDeckScraper

# Initialize
scraper = YouTubeDeckScraper(
    api_key="your-api-key",
    db_path="ptcg_events.db"
)

# Search for videos
videos = scraper.search_videos(
    keywords=['ポケカ デッキ'],
    max_results=25,
    published_after=datetime(2025, 11, 1)
)

# Run full monitoring cycle
stats = scraper.run_monitoring_cycle(days_back=7)
print(f"Found {stats['videos_found']} videos")
print(f"Found {stats['deck_codes_found']} deck codes")

# Get statistics
stats = scraper.get_statistics()
```

### Using YouTubeDeckImporter

```python
from import_youtube_decks import YouTubeDeckImporter

importer = YouTubeDeckImporter(db_path="ptcg_events.db")
importer.connect()

# Link existing decks
links = importer.link_existing_decks()
print(f"Created {links} new links")

# Import new decks
stats = importer.import_all_youtube_decks(max_imports=50)
print(f"Imported {stats['imported']} decks")

# Get summary
summary = importer.get_youtube_deck_summary()

importer.close()
```

## Best Practices

### API Quota Management

The YouTube Data API has daily quotas. To manage usage:

1. Search costs 100 units per call
2. Video details cost 1 unit per video
3. Channel details cost 1 unit per channel

Default quota is 10,000 units/day. Adjust `YOUTUBE_MAX_RESULTS_PER_KEYWORD` accordingly.

### Respectful Scraping

When importing decks from the Pokemon TCG website:
- Use 2+ second delays between requests
- Limit imports per session (default: 50)
- Run during off-peak hours

### Data Freshness

Recommended monitoring schedule:
- Daily: Search for new videos (last 1-2 days)
- Weekly: Full search (last 7 days) + channel scraping
- Monthly: Update video statistics

## Troubleshooting

### API Key Not Working

```
Error: YouTube API not initialized
```

- Verify API key is correct
- Check API is enabled in Google Cloud Console
- Ensure no IP restrictions on key

### No Deck Codes Found

- Deck codes may be in comments (not supported yet)
- Videos may not include deck codes in title/description
- Try adding monitored channels for better results

### Import Failures

```
Error importing deck: ...
```

- Deck code may be invalid
- Official website may be down
- Try again later with delays

## Contributing

To improve deck code extraction:

1. Add regex patterns for alternative formats
2. Implement comment scanning
3. Add OCR for deck codes in thumbnails

## Related Documentation

- [Event Database Guide](EVENT_DATABASE_README.md)
- [Card Linking Guide](CARD_LINKING_GUIDE.md)
- [Project Overview](PROJECT_README.md)
