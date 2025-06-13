import argparse
import json
import os
import re
from datetime import datetime

# Try to import Google API client (for YouTube operations)
try:
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    YOUTUBE_API_AVAILABLE = True
except ImportError:
    YOUTUBE_API_AVAILABLE = False
    print("Warning: Google API client not installed. YouTube operations will be limited.")
    print("Install with: pip install google-api-python-client")

# Config
DEFAULT_MAX_RESULTS = 5000
DEFAULT_BATCH_SIZE = 500
DEFAULT_REPLAYS_FILE = "replays.json"
DEFAULT_VIDEO_OUTPUT = "videos.json"

# YouTube API configuration
YOUTUBE_API_KEY = os.environ.get('YOUTUBE_API_KEY')
YOUTUBE_API_SERVICE_NAME = 'youtube'
YOUTUBE_API_VERSION = 'v3'


def fetch_channel_videos(channel_id, max_results=DEFAULT_MAX_RESULTS, batch_size=DEFAULT_BATCH_SIZE, start_offset=0, youtube_api_key=None):
    """Fetch videos from a YouTube channel in batches
    """
    youtube_api_key = youtube_api_key if youtube_api_key else YOUTUBE_API_KEY
    youtube_service = build(
        YOUTUBE_API_SERVICE_NAME,
        YOUTUBE_API_VERSION,
        developerKey=youtube_api_key
    )
    if not youtube_service:
        print("YouTube API not available")
        return [], [], False

    videos = []
    failed_videos = []

    try:
        # Get channel's uploads playlist
        channels_response = youtube_service.channels().list(
            part='contentDetails',
            id=channel_id
        ).execute()

        if not channels_response['items']:
            print(f"Channel {channel_id} not found")
            return [], [], False

        uploads_playlist_id = channels_response['items'][0]['contentDetails']['relatedPlaylists']['uploads']

        # Calculate how many videos we've already processed
        videos_to_skip = start_offset
        videos_in_batch = 0
        next_page_token = None

        # Skip to the right page if we have an offset
        while videos_to_skip > 0:
            page_size = min(50, videos_to_skip)
            skip_response = youtube_service.playlistItems().list(
                part='id',
                playlistId=uploads_playlist_id,
                maxResults=page_size,
                pageToken=next_page_token
            ).execute()

            videos_to_skip -= len(skip_response['items'])
            next_page_token = skip_response.get('nextPageToken')

            if not next_page_token:
                return [], [], False

        # Fetch videos for this batch
        while videos_in_batch < batch_size and len(videos) < max_results:
            remaining_in_batch = batch_size - videos_in_batch
            remaining_total = max_results - len(videos)
            page_size = min(50, remaining_in_batch, remaining_total)

            playlist_response = youtube_service.playlistItems().list(
                part='snippet',
                playlistId=uploads_playlist_id,
                maxResults=page_size,
                pageToken=next_page_token
            ).execute()

            for item in playlist_response['items']:
                video_id = item['snippet']['resourceId']['videoId']

                try:
                    # Get video details including tags and description
                    video_details = youtube_service.videos().list(
                        part='snippet,topicDetails',
                        id=video_id
                    ).execute()

                    tags = []
                    description = ''
                    if video_details['items']:
                        tags = video_details['items'][0]['snippet'].get('tags', [])
                        description = video_details['items'][0]['snippet'].get('description', '')

                    video_data = {
                        'youtubeId': video_id,
                        'originalTitle': item['snippet']['title'],
                        'date': item['snippet']['publishedAt'][:10],
                        'channelId': channel_id,
                        'tags': tags,
                        'description': description
                    }
                    videos.append(video_data)
                    videos_in_batch += 1

                except Exception as e:
                    failed_video = {
                        'youtubeId': video_id,
                        'originalTitle': item['snippet'].get('title', 'Unknown'),
                        'error': str(e),
                        'timestamp': datetime.now().isoformat()
                    }
                    failed_videos.append(failed_video)
                    print(f"Failed to fetch details for video {video_id}: {e}")

            next_page_token = playlist_response.get('nextPageToken')
            if not next_page_token:
                return videos, failed_videos, False

        # Check if there are more videos
        has_more = next_page_token is not None and len(videos) < max_results

    except HttpError as e:
        print(f"YouTube API error: {e}")
        return videos, failed_videos, False

    return videos, failed_videos, has_more

