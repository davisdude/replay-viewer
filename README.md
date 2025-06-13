# Melee Replay Viewer

A clean, modular Super Smash Bros. Melee replay viewer component that can be easily integrated into any website.

## Quick Start

1. **Copy the files** to your website directory:
   - `index.html` - Basic HTML structure
   - `replay-viewer.js` - Core functionality
   - `styles.css` - Styling

2. **Prepare your data**: Create a `replays.json` file with your replay data in this format:
  ```json
  [
    {
      "id": 1011,
      "tournament": "Gar 27",
      "date": "2025-02-20",
      "player1": "Nak",
      "player1Characters": [
          "Sheik"
      ],
      "player2": "STUNNER VETERAN",
      "player2Characters": [
          "Fox"
      ],
      "youtubeId": "pvt4NXXbgsQ",
      "replayType": "full"
    },
    {
      "id": 8519,
      "youtubeId": "mspu7IosVPU",
      "date": "2021-10-08",
      "tournament": "Arcade Legacy",
      "player1": "agave",
      "player1Characters": [],
      "player2": "stripes",
      "player2Characters": [],
      "replayType": "timestamp",
      "timestamp": 616
    },
  ]
  ```

3. **Optional**: Create an `aliases.json` file for player name variations:
  ```json
  {
    "mango": ["mango", "c9mango", "cloud9mango"],
    "armada": ["armada", "alliance.armada"]
  }
  ```

4. **Testing**: Start up a local web server in your project directory to test. Try:
  ```python
  python -m http.server 8080
  ```

  Then open http://localhost:8080/index.html in your browser.


## Integration Guide

### As a Standalone Page
Simply use the provided `index.html` file as-is.

### Integrating into Existing Sites

1. **Copy the main container** from `index.html`:
  ```html
  <div id="melee-replay-viewer" class="replay-viewer-container">
    <!-- Search Section -->
    <div class="replay-search">
        <input
            type="text"
            id="replaySearch"
            class="replay-search-input"
            placeholder="Search players, characters, tournaments..."
        >
        <button id="searchButton" class="replay-search-button">Search</button>
    </div>

    <!-- Results Section -->
    <div id="replaysResults" class="replay-results">
        <div class="loading-message" style="display: none;">Loading replays...</div>
        <div class="no-results-message" style="display: none;">No matches found</div>
        <!-- Replay items will be dynamically inserted here -->
    </div>

    <!-- Pagination -->
    <div id="pagination" class="replay-pagination"></div>
</div>
  ```

2. **Include the CSS and JavaScript**:
  ```html
  <link rel="stylesheet" href="path/to/styles.css">
  <script src="path/to/replay-viewer.js"></script>
  ```

3. **Adjust data paths** in `replay-viewer.js` if needed:
  ```javascript
  const config = {
    pageSize: 10,
    dataUrl: 'path/to/your/replays.json',
    aliasesUrl: 'path/to/your/aliases.json'
  };
  ```

## Data Format

### Replays JSON Structure
```json
[
  {
    "id": int,
    "player1": "Player 1 Name",
    "player2": "Player 2 Name",
    "player1Character": ["Character1", "Character2"],
    "player2Character": ["Character1"],
    "tournament": "Tournament Name",
    "youtubeId": "YouTube Video ID",
    "uploadDate": "YYYY-MM-DD",
    "replayType": "full | timestamp",
    "timestamp": int
  }
]
```

- id: unique integer
- player1: tag for player 1
- player2: tag for player 2
- player1Character: array of strings representing characters for player 1. These strings need to match the mapping in replay-viewer.js
- player2Character: array of strings representing characters for player 2. These strings need to match the mapping in replay-viewer.js
- tournament: name of the tournament
- youtubeId: ID of the YouTube video (the text that comes after ?v= in https://www.youtube.com/watch?v=dQw4w9WgXcQ)
- uploadDate: date of the set/upload
- replayType: full if the video is the whole set, timestamp if it's coming from a longer VOD
- timestamp: the timestamp to jump to if the replay is from a longer VOD

### Ingesting data

1. **YouTube Data API**:
You'll need a [YouTube Data API key](https://developers.google.com/youtube/v3/getting-started) to get started.
Then, you'll pull down the uploads from a channel or playlist. To get the channel ID easily, go to a channel,
open up the developer console, then search the page source for "og:url". I'd recommend pulling down the video
tags as well, since sometimes VODs will have important info there that can help you filter out non-Melee VODs
or find the tournament name.

2. **Conversion to data format**:
When you're ingesting a bunch of old VODs with different naming conventions, this can be tricky.
I'd recommend grabbing all the uploads from the channel/playlist you're ingesting from and transforming them
into some basic format. There is a script in this repo called ingest.py that can help with this:

#### Using ingest.py

The ingest.py script fetches YouTube video metadata from channels or playlists and manages replay data.

Prerequisites

- Set the YOUTUBE_API_KEY environment variable or pass it via --youtube-api-key
- Install dependencies: pip install -r requirements.txt

Commands

Ingest videos from YouTube:
#### Fetch videos from a channel
python ingest.py ingest CHANNEL_ID

#### Fetch videos from a playlist
python ingest.py ingest PLAYLIST_ID -t playlist

#### Resume from a specific index (useful after API limits)
python ingest.py ingest CHANNEL_ID --start-index 500

#### Customize batch size and max results
python ingest.py ingest CHANNEL_ID -b 100 -m 1000

Filter replay data:
#### Filter by exact match
python ingest.py filter channelId "UC123ABC"

#### Filter with operations (equals, contains, startswith, endswith, regex, greater, less)
python ingest.py filter tags "tournament" -o contains

#### Exclude matches with --negate
python ingest.py filter date "2024" -o startswith -n

#### Preview changes without saving
python ingest.py filter originalTitle "Grand Finals" -o contains --dry-run

All commands save to replays.json by default. Use -o filename.json to specify a different file.

3. **Add to existing data**:
Once you merge new data into the existing replays.json, make sure to index properly so each entry
has a unique ID.

## Hosting your website

Since everything is stored client-side, I'd recommend using either GitHub Pages or [hosting a static website on Google Cloud](https://cloud.google.com/storage/docs/hosting-static-website).

## License

[MIT](https://choosealicense.com/licenses/mit/)
