import json
import urllib.parse

def create_hyperlinks(input_jsonl, output_jsonl) -> None:
    """Create hyperlinks pointing to sentence-level evidence for each record in the input JSONL file and save to output JSONL file."""

    prefix = "https://www.ncbi.nlm.nih.gov/books/n/glyco4/"

    with open(input_jsonl, "r") as f:
        for line in f:
            data = json.loads(line)
            
            uid = data["metadata"]["id"]
            chapter = data["metadata"]["chapter"]
            
            char_len = len(data["content"])
            start_str = data["content"][:35]
            start_space = start_str.rfind(" ")
            end_str = data["content"][(char_len-36):]
            end_space = end_str.find(" ") + 1

            start_str = urllib.parse.quote(start_str[:start_space])
            end_str = urllib.parse.quote(end_str[end_space:])
            end_str = end_str[:-1] if end_str.endswith(".") else end_str

            hyperlink = prefix + chapter + "/#:~:text=" + start_str + "," + end_str

            new_data = {"id": uid, "hyperlink": hyperlink}

            with open(output_jsonl, "a") as out_f:
                json.dump(new_data, out_f, ensure_ascii=False)
                out_f.write("\n")
    return None


from uuid import uuid4
def generate_uuid():
    return str(uuid4())