def fetch_playlist_videos(playlist_id, max_results=DEFAULT_MAX_RESULTS, batch_size=DEFAULT_BATCH_SIZE, start_offset=0, youtube_api_key=None):
    """Fetch videos from a YouTube channel in batches
    """
    youtube_api_key = youtube_api_key if youtube_api_key else YOUTUBE_API_KEY
    youtube_service = build(
        YOUTUBE_API_SERVICE_NAME,
        YOUTUBE_API_VERSION,
        developerKey=youtube_api_key
    )
    if not youtube_service:
        print("YouTube API not available")
        return [], [], False

    videos = []
    failed_videos = []

    try:
        uploads_playlist_id = playlist_id

        # Calculate how many videos we've already processed
        videos_to_skip = start_offset
        videos_in_batch = 0
        next_page_token = None

        # Skip to the right page if we have an offset
        while videos_to_skip > 0:
            page_size = min(50, videos_to_skip)
            skip_response = youtube_service.playlistItems().list(
                part='id',
                playlistId=uploads_playlist_id,
                maxResults=page_size,
                pageToken=next_page_token
            ).execute()

            videos_to_skip -= len(skip_response['items'])
            next_page_token = skip_response.get('nextPageToken')

            if not next_page_token:
                return [], [], False

        # Fetch videos for this batch
        while videos_in_batch < batch_size and len(videos) < max_results:
            remaining_in_batch = batch_size - videos_in_batch
            remaining_total = max_results - len(videos)
            page_size = min(50, remaining_in_batch, remaining_total)

            playlist_response = youtube_service.playlistItems().list(
                part='snippet',
                playlistId=uploads_playlist_id,
                maxResults=page_size,
                pageToken=next_page_token
            ).execute()

            for item in playlist_response['items']:
                video_id = item['snippet']['resourceId']['videoId']

                try:
                    # Get video details including tags and description
                    video_details = youtube_service.videos().list(
                        part='snippet,topicDetails',
                        id=video_id
                    ).execute()

                    tags = []
                    description = ''
                    if video_details['items']:
                        tags = video_details['items'][0]['snippet'].get('tags', [])
                        description = video_details['items'][0]['snippet'].get('description', '')

                    video_data = {
                        'youtubeId': video_id,
                        'originalTitle': item['snippet']['title'],
                        'date': item['snippet']['publishedAt'][:10],
                        'playlistId': playlist_id,
                        'tags': tags,
                        'description': description
                    }
                    videos.append(video_data)
                    videos_in_batch += 1

                except Exception as e:
                    failed_video = {
                        'youtubeId': video_id,
                        'originalTitle': item['snippet'].get('title', 'Unknown'),
                        'error': str(e),
                        'timestamp': datetime.now().isoformat()
                    }
                    failed_videos.append(failed_video)
                    print(f"Failed to fetch details for video {video_id}: {e}")

            next_page_token = playlist_response.get('nextPageToken')
            if not next_page_token:
                return videos, failed_videos, False

        # Check if there are more videos
        has_more = next_page_token is not None and len(videos) < max_results

    except HttpError as e:
        print(f"YouTube API error: {e}")
        return videos, failed_videos, False

    return videos, failed_videos, has_more

def filter_replays(replays, filter_key, filter_value, operation, negate=False):
    """Remove replays based on key-value criteria"""
    filtered = []

    for replay in replays:
        if filter_key not in replay:
            # If field doesn't exist, keep the replay when filtering (removing matches)
            filtered.append(replay)
            continue

        value = replay[filter_key]
        match = False

        if operation == 'equals':
            match = value == filter_value
        elif operation == 'contains':
            if isinstance(value, list):
                # For lists (like tags), check if filter_value is in the list
                match = filter_value in value
            else:
                match = filter_value.lower() in str(value).lower()
        elif operation == 'startswith':
            match = str(value).lower().startswith(filter_value.lower())
        elif operation == 'endswith':
            match = str(value).lower().endswith(filter_value.lower())
        elif operation == 'regex':
            match = bool(re.search(filter_value, str(value), re.IGNORECASE))
        elif operation == 'greater':
            try:
                match = float(value) > float(filter_value)
            except ValueError:
                match = str(value) > str(filter_value)
        elif operation == 'less':
            try:
                match = float(value) < float(filter_value)
            except ValueError:
                match = str(value) < str(filter_value)

        if (not match and not negate) or (match and negate):
                filtered.append(replay)

    return filtered

