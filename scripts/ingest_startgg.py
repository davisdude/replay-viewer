import argparse
import datetime
import json
import pprint
import re
import requests
import sys

from pytubefix import Playlist
from typing import cast
from zoneinfo import ZoneInfo

import startgg_gql

id_to_character = {
    1: "Bowser",
    2: "Captain Falcon",
    3: "Donkey Kong",
    4: "Dr. Mario",
    5: "Falco",
    6: "Fox",
    7: "Ganondorf",
    8: "Ice Climbers",
    9: "Jigglypuff",
    10: "Kirby",
    11: "Link",
    12: "Luigi",
    13: "Mario",
    14: "Marth",
    15: "Mewtwo",
    16: "Mr. Game & Watch",
    17: "Ness",
    18: "Peach",
    19: "Pichu",
    20: "Pikachu",
    21: "Roy",
    22: "Samus",
    23: "Sheik",
    24: "Yoshi",
    25: "Young Link",
    26: "Zelda",
    628: "Sheik / Zelda",
    1744: "Random Character"
}

def get_youtube_id_from_url(url: str):
    match = re.search(r"(youtu.be/|youtube.com/watch\?v=)(?P<id>.{11})", url)
    if not match:
        return None
    return match.group("id")

def get_vod_data(set_obj, tournament_name: str, date: str, video_url: str):
    if (len(set_obj["entrant_1_gamer_tags"]) != 1 or len(set_obj["entrant_2_gamer_tags"]) != 1):
        return None

    youtube_id = get_youtube_id_from_url(video_url)
    entrant_1_characters: list[str] = []
    for character_id in set_obj["entrant_1_character_ids"]:
        entrant_1_characters.append(id_to_character[character_id])
    entrant_2_characters: list[str] = []
    for character_id in set_obj["entrant_2_character_ids"]:
        entrant_2_characters.append(id_to_character[character_id])
    return {
        "youtubeId": youtube_id,
        "date": date,
        "tournament": tournament_name,
        "player1": set_obj["entrant_1_gamer_tags"][0],
        "player1Characters": entrant_1_characters,
        "player2": set_obj["entrant_2_gamer_tags"][0],
        "player2Characters": entrant_2_characters,
        "tags": [],
    }

def normalize(string: str):
    return re.sub(r'[^a-z0-9!#$%&\'+,;=@^`{}~]', '', string.lower())

def get_tournament_sets_name_and_date(slug: str, event_ids: list[int]):
    tournament_response = requests.get(f"https://api.start.gg/tournament/{slug}?expand[]=groups&expand[]=phase").json()
    if not tournament_response.get("success", True):
        print(f"Invalid request! Got message '{tournament_response['message']}'")
        return [], "", ""
    name = tournament_response["entities"]["tournament"]["name"]
    time = tournament_response["entities"]["tournament"]["startAt"]
    timezone = tournament_response["entities"]["tournament"]["timezone"]
    date = datetime.datetime.fromtimestamp(time, tz=ZoneInfo(timezone)).strftime("%Y-%m-%d")
    phase_id_to_name = {
        phase["id"]: phase["name"]
        for phase in tournament_response["entities"]["phase"]
    }
    sets = []
    for group in tournament_response["entities"]["groups"]:
        if event_ids and group["id"] not in event_ids:
            continue
        group_response = requests.get(f"https://api.start.gg/phase_group/{group["id"]}?expand[]=sets&expand[]=entrants").json()
        if "entrants" not in group_response["entities"]:
            continue
        entrant_id_to_gamer_tags = {
            entrant["id"]: [
                participant["gamerTag"]
                for participant in entrant["mutations"]["participants"].values()
            ] for entrant in group_response["entities"]["entrants"]
        }
        for set_obj in group_response["entities"].get("sets", []):
            if (set_obj["entrant1Id"] is not None and set_obj["entrant2Id"] is not None and set_obj["unreachable"] != True):
                sets.append({
                    "id": set_obj["id"],
                    "full_round_text": set_obj["fullRoundText"],
                    "phase_name": phase_id_to_name[set_obj["phaseId"]],
                    "entrant_1_gamer_tags": entrant_id_to_gamer_tags[set_obj["entrant1Id"]],
                    "entrant_2_gamer_tags": entrant_id_to_gamer_tags[set_obj["entrant2Id"]],
                    "entrant_1_character_ids": set_obj.get("entrant1CharacterIds", []),
                    "entrant_2_character_ids": set_obj.get("entrant2CharacterIds", []),
                    "vod_url": set_obj["vodUrl"]
                })
    return sets, name, date

def get_sets_vod_urls(sets: list, tournament_name: str, tournament_date: str):
    data = []
    for set_obj in sets:
        video_url = set_obj["vod_url"]
        if video_url is not None:
            vod_data = get_vod_data(set_obj, tournament_name, tournament_date, video_url)
            if vod_data is not None:
                data.append(vod_data)
    return data

