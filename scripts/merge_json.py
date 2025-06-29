import argparse
import json

def merge_json(parent_data, child_data):
    ids = [vod["id"] for vod in parent_data]
    max_id = max(ids)
    parent_data = {vod["youtubeId"]: vod for vod in parent_data}
    for child_vod in child_data:
        for k, v in child_vod.items():
            if k == "id":
                continue
            yt_id = child_vod["youtubeId"]
            if yt_id not in parent_data:
                print(f"Found a new video: {yt_id}")
                parent_data[yt_id] = {"id": max_id}
                max_id += 1
            parent_data[yt_id][k] = v
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
