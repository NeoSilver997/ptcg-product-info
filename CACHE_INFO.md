# Card Code Cache System

## Overview
The `fetch_card_codes.py` script now includes a caching system that stores card_id → card_code mappings to avoid redundant API calls.

## Cache File
- **Location**: `card_code_cache.json` (in the project root)
- **Format**: JSON object with card_id as keys and card_code as values

Example:
```json
{
  "47198": "SVN 023/045",
  "47878": "MA 019/043",
  "47792": "M1L 059/063"
}
```

## How It Works

1. **Load Cache**: At startup, loads existing card codes from `card_code_cache.json`
2. **Check Cache First**: Before fetching from web, checks if card_id exists in cache
3. **Fetch if Needed**: Only makes HTTP requests for cards not in cache
4. **Update Cache**: Adds newly fetched codes to cache
5. **Save Cache**: Writes updated cache back to file after all fetches complete
6. **Smart Delays**: Only delays 2 seconds between actual web requests, skips delay for cached results

## Benefits

- **Speed**: Cached cards are retrieved instantly (no HTTP request)
- **Efficiency**: Reduces load on Pokemon card website servers
- **Resumable**: If script is interrupted, previously fetched codes are preserved
- **Incremental**: Can run multiple times, only fetches new cards each time

## Usage

### First Run (Empty Cache)
```bash
python fetch_card_codes.py --dry-run
```
Output:
```
Cache status: 0 cards in cache, 812 cards to fetch
[1/812] Fetching card code for 47281...
[2/812] Fetching card code for 47282...
...
```
Estimated time: ~27 minutes (812 cards × 2 sec)

### Second Run (With Cache)
```bash
python fetch_card_codes.py --dry-run
```
Output:
```
Cache status: 812 cards in cache, 0 cards to fetch
```
Estimated time: ~1 second (no web requests needed!)

### Partial Cache
If you have 100 cards cached and find 50 new cards:
```
Cache status: 100 cards in cache, 50 cards to fetch
```
Estimated time: ~2 minutes (50 cards × 2 sec)

## Cache Management

### View Cache
```bash
cat card_code_cache.json
```

### Clear Cache
```bash
rm card_code_cache.json
```

### Manual Entry
You can manually add cards to the cache:
```json
{
  "47198": "SVN 023/045",
  "47878": "MA 019/043"
}
```

## Statistics

- **Current cache size**: 1 card (as of 2025-11-12 01:03)
- **Total cards needing codes**: 812 cards
- **Estimated time for full fetch**: ~27 minutes
- **Estimated time with full cache**: <1 second

## Notes

- Cache is automatically created on first run
- Cache is updated after each successful fetch
- If script is interrupted, cache retains all previously fetched codes
- Cache uses card_id as string keys (e.g., "47198" not 47198)
- No expiration - codes are cached indefinitely (they don't change)
