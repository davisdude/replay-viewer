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

def get_vod_data(set, tournament_name: str, date: str, video_url: str):
    if (len(set["entrant_1_gamer_tags"]) != 1 or len(set["entrant_2_gamer_tags"]) != 1):
        return None

    youtube_id = get_youtube_id_from_url(video_url)
    entrant_1_characters: list[str] = []
    for character_id in set["entrant_1_character_ids"]:
        entrant_1_characters.append(id_to_character[character_id])
    entrant_2_characters: list[str] = []
    for character_id in set["entrant_2_character_ids"]:
        entrant_2_characters.append(id_to_character[character_id])
    return {
        "youtubeId": youtube_id,
        "date": date,
        "tournament": tournament_name,
        "player1": set["entrant_1_gamer_tags"][0],
        "player1Characters": entrant_1_characters,
        "player2": set["entrant_2_gamer_tags"][0],
        "player2Characters": entrant_2_characters,
        "tags": [],
    }

def normalize(string: str):
    return re.sub(r'[^a-z0-9]', '', string.lower())

def get_tournament_name_sets_and_timezone(slug: str):
    tournament_response = requests.get(f"https://api.start.gg/tournament/{slug}?expand[]=groups&expand[]=phase").json()
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
        group_response = requests.get(f"https://api.start.gg/phase_group/{group["id"]}?expand[]=sets&expand[]=entrants").json()
        entrant_id_to_gamer_tags = {
            entrant["id"]: [
                participant["gamerTag"]
                for participant in entrant["mutations"]["participants"].values()
            ] for entrant in group_response["entities"]["entrants"]
        }
        for setObj in group_response["entities"]["sets"]:
            if (setObj["entrant1Id"] is not None and setObj["entrant2Id"] is not None and setObj["unreachable"] != True):
                sets.append({
                    "id": setObj["id"],
                    "full_round_text": setObj["fullRoundText"],
                    "phase_name": phase_id_to_name[setObj["phaseId"]],
                    "entrant_1_gamer_tags": entrant_id_to_gamer_tags[setObj["entrant1Id"]],
                    "entrant_2_gamer_tags": entrant_id_to_gamer_tags[setObj["entrant2Id"]],
                    "entrant_1_character_ids": setObj.get("entrant1CharacterIds", []),
                    "entrant_2_character_ids": setObj.get("entrant2CharacterIds", []),
                })
    return name, sets, date

def process_tournament(slug: str, playlist_urls: list[tuple[str, str]], api_key: str):
    print(f"Processing {slug}")
    data = []
    name, sets, date = get_tournament_name_sets_and_timezone(slug)

    set_id_to_video_url = dict[str, str]()
    current_playlist_urls = playlist_urls
    unmatched_playlist_urls = []
    while len(current_playlist_urls):
        next_playlist_urls: list[tuple[str, str]] = []
        for playlist_url in current_playlist_urls:
            if playlist_url is None:
                continue
            video_title, video_url = playlist_url
            video_title_safe = normalize(video_title)
            exact_matching_sets = []
            matching_sets = []
            for setObj in sets:
                all_gamer_tags_found = all([
                    normalize(gamer_tag) in video_title_safe
                    for gamer_tag in setObj["entrant_1_gamer_tags"] + setObj["entrant_2_gamer_tags"]
                ])
                if all_gamer_tags_found:
                    full_round_text = cast(str, setObj["full_round_text"])
                    full_round_text_found = normalize(setObj["full_round_text"]) in video_title_safe
                    abbrev_round_text = "".join(re.findall('([A-Z]|[0-9])', full_round_text))
                    abbrev_round_text_found = normalize(abbrev_round_text) in video_title_safe
                    any_round_found = full_round_text_found or abbrev_round_text_found
                    phase_name_found = normalize(setObj["phase_name"]) in video_title_safe
                    if any_round_found and phase_name_found:
                        exact_matching_sets.append(setObj)
                    else:
                        matching_sets.append(setObj)
            if len(exact_matching_sets) == 1:
                set_id_to_video_url[exact_matching_sets[0]["id"]] = video_url
                vod_data = get_vod_data(exact_matching_sets[0], name, date, video_url)
                if vod_data is not None:
                    data.append(vod_data)
                sets.remove(exact_matching_sets[0])
                print(f"matched exactly: {video_title}")
            elif len(exact_matching_sets) > 1:
                next_playlist_urls.append(playlist_url)
            elif len(matching_sets) == 1:
                set_id_to_video_url[matching_sets[0]["id"]] = video_url
                vod_data = get_vod_data(matching_sets[0], name, date, video_url)
                if vod_data is not None:
                    data.append(vod_data)
                sets.remove(matching_sets[0])
                print(f"matched: {video_title}")
            elif len(matching_sets) > 1:
                next_playlist_urls.append(playlist_url)
            else:
                unmatched_playlist_urls.append(playlist_url)
        if len(current_playlist_urls) == len(next_playlist_urls):
            print(f"videos with multiple matches: {pprint.pformat(next_playlist_urls)}")
            break
        current_playlist_urls = next_playlist_urls
    if len(unmatched_playlist_urls) > 0:
        print(f"unmatched videos: {pprint.pformat(unmatched_playlist_urls)}")
    requests = []
    for set_id in set_id_to_video_url:
        requests.append(startgg_gql.get_set_vod_request(set_id, set_id_to_video_url[set_id]))
    startgg_gql.batch_set_vods(startgg_gql.get_client(api_key), requests=requests)
    return data

def process_urls(slug: str, playlist_urls: list[str], file, api_key: str):
    if len(playlist_urls) == 0:
        print("Not enough playlist URLs!")
        sys.exit(1)

    for i, playlist_url in enumerate(playlist_urls):
        if not playlist_url:
            playlist_urls[i] = []
            continue
        print(f"Processing {playlist_url}")
        try:
            playlist = Playlist(playlist_url)
            playlist_urls[i] = [(vid.title, vid.watch_url) for vid in playlist.videos]
            print(f"{len(playlist_urls[i])} videos found in {playlist_url}")
        except Exception as e:
            print(f"Failed to process playlist {playlist_url}: {e}")
            sys.exit(1)

    data = []
    for playlist_url in playlist_urls:
        data.extend(process_tournament(slug, playlist_url, api_key))

    json.dump(data, file, indent=2)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("slug", type=str)
    parser.add_argument("--playlist-urls", nargs="*", type=str, default=[[]])
    parser.add_argument("--out", type=argparse.FileType("w"), default="out.json")
    parser.add_argument("--api_key", type=str)
    args = parser.parse_args()

    process_urls(args.slug, args.playlist_urls, args.out, args.api_key)
