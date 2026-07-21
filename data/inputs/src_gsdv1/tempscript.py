import json

with open("/home/cyruschauyeung/projects/glycan-structure-dictionary/data/raw/src_gsdv0/terms.jsonl", "r", encoding="utf-8") as f:
    gsd_count = 0
    gsd_list = []
    for line in f:
        data = json.loads(line)
        gsd_id = data["metadata"].get("gsd_id")
        if gsd_id:
            gsd_count += 1
            gsd_list.append(int(gsd_id[3:]))
print(sorted(gsd_list))
print(gsd_count)

        