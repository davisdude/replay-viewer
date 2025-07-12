import argparse
import datetime
import json
import pprint
import re
import sys
import time

from gql.transport.exceptions import TransportServerError
from pytubefix import Playlist

import startgg_gql

def get_youtube_id_from_url(url):
    match = re.search(r"(youtu.be/|youtube.com/watch\?v=)(?P<id>.{11})", url)
    if not match:
        return None
    return match.group("id")

def get_slugs_from_url(url):
    match = re.search(r"start.gg/(?P<event>(?P<tournament>tournament/([^/]+))/event/[^/]+?)(/|$)", url)
    if not match:
        return None
    return match.group("tournament"), match.group("event")

def get_relevant_games(set_data, entrant_id):
    # Drop irrelevant / missing data
    return [
        selection
        for game in set_data["games"]
        if (game["selections"] is not None)
        for selection in game["selections"]
        if (selection["entrant"]["id"] == entrant_id)
    ]


def get_game_selection_data(set_data, entrant_id):
    relevant_games = get_relevant_games(set_data, entrant_id)
    if len(relevant_games) == 0:
        return None
    name = relevant_games[0]["entrant"]["participants"][0]["gamerTag"]
    # Use dict to preserve order
    chars = {game["character"]["name"]: True for game in relevant_games}
    return name, list(dict.fromkeys(chars))

def get_vod_data(set_data, tournament_name, zone_info):
    if set_data["vodUrl"] is None:
        return None
    youtube_id = get_youtube_id_from_url(set_data["vodUrl"])
    time = set_data["startAt"] or set_data["startedAt"] or set_data["createdAt"]
    date = datetime.datetime.fromtimestamp(time, tz=zone_info).strftime("%Y-%m-%d")
    if not youtube_id:
        print(f"Unsupported URL '{set_data['vodUrl']}' for set id {set_data['id']}")
        return None
    if len(set_data["slots"]) != 2:
        print(f"Unsupported format for set id {set_data['id']}")
        return None
    if len(set_data["slots"][0]["entrant"]["participants"]) != 1:
        print(f"Unsupported format for set id {set_data['id']}")
        return None
    player_1_name = set_data["slots"][0]["entrant"]["participants"][0]["gamerTag"]
    player_2_name = set_data["slots"][1]["entrant"]["participants"][0]["gamerTag"]
    player_1_chars = []
    player_2_chars = []
    if set_data["games"] is not None:
        player_1_data = get_game_selection_data(set_data, set_data["slots"][0]["entrant"]["id"])
        player_2_data = get_game_selection_data(set_data, set_data["slots"][1]["entrant"]["id"])
        if player_1_data is not None:
            player_1_name, player_1_chars = player_1_data
        if player_2_data is not None:
            player_2_name, player_2_chars = player_2_data
    return {
        "youtubeId": youtube_id,
        "date": date,
        "tournament": tournament_name,
        "player1": player_1_name,
        "player1Characters": player_1_chars,
        "player2": player_2_name,
        "player2Characters": player_2_chars,
        "tags": [],
    }

def normalize(string):
    return re.sub(r'[^a-z0-9]', '', string.lower())

def find_matching_youtube_video(set_data, playlist_urls):
    if not set_data["slots"][0]["entrant"]:
        return None
    if not set_data["slots"][1]["entrant"]:
        return None
    player1 = set_data["slots"][0]["entrant"]["participants"][0]["gamerTag"]
    player2 = set_data["slots"][1]["entrant"]["participants"][0]["gamerTag"]
    round_text = set_data["fullRoundText"]
    p1_safe_name = normalize(player1)
    p2_safe_name = normalize(player2)
    match_url = None
    url_indices_to_remove = []
    for video_index, video_data in enumerate(playlist_urls):
        if video_data is None:
            continue
        video_title, video_url = video_data
        video_title_safe = normalize(video_title)
        if (p1_safe_name in video_title_safe) and (p2_safe_name in video_title_safe):
            # Prompts for input
            print(f"Found potential match for '{player1}' vs '{player2}' ({round_text}): {video_title}")
            prompt = input("Use? (y/n/remove): ")
            if prompt.lower().startswith("y"):
                match_url = video_url
                url_indices_to_remove.append(video_index)
                break
            elif prompt.lower().startswith("r"):
                url_indices_to_remove.append(video_index)
    for url_index in sorted(url_indices_to_remove, reverse=True):
        del playlist_urls[url_index]
    return match_url

def process_event(startgg_url, playlist_urls):
    print(f"Processing {startgg_url}")
    data = []
    slugs = get_slugs_from_url(startgg_url)
    if not slugs:
        print("Could not get slugs")
        return []
    tournament_slug, event_slug = slugs
    client = startgg_gql.get_client()
    tournament_name, timezone = startgg_gql.get_tournament_name_and_timezone(client, tournament_slug)
    event_id = startgg_gql.get_event_id(client, event_slug)
    set_ids = startgg_gql.get_event_set_ids(client, event_id)
    while len(set_ids):
        set_id = set_ids[-1]
        print(f"Processing set {set_id}")
        try:
            set_data = startgg_gql.get_set_data(client, set_id)
            vod_data = get_vod_data(set_data, tournament_name, timezone)
            if not vod_data:
                # Try to get video from playlist
                url = find_matching_youtube_video(set_data, playlist_urls)
                if url:
                    set_data["vodUrl"] = url
                    vod_data = get_vod_data(set_data, tournament_name, timezone)
                    try:
                        startgg_gql.set_vod(client, set_id, url)
                    except Exception as e:
                        print(f"Failed to assign video: {e}")
            if vod_data:
                vod_data["id"] = len(data)
                data.append(vod_data)
            set_ids.pop()
        except TransportServerError as err:
            if err.code == 429:
                print("Too many requests; taking a nap")
                print("(You shouldn't see this if you're limiting reqs properly)")
                client = startgg_gql.get_client()
                time.sleep(10)
            else:
                raise
    return data

def process_urls(startgg_urls, playlist_urls, file):
    if len(playlist_urls) == 0:
        playlist_urls = [[None]] * len(startgg_urls)
    elif len(startgg_urls) != len(startgg_urls):
        print("Not enough playlist URLs!")
        sys.exit(1)

    for i, playlist_url in enumerate(playlist_urls):
        if not playlist_url:
            playlist_urls[i] = []
            continue
        try:
            playlist = Playlist(playlist_url)
            playlist_urls[i] = [(vid.title, vid.watch_url) for vid in playlist.videos]
        except Exception as e:
            print(f"Failed to process playlist '{playlist_url}': {e}")
            sys.exit(1)

    data = []
    for startgg_url, playlist_url in zip(startgg_urls, playlist_urls):
        data.extend(process_event(startgg_url, playlist_url))
        if playlist_url:
            print(f"Warning - videos left in playlist: {pprint.pformat(playlist_url)}")

    json.dump(data, file, indent=2)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("startgg_urls", nargs="+", type=str)
    parser.add_argument("--playlist-urls", nargs="*", type=str, default=[[]])
    parser.add_argument("--out", type=argparse.FileType("w"), default="out.json")
    args = parser.parse_args()

    process_urls(args.startgg_urls, args.playlist_urls, args.out)
