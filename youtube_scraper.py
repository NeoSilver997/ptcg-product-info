#!/usr/bin/env python3
"""
YouTube PTCG Deck Video Scraper

Monitor YouTube for Pokemon TCG deck-related videos and store them in the database.
Extracts deck codes and card information from video titles and descriptions.
"""

import os
import re
import json
import logging
import sqlite3
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class YouTubeDeckScraper:
    """
    Scraper for Pokemon TCG deck videos from YouTube.
    
    Uses YouTube Data API v3 to search for PTCG deck videos and extracts
    deck information from titles and descriptions.
    """
    
    # Common PTCG-related search keywords (Japanese)
    DEFAULT_SEARCH_KEYWORDS = [
        'ポケカ デッキ',  # Pokemon Card Deck
        'ポケモンカード デッキ紹介',  # Pokemon Card Deck Introduction
        'ポケカ 環境デッキ',  # Pokemon Card Meta Deck
        'ポケカ デッキレシピ',  # Pokemon Card Deck Recipe
        'PTCG deck',
        'Pokemon TCG deck profile',
    ]
    
    # Deck code pattern (format: XXXXXX-YYYYYY-ZZZZZZ)
    DECK_CODE_PATTERN = re.compile(r'[a-zA-Z0-9]{6}-[a-zA-Z0-9]{6}-[a-zA-Z0-9]{6}')
    
    def __init__(self, api_key: Optional[str] = None, db_path: str = 'ptcg_events.db'):
        """
        Initialize the YouTube deck scraper.
        
        Args:
            api_key: YouTube Data API key. If None, reads from YOUTUBE_API_KEY env var.
            db_path: Path to SQLite database file.
        """
        self.api_key = api_key or os.environ.get('YOUTUBE_API_KEY')
        self.db_path = db_path
        self.youtube = None
        
        if self.api_key:
            try:
                from googleapiclient.discovery import build
                self.youtube = build('youtube', 'v3', developerKey=self.api_key)
                logger.info("YouTube API client initialized")
            except ImportError:
                logger.warning("google-api-python-client not installed. Install with: pip install google-api-python-client")
            except Exception as e:
                logger.error(f"Failed to initialize YouTube API client: {e}")
        else:
            logger.warning("No YouTube API key provided. Set YOUTUBE_API_KEY environment variable or pass api_key parameter.")
    
    def create_tables(self, conn: sqlite3.Connection) -> None:
        """
        Create database tables for YouTube video data.
        
        Args:
            conn: SQLite database connection
        """
        cursor = conn.cursor()
        
        # YouTube videos table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS youtube_videos (
                video_id TEXT PRIMARY KEY,
                channel_id TEXT,
                channel_name TEXT,
                title TEXT NOT NULL,
                description TEXT,
                published_at TIMESTAMP,
                thumbnail_url TEXT,
                view_count INTEGER DEFAULT 0,
                like_count INTEGER DEFAULT 0,
                comment_count INTEGER DEFAULT 0,
                deck_code TEXT,
                import_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # YouTube video to deck mapping table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS youtube_deck_links (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                video_id TEXT NOT NULL,
                deck_id TEXT,
                deck_code TEXT,
                source_type TEXT DEFAULT 'youtube',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (video_id) REFERENCES youtube_videos(video_id) ON DELETE CASCADE,
                FOREIGN KEY (deck_id) REFERENCES decks(deck_id) ON DELETE SET NULL,
                UNIQUE(video_id, deck_code)
            )
        """)
        
        # YouTube channels table (for tracking favorite channels)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS youtube_channels (
                channel_id TEXT PRIMARY KEY,
                channel_name TEXT,
                channel_url TEXT,
                subscriber_count INTEGER DEFAULT 0,
                video_count INTEGER DEFAULT 0,
                is_monitored BOOLEAN DEFAULT 1,
                last_checked TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create indexes for performance
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_youtube_videos_channel ON youtube_videos(channel_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_youtube_videos_published ON youtube_videos(published_at)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_youtube_videos_deck_code ON youtube_videos(deck_code)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_youtube_deck_links_video ON youtube_deck_links(video_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_youtube_deck_links_deck ON youtube_deck_links(deck_id)")
        
        conn.commit()
        logger.info("YouTube database tables created successfully")
    
    def search_videos(
        self,
        keywords: Optional[List[str]] = None,
        max_results: int = 25,
        published_after: Optional[datetime] = None
    ) -> List[Dict]:
        """
        Search YouTube for PTCG deck videos.
        
        Args:
            keywords: List of search keywords. Uses defaults if None.
            max_results: Maximum number of results per keyword search.
            published_after: Only return videos published after this date.
        
        Returns:
            List of video dictionaries with metadata.
        """
        if not self.youtube:
            logger.error("YouTube API not initialized")
            return []
        
        if keywords is None:
            keywords = self.DEFAULT_SEARCH_KEYWORDS
        
        all_videos = []
        seen_video_ids = set()
        
        for keyword in keywords:
            try:
                logger.info(f"Searching YouTube for: {keyword}")
                
                search_params = {
                    'q': keyword,
                    'part': 'snippet',
                    'type': 'video',
                    'maxResults': max_results,
                    'order': 'date',  # Get newest first
                    'regionCode': 'JP',  # Target Japanese region
                }
                
                if published_after:
                    search_params['publishedAfter'] = published_after.strftime('%Y-%m-%dT%H:%M:%SZ')
                
                request = self.youtube.search().list(**search_params)
                response = request.execute()
                
                for item in response.get('items', []):
                    video_id = item['id']['videoId']
                    
                    if video_id in seen_video_ids:
                        continue
                    
                    seen_video_ids.add(video_id)
                    
                    snippet = item['snippet']
                    video = {
                        'video_id': video_id,
                        'channel_id': snippet['channelId'],
                        'channel_name': snippet['channelTitle'],
                        'title': snippet['title'],
                        'description': snippet['description'],
                        'published_at': snippet['publishedAt'],
                        'thumbnail_url': snippet['thumbnails'].get('high', {}).get('url', ''),
                    }
                    
                    # Extract deck code from title or description
                    deck_codes = self.extract_deck_codes(
                        f"{video['title']} {video['description']}"
                    )
                    if deck_codes:
                        video['deck_code'] = deck_codes[0]  # Use first found deck code
                    
                    all_videos.append(video)
                
                logger.info(f"Found {len(response.get('items', []))} videos for keyword: {keyword}")
                
            except Exception as e:
                logger.error(f"Error searching for '{keyword}': {e}")
                continue
        
        logger.info(f"Total unique videos found: {len(all_videos)}")
        return all_videos
    
    def get_video_details(self, video_ids: List[str]) -> Dict[str, Dict]:
        """
        Get detailed statistics for a list of videos.
        
        Args:
            video_ids: List of YouTube video IDs.
        
        Returns:
            Dictionary mapping video IDs to their statistics.
        """
        if not self.youtube:
            logger.error("YouTube API not initialized")
            return {}
        
        details = {}
        
        # API allows max 50 IDs per request
        for i in range(0, len(video_ids), 50):
            batch_ids = video_ids[i:i+50]
            
            try:
                request = self.youtube.videos().list(
                    part='statistics,snippet',
                    id=','.join(batch_ids)
                )
                response = request.execute()
                
                for item in response.get('items', []):
                    video_id = item['id']
                    stats = item.get('statistics', {})
                    snippet = item.get('snippet', {})
                    
                    details[video_id] = {
                        'view_count': int(stats.get('viewCount', 0)),
                        'like_count': int(stats.get('likeCount', 0)),
                        'comment_count': int(stats.get('commentCount', 0)),
                        'description': snippet.get('description', ''),  # Full description
                    }
                    
            except Exception as e:
                logger.error(f"Error fetching video details: {e}")
        
        return details
    
    def extract_deck_codes(self, text: str) -> List[str]:
        """
        Extract Pokemon TCG deck codes from text.
        
        Deck codes follow the format: XXXXXX-YYYYYY-ZZZZZZ
        
        Args:
            text: Text to search for deck codes.
        
        Returns:
            List of found deck codes.
        """
        return self.DECK_CODE_PATTERN.findall(text)
    
    def save_videos_to_db(self, videos: List[Dict], conn: sqlite3.Connection) -> Tuple[int, int]:
        """
        Save videos to the database.
        
        Args:
            videos: List of video dictionaries.
            conn: SQLite database connection.
        
        Returns:
            Tuple of (inserted_count, updated_count)
        """
        cursor = conn.cursor()
        inserted = 0
        updated = 0
        
        for video in videos:
            try:
                # Check if video already exists
                cursor.execute(
                    "SELECT video_id FROM youtube_videos WHERE video_id = ?",
                    (video['video_id'],)
                )
                existing = cursor.fetchone()
                
                if existing:
                    # Update existing video
                    cursor.execute("""
                        UPDATE youtube_videos SET
                            title = ?,
                            description = ?,
                            thumbnail_url = ?,
                            view_count = ?,
                            like_count = ?,
                            comment_count = ?,
                            deck_code = ?,
                            last_updated = CURRENT_TIMESTAMP
                        WHERE video_id = ?
                    """, (
                        video['title'],
                        video.get('description', ''),
                        video.get('thumbnail_url', ''),
                        video.get('view_count', 0),
                        video.get('like_count', 0),
                        video.get('comment_count', 0),
                        video.get('deck_code'),
                        video['video_id']
                    ))
                    updated += 1
                else:
                    # Insert new video
                    cursor.execute("""
                        INSERT INTO youtube_videos
                        (video_id, channel_id, channel_name, title, description,
                         published_at, thumbnail_url, view_count, like_count,
                         comment_count, deck_code)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        video['video_id'],
                        video.get('channel_id', ''),
                        video.get('channel_name', ''),
                        video['title'],
                        video.get('description', ''),
                        video.get('published_at'),
                        video.get('thumbnail_url', ''),
                        video.get('view_count', 0),
                        video.get('like_count', 0),
                        video.get('comment_count', 0),
                        video.get('deck_code')
                    ))
                    inserted += 1
                
                # If video has deck code, create link
                deck_code = video.get('deck_code')
                if deck_code:
                    self._link_deck(cursor, video['video_id'], deck_code)
                
            except Exception as e:
                logger.error(f"Error saving video {video.get('video_id')}: {e}")
        
        conn.commit()
        logger.info(f"Saved videos to database: {inserted} inserted, {updated} updated")
        return inserted, updated
    
    def _link_deck(self, cursor: sqlite3.Cursor, video_id: str, deck_code: str) -> None:
        """
        Create link between video and deck code.
        
        Args:
            cursor: SQLite cursor
            video_id: YouTube video ID
            deck_code: Pokemon TCG deck code
        """
        try:
            # Check if deck exists in decks table
            cursor.execute(
                "SELECT deck_id FROM decks WHERE deck_id = ? OR deck_code = ?",
                (deck_code, deck_code)
            )
            deck_row = cursor.fetchone()
            deck_id = deck_row[0] if deck_row else None
        except sqlite3.OperationalError:
            # Table doesn't exist - no deck to link
            deck_id = None
        
        # Create or update link
        cursor.execute("""
            INSERT OR REPLACE INTO youtube_deck_links
            (video_id, deck_id, deck_code)
            VALUES (?, ?, ?)
        """, (video_id, deck_id, deck_code))
    
    def add_monitored_channel(
        self,
        channel_id: str,
        conn: sqlite3.Connection
    ) -> bool:
        """
        Add a YouTube channel to the monitored list.
        
        Args:
            channel_id: YouTube channel ID.
            conn: SQLite database connection.
        
        Returns:
            True if channel was added successfully.
        """
        if not self.youtube:
            logger.error("YouTube API not initialized")
            return False
        
        try:
            # Get channel info
            request = self.youtube.channels().list(
                part='snippet,statistics',
                id=channel_id
            )
            response = request.execute()
            
            if not response.get('items'):
                logger.warning(f"Channel not found: {channel_id}")
                return False
            
            channel = response['items'][0]
            snippet = channel['snippet']
            stats = channel.get('statistics', {})
            
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO youtube_channels
                (channel_id, channel_name, channel_url, subscriber_count, video_count, is_monitored)
                VALUES (?, ?, ?, ?, ?, 1)
            """, (
                channel_id,
                snippet['title'],
                f"https://www.youtube.com/channel/{channel_id}",
                int(stats.get('subscriberCount', 0)),
                int(stats.get('videoCount', 0))
            ))
            conn.commit()
            
            logger.info(f"Added monitored channel: {snippet['title']}")
            return True
            
        except Exception as e:
            logger.error(f"Error adding channel {channel_id}: {e}")
            return False
    
    def scrape_channel_videos(
        self,
        channel_id: str,
        max_results: int = 50,
        published_after: Optional[datetime] = None
    ) -> List[Dict]:
        """
        Scrape videos from a specific YouTube channel.
        
        Args:
            channel_id: YouTube channel ID.
            max_results: Maximum number of videos to fetch.
            published_after: Only return videos published after this date.
        
        Returns:
            List of video dictionaries.
        """
        if not self.youtube:
            logger.error("YouTube API not initialized")
            return []
        
        videos = []
        
        try:
            search_params = {
                'channelId': channel_id,
                'part': 'snippet',
                'type': 'video',
                'maxResults': min(max_results, 50),
                'order': 'date',
            }
            
            if published_after:
                search_params['publishedAfter'] = published_after.strftime('%Y-%m-%dT%H:%M:%SZ')
            
            request = self.youtube.search().list(**search_params)
            response = request.execute()
            
            for item in response.get('items', []):
                snippet = item['snippet']
                video = {
                    'video_id': item['id']['videoId'],
                    'channel_id': channel_id,
                    'channel_name': snippet['channelTitle'],
                    'title': snippet['title'],
                    'description': snippet['description'],
                    'published_at': snippet['publishedAt'],
                    'thumbnail_url': snippet['thumbnails'].get('high', {}).get('url', ''),
                }
                
                # Extract deck codes
                deck_codes = self.extract_deck_codes(
                    f"{video['title']} {video['description']}"
                )
                if deck_codes:
                    video['deck_code'] = deck_codes[0]
                
                videos.append(video)
            
            logger.info(f"Found {len(videos)} videos from channel {channel_id}")
            
        except Exception as e:
            logger.error(f"Error scraping channel {channel_id}: {e}")
        
        return videos
    
    def run_monitoring_cycle(
        self,
        keywords: Optional[List[str]] = None,
        days_back: int = 7,
        scrape_monitored_channels: bool = True
    ) -> Dict:
        """
        Run a complete monitoring cycle.
        
        Searches for new videos and updates the database.
        
        Args:
            keywords: Search keywords. Uses defaults if None.
            days_back: How many days back to search.
            scrape_monitored_channels: Whether to also scrape monitored channels.
        
        Returns:
            Dictionary with cycle statistics.
        """
        stats = {
            'videos_found': 0,
            'videos_inserted': 0,
            'videos_updated': 0,
            'deck_codes_found': 0,
            'errors': []
        }
        
        conn = sqlite3.connect(self.db_path)
        
        try:
            # Ensure tables exist
            self.create_tables(conn)
            
            published_after = datetime.utcnow() - timedelta(days=days_back)
            
            # Search for videos with keywords
            videos = self.search_videos(
                keywords=keywords,
                max_results=25,
                published_after=published_after
            )
            
            # Scrape monitored channels
            if scrape_monitored_channels:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT channel_id FROM youtube_channels WHERE is_monitored = 1"
                )
                channels = cursor.fetchall()
                
                for (channel_id,) in channels:
                    channel_videos = self.scrape_channel_videos(
                        channel_id,
                        max_results=25,
                        published_after=published_after
                    )
                    
                    # Avoid duplicates
                    existing_ids = {v['video_id'] for v in videos}
                    for video in channel_videos:
                        if video['video_id'] not in existing_ids:
                            videos.append(video)
                            existing_ids.add(video['video_id'])
            
            stats['videos_found'] = len(videos)
            
            # Get detailed stats for all videos
            if videos and self.youtube:
                video_ids = [v['video_id'] for v in videos]
                details = self.get_video_details(video_ids)
                
                for video in videos:
                    if video['video_id'] in details:
                        video.update(details[video['video_id']])
                    
                    # Check for deck codes in full description only if not already found
                    # The search API returns truncated descriptions, so we need the full one
                    if 'deck_code' not in video:
                        full_desc = details.get(video['video_id'], {}).get('description', '')
                        if full_desc:
                            deck_codes = self.extract_deck_codes(full_desc)
                            if deck_codes:
                                video['deck_code'] = deck_codes[0]
            
            # Count deck codes
            stats['deck_codes_found'] = sum(1 for v in videos if v.get('deck_code'))
            
            # Save to database
            inserted, updated = self.save_videos_to_db(videos, conn)
            stats['videos_inserted'] = inserted
            stats['videos_updated'] = updated
            
        except Exception as e:
            logger.error(f"Error in monitoring cycle: {e}")
            stats['errors'].append(str(e))
        finally:
            conn.close()
        
        return stats
    
    def get_statistics(self) -> Dict:
        """
        Get YouTube monitoring statistics from the database.
        
        Returns:
            Dictionary with various statistics.
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        stats = {}
        
        try:
            # Total videos
            cursor.execute("SELECT COUNT(*) FROM youtube_videos")
            stats['total_videos'] = cursor.fetchone()[0]
            
            # Videos with deck codes
            cursor.execute("SELECT COUNT(*) FROM youtube_videos WHERE deck_code IS NOT NULL")
            stats['videos_with_deck_codes'] = cursor.fetchone()[0]
            
            # Unique channels
            cursor.execute("SELECT COUNT(DISTINCT channel_id) FROM youtube_videos")
            stats['unique_channels'] = cursor.fetchone()[0]
            
            # Monitored channels
            cursor.execute("SELECT COUNT(*) FROM youtube_channels WHERE is_monitored = 1")
            stats['monitored_channels'] = cursor.fetchone()[0]
            
            # Linked decks
            cursor.execute("SELECT COUNT(*) FROM youtube_deck_links WHERE deck_id IS NOT NULL")
            stats['linked_decks'] = cursor.fetchone()[0]
            
            # Date range
            cursor.execute("SELECT MIN(published_at), MAX(published_at) FROM youtube_videos")
            date_range = cursor.fetchone()
            stats['earliest_video'] = date_range[0]
            stats['latest_video'] = date_range[1]
            
            # Top channels
            cursor.execute("""
                SELECT channel_name, COUNT(*) as video_count
                FROM youtube_videos
                GROUP BY channel_id
                ORDER BY video_count DESC
                LIMIT 10
            """)
            stats['top_channels'] = [
                {'channel': row[0], 'videos': row[1]}
                for row in cursor.fetchall()
            ]
            
        except Exception as e:
            logger.error(f"Error getting statistics: {e}")
        finally:
            conn.close()
        
        return stats