def get_matching_sets(video_title: str, sets: list):
    video_title_safe = normalize(video_title)
    exact_match_sets = []
    only_tags_match_sets = []
    for set_obj in sets:
        all_gamer_tags_found = all([
            normalize(gamer_tag) in video_title_safe
            for gamer_tag in set_obj["entrant_1_gamer_tags"] + set_obj["entrant_2_gamer_tags"]
        ])
        if all_gamer_tags_found:
            full_round_text = cast(str, set_obj["full_round_text"])
            full_round_text_found = normalize(set_obj["full_round_text"]) in video_title_safe
            abbrev_round_text = "".join(re.findall('([A-Z]|[0-9])', full_round_text))
            abbrev_round_text_found = normalize(abbrev_round_text) in video_title_safe
            any_round_found = full_round_text_found or abbrev_round_text_found
            phase_name_found = normalize(set_obj["phase_name"]) in video_title_safe
            if any_round_found and phase_name_found:
                exact_match_sets.append(set_obj)
            else:
                only_tags_match_sets.append(set_obj)
    return exact_match_sets, only_tags_match_sets

def match_videos_to_sets(videos: list[tuple[str, str]], sets: list, name: str, date: str):
    data = []
    set_video_urls: list[tuple[any, str]] = []
    unmatched_videos: list[tuple[str, str]] = []

    current_videos = videos
    while len(current_videos) > 0:
        next_videos: list[tuple[str, str]] = []
        for video in current_videos:
            video_title, video_url = video
            exact_match_sets, only_tags_match_sets = get_matching_sets(video_title, sets)
            if len(exact_match_sets) == 1:
                set_video_urls.append((exact_match_sets[0], video_url))
                vod_data = get_vod_data(exact_match_sets[0], name, date, video_url)
                if vod_data is not None:
                    data.append(vod_data)
                sets.remove(exact_match_sets[0])
                print(f"matched tags, round, and phase: {video_title}")
            elif len(exact_match_sets) > 1:
                next_videos.append(video)
            elif len(only_tags_match_sets) == 1:
                set_video_urls.append((only_tags_match_sets[0], video_url))
                vod_data = get_vod_data(only_tags_match_sets[0], name, date, video_url)
                if vod_data is not None:
                    data.append(vod_data)
                sets.remove(only_tags_match_sets[0])
                print(f"matched tags: {video_title}")
            elif len(only_tags_match_sets) > 1:
                next_videos.append(video)
            else:
                unmatched_videos.append(video)
        if len(current_videos) == len(next_videos):
            print(f"videos with multiple matches: {pprint.pformat(next_videos)}")
            break
        current_videos = next_videos
    if len(unmatched_videos) > 0:
        print(f"unmatched videos: {pprint.pformat(unmatched_videos)}")
    return set_video_urls, data

def set_tournament_vod_urls(slug: str, videos: list[tuple[str, str]], api_key: str, dry_run: bool, event_ids: list[int]):
    print(f"Setting VOD URLs for {slug}")
    sets, name, date = get_tournament_sets_name_and_date(slug, event_ids)
    set_video_urls, data = match_videos_to_sets(videos, sets, name, date)

    requests = []
    for set_obj, video_url in set_video_urls:
        if (set_obj["vod_url"] is None) or (get_youtube_id_from_url(set_obj["vod_url"]) != get_youtube_id_from_url(video_url)):
            requests.append(startgg_gql.get_set_vod_request(set_obj["id"], video_url))
    original_requests_len = len(requests)
    if dry_run:
        print(f"{len(requests)} new VOD URLs matched but not set in {slug}")
    else:
        while len(requests) > 0:
            # no rate handling because you'd need 40,000 VODs to exceed
            startgg_gql.batch_set_vods(startgg_gql.get_client(api_key), requests[:500])
            requests = requests[500:]
        print(f"{original_requests_len} new VOD URLs set in {slug}")

    existing_data = get_sets_vod_urls(sets, name, date)
    print(f"{len(existing_data) + len(data) - original_requests_len} existing VOD URLs found in {slug}")
    data.extend(existing_data)
    return data

def get_tournament_vod_urls(slug: str):
    print(f"Getting VOD URLs from {slug}")
    sets, name, date = get_tournament_sets_name_and_date(slug)
    data = get_sets_vod_urls(sets, name, date)
    print(f"{len(data)} VOD URLs found in {slug}")
    return data

def process(slug: str, playlist_urls: list[str], file, api_key: str, dry_run: bool, event_ids: list[int]):
    videos: list[tuple[str, str]] = []
    for playlist_url in playlist_urls:
        print(f"Processing {playlist_url}")
        try:
            playlist = Playlist(playlist_url)
            playlist_videos = [(vid.title, vid.watch_url) for vid in playlist.videos]
            videos.extend(playlist_videos)
            print(f"{len(playlist_videos)} videos found in {playlist_url}")
        except Exception as e:
            print(f"Failed to process playlist {playlist_url}: {e}")
            sys.exit(1)

    data = []
    if len(videos) == 0:
        data.extend(get_tournament_vod_urls(slug))
    else:
        data.extend(set_tournament_vod_urls(slug, videos, api_key, dry_run, event_ids))

    json.dump(data, file, indent=2)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("slug", type=str)
    parser.add_argument("--playlist-urls", nargs="*", type=str, default=[])
    parser.add_argument("--out", type=argparse.FileType("w"), default="out.json")
    parser.add_argument("--api-key", type=str, default="")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--event-ids", nargs="*", type=int, default=[])
    args = parser.parse_args()

    process(args.slug, args.playlist_urls, args.out, args.api_key, args.dry_run, args.event_ids)