def main():
    parser = argparse.ArgumentParser(
        description='Melee Manager CLI - Manage Super Smash Bros. Melee replay data',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument('-o', '--out', default=DEFAULT_REPLAYS_FILE,
                       help='Replay JSON file to use (default: replays.json)')

    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # Ingest command
    ingest_parser = subparsers.add_parser('ingest', help='Fetch and ingest YouTube videos')
    ingest_parser.add_argument('source', help='YouTube channel ID or playlist ID')
    ingest_parser.add_argument('-t', '--type', choices=['channel', 'playlist'], default='channel',
                              help='Source type (default: channel)')
    ingest_parser.add_argument('-m', '--max-results', type=int, default=DEFAULT_MAX_RESULTS,
                              help=f'Maximum number of videos to fetch (default: {DEFAULT_BATCH_SIZE})')
    ingest_parser.add_argument('-b', '--batch-size', type=int, default=DEFAULT_BATCH_SIZE,
                              help=f'Number of videos to process per batch (default: {DEFAULT_BATCH_SIZE})')
    ingest_parser.add_argument('--no-parse', action='store_true',
                              help='Skip parsing video titles')
    ingest_parser.add_argument('--start-index', type=int, default=0,
                              help='Start processing from this index (useful for resuming after API limits)')
    ingest_parser.add_argument('--youtube-api-key', type=str,
                              help='YouTube API key')

    # Filter command
    filter_parser = subparsers.add_parser('filter', help='Filter replay entries')
    filter_parser.add_argument('key', help='Field to filter on')
    filter_parser.add_argument('value', help='Value to match')
    filter_parser.add_argument('-o', '--operation',
                              choices=['equals', 'contains', 'startswith', 'endswith', 'regex', 'greater', 'less'],
                              default='equals', help='Filter operation (default: equals)')
    filter_parser.add_argument('-n', '--negate', action='store_true',
                              help='Negate the filter (exclude matches)')
    filter_parser.add_argument('--dry-run', action='store_true',
                              help='Preview without saving')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    if args.command == 'ingest':
        print(f"Fetching videos from {args.type}: {args.source}")
        print(f"Batch size: {args.batch_size}, Max results: {args.max_results}")
        if args.start_index > 0:
            print(f"Starting from index: {args.start_index}")

        total_videos = 0
        total_failed = 0
        batch_number = 0
        offset = args.start_index

        while total_videos < args.max_results:
            batch_number += 1
            print(f"\nProcessing batch {batch_number} (offset: {offset})...")

            if args.type == "channel":
                videos, failed_fetches, has_more = fetch_channel_videos(
                    args.source, args.max_results, args.batch_size, offset, youtube_api_key=args.youtube_api_key
                )
            else:
                videos, failed_fetches, has_more = fetch_playlist_videos(
                    args.source, args.max_results, args.batch_size, offset, youtube_api_key=args.youtube_api_key
                )

            if failed_fetches:
                total_failed += len(failed_fetches)

            print(f"Fetched {len(videos)} videos in batch {batch_number}")
            if videos:

                with open(args.out, 'r') as f:
                    processed_videos_file = json.loads(f.read())
                processed_videos_file.extend(videos)
                with open(args.out, 'w') as f:
                    f.write(json.dumps(processed_videos_file, indent=4))
                print(f"Saved batch {batch_number} to {args.out}")

                total_videos += len(videos)
                offset += len(videos)

            if not has_more or len(videos) == 0:
                print("\nNo more videos to fetch")
                break

        print(f"\nIngestion complete:")
        print(f"Total videos processed: {total_videos}")
        print(f"Total failed: {total_failed}")

    elif args.command == 'filter':
        with open(args.out, 'r') as f:
            videos = json.loads(f.read())
        filtered_videos = filter_replays(videos, args.key, args.value, args.operation, args.negate)
        print(f"Filtered to {len(filtered_videos)} replays")
        if not args.dry_run:
            with open(args.out, 'w') as f:
                f.write(json.dumps(filtered_videos, indent=4))

if __name__ == "__main__":
    main()
