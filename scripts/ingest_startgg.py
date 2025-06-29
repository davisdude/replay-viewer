import argparse
import datetime
import json
import re
import sys

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

def get_game_selection_data(set_data):
    participant_ids = list(set(
        selection["entrant"]["id"]
        for game in set_data["games"]
        for selection in game["selections"]
    ))
    player_1_name = list(set([
        selection["entrant"]["participants"][0]["gamerTag"]
        for game in set_data["games"]
        for selection in game["selections"]
        if selection["entrant"]["id"] == participant_ids[0]
    ]))
    player_2_name = list(set([
        selection["entrant"]["participants"][0]["gamerTag"]
        for game in set_data["games"]
        for selection in game["selections"]
        if selection["entrant"]["id"] == participant_ids[1]
    ]))
    if (len(participant_ids) > 2) or (len(player_1_name) > 1) or (len(player_2_name) > 1):
        return None
    player_1_chars = list(set([
        selection["character"]["name"]
        for game in set_data["games"]
        for selection in game["selections"]
        if selection["entrant"]["id"] == participant_ids[0]
    ]))
    player_2_chars = list(set([
        selection["character"]["name"]
        for game in set_data["games"]
        for selection in game["selections"]
        if selection["entrant"]["id"] == participant_ids[1]
    ]))
    return player_1_name[0], player_1_chars, player_2_name[0], player_2_chars

def get_vod_data(set_data, tournament_name):
    if set_data["vodUrl"] is None:
        return None
    youtube_id = get_youtube_id_from_url(set_data["vodUrl"])
    date = datetime.datetime.fromtimestamp(set_data["completedAt"], datetime.UTC).strftime("%Y-%m-%d")
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
        data = get_game_selection_data(set_data)
        if data is None:
            print(f"Invalid data for set id {set_data['id']}")
            return None
        player_1_name, player_1_chars, player_2_name, player_2_chars = data
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

def get_data(url):
    data = []

    slugs = get_slugs_from_url(url)
    if not slugs:
        print("Could not get slugs")
        return []
    tournament_slug, event_slug = slugs

    with startgg_gql.get_client() as session:
        tournament_name = startgg_gql.get_tournament_name(session, tournament_slug)
        event_id = startgg_gql.get_event_id(session, event_slug)
        sets = startgg_gql.get_event_sets(session, event_id)
        for set_data in sets:
            set_id = set_data["id"]
            set_data = startgg_gql.get_set_data(session, set_id)
            vod_data = get_vod_data(set_data, tournament_name)
            if vod_data:
                vod_data["id"] = len(data)
                data.append(vod_data)

    return data

def process_urls(urls, file):
    data = []
    for url in urls:
        data.extend(get_data(url))
    json.dump(data, file, indent=4)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("urls", nargs="+", type=str)
    parser.add_argument("--out", type=argparse.FileType("w"), default="out.json")
    args = parser.parse_args()

    process_urls(args.urls, args.out)
