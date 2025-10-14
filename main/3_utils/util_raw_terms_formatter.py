import os
import json
from pathlib import Path

SRC = "src_pubdictionaries"
INPUT_FILE_NAME = "terms.jsonl"
OUTPUT_FILE_NAME = "terms2.jsonl"

src_path = Path(os.path.abspath(__file__)).parent.parent.parent
input_file = src_path / "data/raw" / SRC / INPUT_FILE_NAME
output_file = src_path / "data/raw" / SRC / OUTPUT_FILE_NAME

def raw_data_formatter(input_file, output_file):
    with open(input_file, "r") as infile, open(output_file, "w") as outfile:
        for line in infile:
            data = json.loads(line)
            
            # Mandatory fields
            term = data.get("normalized_term", "[ERROR]")
            if term == "[DISCARD]":
                continue
            #xref = data.get("xref", "[ERROR]")
            xref = data.get("xref", "[ERROR]")
            term_uuid = data.get("term_uuid", "[ERROR]")
            src_uuid = data.get("src_uuid", "[ERROR]")
                
            # Optional fields
            metadata = {}

            METADATA_ORDER = ["exact_synonyms", "gsd_id", "gtc_id", "description", "definition", "glycoCT", "iupac_condensed", "classification", "is_class", "raw_term", "evidence"]

            metadata["exact_synonyms"] = data.get("exact_synonyms", [])
            #metadata["gsd_id"] = data.get("gsd_id", None)
            gtc_id_raw = data.get("gtc_id", None)
            if gtc_id_raw:
                metadata["gtc_id"] = [gtc_id_raw]
            else:
                metadata["gtc_id"] = []
            #metadata["gtc_id"] = data.get("gtc_id", [])
            #metadata["description"] = data.get("description", None)
            #metadata["definition"] = data.get("definition", None)
            #if metadata["definition"] == "":
            #    metadata["definition"] = None
            #metadata["glycoCT"] = data.get("glycoCT", None)
            metadata["iupac_condensed"] = data.get("iupac_condensed", None)
            if metadata["iupac_condensed"] == "":
                metadata["iupac_condensed"] = None
            #metadata["classification"] = data.get("code_system", None)
            metadata["raw_term"] = data.get("raw_term", None)
            #metadata["evidence"] = data.get("term_in_sentence", [])
            #metadata["publication"] = data.get("publication", [])
            #metadata["db_xref"] = data.get("term_xref", [])
            #metadata["function"] = data.get("function", [])
            #metadata["disease_association"] = data.get("disease_associations", [])
            #metadata["comment"] = data.get("comment", None)
                
            # Construct the new data structure
            new_data = {
                "term": term,
                "xref": xref,
                "term_uuid": term_uuid,
                "src_uuid": src_uuid,
                "metadata": metadata
            }

            # Write the new data structure to the output file
            outfile.write(json.dumps(new_data, ensure_ascii=False) + "\n")