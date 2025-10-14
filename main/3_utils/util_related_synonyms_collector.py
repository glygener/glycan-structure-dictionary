import json

def get_related_synonyms(input_file, output_file):
    with open(input_file, "r") as infile, open(output_file, "w") as outfile:
        xref = "SRC:GLYGEN_CURATORS"
        
        # Create mapping dict
        synonym_dict = {}
        for line in infile:
            data = json.loads(line)
            term = data.get("term", "[ERROR]")
            term_uuid = data.get("term_uuid", "[ERROR]")
            synonym_dict[term] = term_uuid
        infile.seek(0)
   
        # Reiterate, map related_synonyms to term_uuid         
        edge_json = {"subj": "", "pred": "has_related_synonym", "obj": "", "xref": xref, "comment": ""}
        for line in infile:
            data = json.loads(line)
            related_synonym = data.get("related_synonyms", "") # This is taking in string although related_synonyms is plural
            term_uuid = data.get("term_uuid", "")
            if related_synonym != None and related_synonym != "":
                try:
                    edge_json["subj"] = synonym_dict[related_synonym]
                except KeyError:
                    edge_json["subj"] = "[PLACEHOLDER]"
                
                edge_json["obj"] = data.get("term_uuid", "")

                str_subj = related_synonym
                str_obj = data.get("term", "[ERROR]")
                edge_json["comment"] = f"{str_subj} has a related synonym of {str_obj}" # Human-readable comment, subj and obj term names may not be updated in changes.
                
                # Write to file if related_synonym found
                outfile.write(json.dumps(edge_json, ensure_ascii = False) + "\n")
