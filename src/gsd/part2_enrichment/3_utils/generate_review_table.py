import csv
import json
from pathlib import Path

MASTER_NODE_FILENAME = "master_nodes_20260202_154204.json"
MASTER_NODE_PATH = Path(__file__).parents[2] / "data" / "processed" / MASTER_NODE_FILENAME

OUTPUT_FILENAME = "review_table.csv"
OUTPUT_PATH = Path(__file__).parents[2] / "data" / "processed" / OUTPUT_FILENAME

with open(MASTER_NODE_PATH, "r", encoding="utf-8") as f:
    data = json.load(f)

with open(OUTPUT_PATH, "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["lbl", "gsd_id"])
    new_count = 0
    for item in data:
        lbl = item.get("lbl")
        gsd_id = item.get("gsd_id")
        if gsd_id:
            new_count += 1
        else:
            gsd_id = "None"
        writer.writerow([lbl, gsd_id])
        
print(new_count)
        