def main():
    """Main function for testing the YouTube scraper."""
    import argparse
    
    parser = argparse.ArgumentParser(description='YouTube PTCG Deck Video Scraper')
    parser.add_argument('--api-key', help='YouTube Data API key')
    parser.add_argument('--db', default='ptcg_events.db', help='Database path')
    parser.add_argument('--days', type=int, default=7, help='Days back to search')
    parser.add_argument('--init-only', action='store_true', help='Only initialize database tables')
    parser.add_argument('--stats', action='store_true', help='Show statistics')
    parser.add_argument('--add-channel', help='Add a channel to monitor (channel ID)')
    
    args = parser.parse_args()
    
    scraper = YouTubeDeckScraper(api_key=args.api_key, db_path=args.db)
    
    if args.init_only:
        conn = sqlite3.connect(args.db)
        scraper.create_tables(conn)
        conn.close()
        print("Database tables initialized")
        return
    
    if args.stats:
        stats = scraper.get_statistics()
        print("\n" + "=" * 60)
        print("YOUTUBE MONITORING STATISTICS")
        print("=" * 60)
        for key, value in stats.items():
            if key == 'top_channels':
                print(f"\nTop Channels:")
                for ch in value:
                    print(f"  - {ch['channel']}: {ch['videos']} videos")
            else:
                print(f"{key}: {value}")
        print("=" * 60)
        return
    
    if args.add_channel:
        conn = sqlite3.connect(args.db)
        scraper.create_tables(conn)
        success = scraper.add_monitored_channel(args.add_channel, conn)
        conn.close()
        if success:
            print(f"Channel added successfully: {args.add_channel}")
        else:
            print(f"Failed to add channel: {args.add_channel}")
        return
    
    # Run monitoring cycle
    print("\n" + "=" * 60)
    print("RUNNING YOUTUBE MONITORING CYCLE")
    print("=" * 60)
    
    stats = scraper.run_monitoring_cycle(days_back=args.days)
    
    print(f"\nResults:")
    print(f"  Videos found: {stats['videos_found']}")
    print(f"  Videos inserted: {stats['videos_inserted']}")
    print(f"  Videos updated: {stats['videos_updated']}")
    print(f"  Deck codes found: {stats['deck_codes_found']}")
    
    if stats['errors']:
        print(f"\nErrors:")
        for error in stats['errors']:
            print(f"  - {error}")
    
    print("=" * 60)


if __name__ == "__main__":
    main()
