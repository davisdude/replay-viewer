import argparse
import json

def merge_json(parent_data, child_data):
    ids = [vod["id"] for vod in parent_data]
    max_id = max(ids)
    parent_data = {vod["youtubeId"]: vod for vod in parent_data}
    for child_vod in child_data:
        yt_id = child_vod["youtubeId"]
        if yt_id not in parent_data:
            print(f"Found a new video: {yt_id}")
            parent_data[yt_id] = {"id": max_id}
            max_id += 1
        parent_vod = parent_data[yt_id]
        # TODO: This doesn't properly account for tag differences (non-swaps)
        ##manual_items = ["player1", "player2"]
        ## Swaps players/characters to match start.gg data
        #if (
        #        (("player1" in parent_vod) and ("player2" in parent_vod))
        #    and (child_vod["player1"] != parent_vod["player1"])
        #):
        #    tmp_characters = child_vod["player2Characters"] or parent_vod["player1Characters"]
        #    parent_vod["player1"] = child_vod["player1"]
        #    parent_vod["player2"] = child_vod["player2"]
        #    parent_vod["player1Characters"] = child_vod["player1Characters"] or parent_vod["player2Characters"]
        #    parent_vod["player2Characters"] = tmp_characters
        #else:
        #    for item in manual_items:
        #        parent_vod[item] = child_vod[item]
        for k, v in child_vod.items():
            if k == "id":
                continue
            if not v:
                continue
            #if k in manual_items:
            #    continue
            parent_vod[k] = v
    return list(parent_data.values())

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("parent", type=argparse.FileType("r"))
    parser.add_argument("child", type=argparse.FileType("r"))
    parser.add_argument("out", type=argparse.FileType("w"))

    args = parser.parse_args()
    parent_data = json.load(args.parent)
    child_data = json.load(args.child)

    new_data = merge_json(parent_data, child_data)
    json.dump(new_data, args.out, indent=2)
