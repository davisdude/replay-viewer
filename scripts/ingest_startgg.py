import argparse
import datetime
import json
import re
import time

from gql.transport.exceptions import TransportServerError

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
    chars = list(set(game["character"]["name"] for game in relevant_games))
    return name, chars

def get_vod_data(set_data, tournament_name):
    if set_data["vodUrl"] is None:
        return None
    youtube_id = get_youtube_id_from_url(set_data["vodUrl"])
    # TODO: Timezone
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

def process_url(url):
    print(f"Processing {url}")
    data = []
    slugs = get_slugs_from_url(url)
    if not slugs:
        print("Could not get slugs")
        return []
    tournament_slug, event_slug = slugs
    client = startgg_gql.get_client()
    tournament_name = startgg_gql.get_tournament_name(client, tournament_slug)
    event_id = startgg_gql.get_event_id(client, event_slug)
    set_ids = startgg_gql.get_event_set_ids(client, event_id)
    while len(set_ids):
        set_id = set_ids[-1]
        print(f"Processing set {set_id}")
        try:
            set_data = startgg_gql.get_set_data(client, set_id)
            vod_data = get_vod_data(set_data, tournament_name)
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

def process_urls(urls, file):
    data = []
    for url in urls:
        data.extend(process_url(url))
    json.dump(data, file, indent=2)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("urls", nargs="+", type=str)
    parser.add_argument("--out", type=argparse.FileType("w"), default="out.json")
    args = parser.parse_args()

    process_urls(args.urls, args.out)
