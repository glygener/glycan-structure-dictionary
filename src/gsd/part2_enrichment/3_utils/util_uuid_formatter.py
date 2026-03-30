# Adds "SRC:" prefix to src_uuid and "GSD:" prefix to term_uuid if not already present
import json
def fix_uuid_prefix(input_file, output_file):
    with open(input_file, "r") as infile, open(output_file, "w") as outfile:
        for line in infile:
            data = json.loads(line)
            # Modify the data as needed
            if not data["src_uuid"].startswith("SRC:"):
                data["src_uuid"] = "SRC:" + data["src_uuid"]
            if not data["term_uuid"].startswith("GSD:"):
                data["term_uuid"] = "GSD:" + data["term_uuid"]
            if data["glycoCT"]:
                data["glycoCT"] = data["glycoCT"].replace("\\n", "\n").replace("\\r", "\r")
            outfile.write(json.dumps(data) + "\n")