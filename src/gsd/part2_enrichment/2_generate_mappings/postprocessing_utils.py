from pathlib import Path
import json


def backup_existing_file(SRC_DIR: Path) -> None:   
    """Backs up all existing JSON files in the processed directory by moving them to backup/"""
    PRC_DIR = SRC_DIR / "data" / "processed"
    BCK_DIR = SRC_DIR / "data" / "processed" / "backup"

    BCK_DIR.mkdir(parents=True, exist_ok=True)

    # Move all JSON files in processed directory to backup
    json_files = list(PRC_DIR.glob("*.json"))
    
    if json_files:
        for json_file in json_files:
            backup_name = json_file.name
            backup_path = BCK_DIR / backup_name
            json_file.rename(backup_path)
            print(f"- Backed up {json_file.name} to {BCK_DIR.name}/{backup_name}")
    
    return None
        
        
def create_processing_queue(PROCESSING_ORDER, RAW_DIR) -> list:
    """Creates a processing queue based on the defined order and available term/edge files.

    Looks for:
      - terms.jsonl OR terms_resolved.jsonl (graph.py output) in each source dir
      - edges.jsonl AND edges_ai-decisions.jsonl (graph.py output) in each source dir
    Prefers terms_resolved.jsonl over terms.jsonl when both exist for non-seed sources.
    """
    print("\n" + "="*80 + "\nCreating processing queue...")
    processing_queue_terms = []
    processing_queue_edges = []

    for source in PROCESSING_ORDER:
        source_dir = RAW_DIR / source
        if not source_dir.is_dir():
            print(f"- {source}: directory not found, skipping")
            continue

        print(f"- {source}: ", end="")

        # Terms: prefer terms_resolved.jsonl (output of graph.py) for non-seed sources
        resolved = source_dir / "terms_resolved.jsonl"
        standard = source_dir / "terms.jsonl"
        if resolved.exists():
            print(f"{resolved.name}  ", end="")
            processing_queue_terms.append(resolved)
        elif standard.exists():
            print(f"{standard.name}  ", end="")
            processing_queue_terms.append(standard)

        # Edges: collect both manual edges and AI-generated edges
        for edge_file in sorted(source_dir.glob("*edges*.jsonl")):
            if "archive" in str(edge_file):
                continue
            print(f"{edge_file.name}  ", end="")
            processing_queue_edges.append(edge_file)

        print("")

    print(f"\nTotal term files: {len(processing_queue_terms)}")
    print(f"Total edge files: {len(processing_queue_edges)}")
    return processing_queue_terms, processing_queue_edges

def quality_check_jsonl_files(processing_queue_terms, processing_queue_edges, MANDATORY_FIELDS_TERMS, MANDATORY_FIELDS_EDGES) -> None:
    # terms.jsonl
    print("\n" + "="*80 + "\nRunning pre-merge quality check...")
    seen_src_uuids = []
    for term_file in processing_queue_terms:
        seen_term_uuids = []
        with open(term_file, "r") as f:
            for index, line in enumerate(f):
                try:
                    data = json.loads(line)
                except json.JSONDecodeError as e:
                    print(f"[Error] JSONDecodeError in {term_file.parent.name}/{term_file.name}: {e}; line {index + 1}")
                    quit()
                
                mandatory_fields = MANDATORY_FIELDS_TERMS
                for field in mandatory_fields:
                    if field not in data:
                        print(f"[Error] Missing mandatory field '{field}' in {term_file.parent.name}/{term_file.name}; line {index + 1}")
                        quit()
                
                term_uuid = data["term_uuid"]
                if term_uuid.startswith("GSD:") == False:
                    print(f"[Error] term_uuid '{term_uuid}' does not start with 'GSD:' in {term_file.parent.name}/{term_file.name}; line {index + 1}")
                    quit()
                # NOTE: duplicate term_uuid WITHIN a file is allowed — the resolver
                # may map multiple surface forms in a single source to the same
                # canonical term, and postprocessing collects each row as a
                # separate `sources[]` entry on the merged node. So we only track
                # the count here (no error).
                seen_term_uuids.append(term_uuid)
                
                src_uuid = data["src_uuid"]
                if src_uuid.startswith("SRC:") == False:
                    print(f"[Error] src_uuid '{src_uuid}' does not start with 'SRC:' in {term_file.parent.name}/{term_file.name}; line {index + 1}")
                    quit()
                if src_uuid in seen_src_uuids:
                    print(f"[Error] Duplicate src_uuid '{src_uuid}' in {term_file.parent.name}/{term_file.name}; line {index + 1}")
                    quit()
                else:
                    seen_src_uuids.append(src_uuid)
            print(f"[PASS] QC of {term_file.parent.name}/{term_file.name} - Lines: {index + 1}")
            
    # edges.jsonl
    print("-"*80)
    for edge_file in processing_queue_edges:
        with open(edge_file, "r") as f:
            for index, line in enumerate(f):
                try:
                    data = json.loads(line)
                except json.JSONDecodeError as e:
                    print(f"[Error] JSONDecodeError in {edge_file.parent.name}/{edge_file.name}: {e}; line {index + 1}")
                    quit()
                
                mandatory_fields = MANDATORY_FIELDS_EDGES
                for field in mandatory_fields:
                    if field not in data:
                        print(f"[Error] Missing mandatory field '{field}' in {edge_file.parent.name}/{edge_file.name}; line {index + 1}")
                        quit()
                
                subj = data["subj"]
                if subj.startswith("GSD:") == False:
                    print(f"[Error] subj '{subj}' does not start with 'GSD:' in {edge_file.parent.name}/{edge_file.name}; line {index + 1}")
                    quit()
                
                obj = data["obj"]
                if obj.startswith("GSD:") == False:
                    print(f"[Error] obj '{obj}' does not start with 'GSD:' in {edge_file.parent.name}/{edge_file.name}; line {index + 1}")
                    quit()
            print(f"[PASS] QC of {edge_file.parent.name}/{edge_file.name} - Lines: {index + 1}")
    return None

def update_master_registered_terms_file(term_file, output_file) -> None:
    term_data = []
    skipped_by_keep = 0
    with open(term_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                row = json.loads(line)
                # Reviewer can mark `"keep": false` on any row to omit it from
                # the final dictionary. Default (missing field) is True.
                if row.get("keep", True) is False:
                    skipped_by_keep += 1
                    continue
                term_data.append(row)
    if skipped_by_keep:
        print(f"[KEEP=FALSE] Skipped {skipped_by_keep} rows in {term_file.parent.name}/{term_file.name}")

    with open(output_file, 'r', encoding='utf-8') as f:
            try:
                output_data = json.load(f)
                output_data = output_data if isinstance(output_data, list) else []
                print("-"*80)
            except:
                output_data = []
                print("\n" + "="*80)
                print("Initializing registered terms file...\n" + "-"*80)

    print(f"Loaded {len(term_data)} terms from {term_file.parent.name}/{term_file.name}...")
    term_uuid_to_index = {}
    try:
        for i, entry in enumerate(output_data):
            term_uuid = entry.get("term_uuid")
            if term_uuid:
                term_uuid_to_index[term_uuid] = i
    except Exception as e:
        term_uuid_to_index = {}
        print(f"[ERROR] {e}")

    # Process each term from terms.jsonl
    updated_count, new_count, skipped_count = 0, 0, 0
    for entry in term_data:
        # Mandatory fields
        term = entry['term'].strip()
        xref = entry["xref"].strip()
        term_uuid = entry["term_uuid"].strip()
        src_uuid = entry["src_uuid"].strip()

        # Optional fields
        # METADATA_ORDER = ["exact_synonyms", "gsd_id", "gtc_id", "description", "definition", "glycoCT", "iupac_condensed", "classification", "is_class", "raw_term", "evidence"]
        metadata = entry.get("metadata", {})
        gsd_id = metadata.get("gsd_id", None)
        gtc_id = metadata.get("gtc_id", [])
        metadata_fields = [
            "exact_synonyms",
            "abbreviations",
            "gsd_id",
            "gtc_id",
            "db_xref",
            "description",
            "definition",
            "glycoCT",
            "iupac_condensed",
            "classification",
            "bgsl_curator_meta",   # carries suggested_class from curator
            "is_class",
            "raw_term",
            "evidence",
        ]

        def merge_metadata_field(existing_entry, field_name, new_value):
            if new_value is None or new_value == "":
                return

            existing_value = existing_entry.get(field_name)

            # Normalize list-like values
            if isinstance(new_value, list):
                new_list = [v for v in new_value if v not in [None, ""]]
                if not new_list:
                    return
                if existing_value in [None, ""]:
                    existing_entry[field_name] = new_list
                    return
                if isinstance(existing_value, list):
                    for v in new_list:
                        if v not in existing_value:
                            existing_value.append(v)
                    existing_entry[field_name] = existing_value
                    return
                # Existing is scalar, new is list -> conflict
                print(f"[WARN] Metadata conflict for '{field_name}' on {term_uuid}: existing scalar vs new list. Keeping existing.")
                return

            # Scalar new value
            if existing_value in [None, ""]:
                existing_entry[field_name] = new_value
                return
            if isinstance(existing_value, list):
                if new_value not in existing_value:
                    existing_value.append(new_value)
                existing_entry[field_name] = existing_value
                return
            if existing_value != new_value:
                print(f"[WARN] Metadata conflict for '{field_name}' on {term_uuid}: '{existing_value}' vs '{new_value}'. Keeping existing.")

        # Skip if no term_uuid or term is [DISCARD]
        if not term_uuid or term == "[DISCARD]":
            skipped_count += 1
            continue
        
        # Create new source entry
        new_source = {
            "src_lbl": term,
            "src": xref,
            "src_uuid": src_uuid
        }

        # If term_uuid already exists in registered terms
        if term_uuid in term_uuid_to_index:
            # Update existing entry
            index = term_uuid_to_index[term_uuid]
            existing_entry = output_data[index]

            # label (the term name)
            if not existing_entry.get("lbl") and term:
                existing_entry["lbl"] = term

            # gtc_id (GlyTouCan ID)
            if "gtc_id" not in existing_entry:
                existing_entry["gtc_id"] = []
            if gtc_id:
                if isinstance(gtc_id, list):
                    for gid in gtc_id:
                        if gid and gid not in existing_entry["gtc_id"]:
                            existing_entry["gtc_id"].append(gid)
                else:
                    if gtc_id not in existing_entry["gtc_id"]:
                        existing_entry["gtc_id"].append(gtc_id)

            # gsd_id (GSDXXXXX)
            if "gsd_id" not in existing_entry:
                existing_entry["gsd_id"] = ""

            if gsd_id and gsd_id not in existing_entry.get("gsd_id", []):
                existing_entry["gsd_id"] = gsd_id

            # Other metadata fields
            for field_name in metadata_fields:
                if field_name == "gtc_id":
                    continue
                merge_metadata_field(existing_entry, field_name, metadata.get(field_name))

            # Add new source to existing sources
            existing_sources = existing_entry.get("sources", [])       
            # Check if this source already exists (by src_uuid)
            source_exists = any(s.get("src_uuid") == src_uuid for s in existing_sources)      
            if not source_exists:
                existing_sources.append(new_source)
                existing_entry["sources"] = existing_sources
                updated_count += 1
                #print(f"Updated entry for '{term}' (UUID: {term_uuid}...)")
            else:
                print(f"[ERROR] You should never see this message. Source already exists for '{term}' (term_uuid: {term_uuid})")
        
        # If term_uuid does not exist, create a new entry        
        else:
            gtc_id_list = []
            if gtc_id:
                if isinstance(gtc_id, list):
                    gtc_id_list.extend([gid for gid in gtc_id if gid])
                else:
                    gtc_id_list.append(gtc_id)

            new_entry = {
                "lbl": term,
                "term_uuid": term_uuid,
                "gtc_id": gtc_id_list,
                "sources": [new_source]
            }

            # Carry over metadata fields into new entries
            for field_name in metadata_fields:
                if field_name == "gtc_id":
                    continue
                value = metadata.get(field_name)
                if value not in [None, ""]:
                    new_entry[field_name] = value
            
            output_data.append(new_entry)
            term_uuid_to_index[term_uuid] = len(output_data) - 1
            new_count += 1
            #print(f"Added new entry for '{term}' (UUID: {term_uuid[:8]}...)")

    # --- Hoist curator suggested_class → classification (3-tier only) ---
    import re as _re
    _VALID_3TIER = _re.compile(r'^[123][A-E]$|^X$')
    n_curator_class = 0
    n_legacy_cleared = 0
    for entry in output_data:
        # Extract the curator's 3-tier code from bgsl_curator_meta
        curator_meta = entry.get("bgsl_curator_meta") or {}
        if isinstance(curator_meta, dict):
            sc = (curator_meta.get("suggested_class") or "").strip()
            if sc and _VALID_3TIER.match(sc):
                entry["classification"] = sc
                n_curator_class += 1
                continue
        # If no curator code, clear legacy free-text classification
        existing = (entry.get("classification") or "").strip()
        if existing and not _VALID_3TIER.match(existing):
            entry["classification"] = ""
            n_legacy_cleared += 1
    if n_curator_class or n_legacy_cleared:
        print(f"- Classification: {n_curator_class} from curator suggested_class, {n_legacy_cleared} legacy free-text cleared")

    with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)

    print(f"- Entries skipped: {skipped_count}")
    print(f"- Entries updated: {updated_count}")
    print(f"- Entries created: {new_count}")

    print(f"- Total entries in master file: {len(output_data)} (+{new_count})")

    return None

def post_merge_quality_check(output_file) -> None:
    print("\n" + "="*80 + "\nRunning post-merge quality check...")
    with open(output_file, "r") as f:
        # Check for duplicates in term and gsd_id in metadata
        json_data = json.load(f)
        term_set = set()
        gsd_id_set = set()
        duplicate_terms = set()
        duplicate_gsd_ids = set()
        
        for entry in json_data:
            term = entry.get("lbl", "").strip()
            gsd_id = entry.get("gsd_id", "").strip()
            if term:
                if term in term_set:
                    duplicate_terms.add(term)
                else:
                    term_set.add(term)
            if gsd_id:
                if gsd_id in gsd_id_set:
                    duplicate_gsd_ids.add(gsd_id)
                else:
                    gsd_id_set.add(gsd_id)

        if duplicate_terms:
            print(f"[ALERT] Found {len(duplicate_terms)} duplicate terms in master nodes file:")
            for term in duplicate_terms:
                print(f"- {term}")
                dup_entries = [entry for entry in json_data if entry.get("lbl", "").strip() == term]
                for entry in dup_entries:
                    print(f"   - {entry['term_uuid']}")
                    print(f"     Sources: {', '.join([src.get('src', '') for src in entry['sources']])} ({', '.join([src.get('src_uuid', '') for src in entry['sources']])})")
        else:
            print("[PASS] No duplicate terms found in master_registered_terms.json")
        
        if duplicate_gsd_ids:
            print(f"[ALERT] Found {len(duplicate_gsd_ids)} duplicate gsd_id in master nodes file:")
            for gsd_id in duplicate_gsd_ids:
                src_uuids = [src.get("src_uuid", "") for entry in json_data if entry.get("gsd_id", "").strip() == gsd_id for src in entry.get("sources", [])]
                print(f"- {gsd_id} ({', '.join(src_uuids)})")
        else:
            print("[PASS] No duplicate gsd_id found in master nodes file")

def update_master_registered_edges_file(edge_file, output_file) -> None:
    edge_data = []
    with open(edge_file, 'r', encoding='utf-8') as f:
        for index, line in enumerate(f):
            try:
                line = json.loads(line)
                edge_data.append(line)
            except json.JSONDecodeError:
                print(f"[Error] Error decoding JSON on line {index + 1} of {edge_file.parent.name}/{edge_file.name}. Skipping this line.")

    with open(output_file, 'r', encoding='utf-8') as f:
            try:
                output_data = json.load(f)
                output_data = output_data if isinstance(output_data, list) else []
                print("-"*80)
            except:
                output_data = []
                print("\n" + "="*80)
                print("Initializing registered edges file...\n" + "-"*80)

    print(f"Loaded {len(edge_data)} edges from {edge_file.parent.name}/{edge_file.name}...")

    skipped, merged, created = 0, 0, 0
    
    relations_list = []
    try:
        for entry in output_data:
            subj = entry.get("subj")
            pred = entry.get("pred")
            obj = entry.get("obj")
            query_key = subj + pred + obj

            if query_key:
                relations_list.append((query_key))
    except Exception as e:
        relations_list = []
        print(f"[ERROR] {e}")
        
    for edge in edge_data:
        subj = edge.get("subj", "").strip()
        pred = edge.get("pred", "").strip()
        obj = edge.get("obj", "").strip()      
        candidate_key = subj + pred + obj
        
        xref = edge.get("xref", "").strip()
        comment = edge.get("comment", "").strip()
        if comment == "[DISCARD]":
            skipped += 1
            continue
        
        if candidate_key not in relations_list:
            created += 1
            new_entry = {
                "subj": subj,
                "pred": pred,
                "obj": obj,
                "comment": comment  
            }
            output_data.append(new_entry)
        else:
            merged += 1
    
    print(f"- Entries skipped: {skipped}")
    print(f"- Entries merged: {merged}")
    print(f"- Entries created: {created}")
    print(f"- Total edges in master file: {len(output_data)} (+{created})")
        
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)
    return None

def build_ontology(nodes_file, edges_file, output_file, processing_queue_terms) -> None:
    print("\n" + "="*80)
    print("Building glycan structure dictionary...")
    
    # Load master nodes
    with open(nodes_file, "r", encoding="utf-8") as f:
        master_nodes = json.load(f)
    print(f"Loaded {len(master_nodes)} nodes from {nodes_file.name}")
    
    # Load master edges
    with open(edges_file, "r", encoding="utf-8") as f:
        master_edges = json.load(f)
    print(f"Loaded {len(master_edges)} edges from {edges_file.name}")
    
    # Build relationship maps from edges (supports expanded edge types)
    # Synonym predicates are bidirectional; is_a / broad_synonym_of /
    # narrow_synonym_of are directional but still surfaced in the
    # related_synonyms map so consumers can see the naming neighbourhood.
    SYNONYM_PREDICATES = {
        "has_related_synonym",
        "exact_synonym_of",
        "related_synonym_of",
        "abbreviation_of",
        "broad_synonym_of",
        "narrow_synonym_of",
    }

    related_synonyms_map = {}  # term_uuid -> list of related synonym labels
    uuid_to_label = {node.get("term_uuid"): node.get("lbl") for node in master_nodes}

    for edge in master_edges:
        pred = edge.get("pred", "")
        subj_uuid = edge.get("subj")
        obj_uuid = edge.get("obj")

        subj_label = uuid_to_label.get(subj_uuid)
        obj_label = uuid_to_label.get(obj_uuid)

        if pred in SYNONYM_PREDICATES and subj_label and obj_label:
            # Bidirectional synonym mapping
            if subj_uuid not in related_synonyms_map:
                related_synonyms_map[subj_uuid] = []
            if obj_label not in related_synonyms_map[subj_uuid]:
                related_synonyms_map[subj_uuid].append(obj_label)

            if obj_uuid not in related_synonyms_map:
                related_synonyms_map[obj_uuid] = []
            if subj_label not in related_synonyms_map[obj_uuid]:
                related_synonyms_map[obj_uuid].append(subj_label)

        elif pred == "is_a" and subj_label and obj_label:
            # Directional: subj is_a obj (subj is more specific)
            # Store in related_synonyms_map for now (both directions as context)
            if subj_uuid not in related_synonyms_map:
                related_synonyms_map[subj_uuid] = []
            if obj_label not in related_synonyms_map[subj_uuid]:
                related_synonyms_map[subj_uuid].append(obj_label)

    print(f"Built relationship maps for {len(related_synonyms_map)} terms")
    
    # Helper function
    def flatten_list(data):
        if not isinstance(data, list):
            return data
        result = []
        for item in data:
            if isinstance(item, list):
                result.extend(flatten_list(item))
            else:
                result.append(item)
        return result
    
    # Helper function: get metadata from raw JSONL files
    def get_source_metadata(src_uuid, term_uuid):
        # Search through all raw term files
        for terms_file in processing_queue_terms:
            try:
                with open(terms_file, "r", encoding="utf-8") as f:
                    for line in f:
                        entry = json.loads(line)
                        # Same filter as the term merger: ignore keep=false rows
                        if entry.get("keep", True) is False:
                            continue
                        if entry.get("src_uuid") == src_uuid:
                            metadata = entry.get("metadata", {})
                            
                            # Flatten any nested lists in metadata
                            for key, value in metadata.items():
                                if isinstance(value, list):
                                    metadata[key] = flatten_list(value)
                            
                            # Build SourceContent structure
                            source_content = {
                                "gsd_id": metadata.get("gsd_id"),
                                "gtc_id": metadata.get("gtc_id"),
                                "exact_synonyms": metadata.get("exact_synonyms"),
                                "abbreviations": metadata.get("abbreviations"),
                                "related_synonyms": related_synonyms_map.get(term_uuid, []),
                                "classification": metadata.get("classification"),
                                "definition": metadata.get("definition"),
                                "description": metadata.get("description"),
                                "evidence": metadata.get("evidence"),
                                "publication": metadata.get("publication"),
                                "db_xref": metadata.get("db_xref"),
                                "iupac_condensed": metadata.get("iupac_condensed"),
                            }
                            
                            # Handle function field (list of objects with src and content)
                            if metadata.get("function"):
                                functions = metadata["function"]
                                if isinstance(functions, list):
                                    source_content["function"] = [
                                        {"src": f.get("src", ""), "content": f.get("content", "")}
                                        if isinstance(f, dict) else {"src": "", "content": str(f)}
                                        for f in functions
                                    ]
                            
                            # Handle disease_association field
                            if metadata.get("disease_association"):
                                diseases = metadata["disease_association"]
                                if isinstance(diseases, list):
                                    source_content["disease_association"] = [
                                        {"src": d.get("src", ""), "content": d.get("content", "")}
                                        if isinstance(d, dict) else {"src": "", "content": str(d)}
                                        for d in diseases
                                    ]
                            
                            return source_content
            except Exception as e:
                print(f"Warning: Error reading {terms_file}: {e}")
                continue
        return {}
    
    # Build nodes with enhanced source metadata
    enhanced_nodes = []
    for node in master_nodes:
        term_uuid = node.get("term_uuid")
        enhanced_sources = []
        for source in node.get("sources", []):
            src_content = get_source_metadata(source.get("src_uuid"), term_uuid)
            enhanced_source = {
                "src_lbl": source.get("src_lbl"),
                "src": source.get("src"),
                "src_uuid": source.get("src_uuid"),
                "src_content": src_content
            }
            enhanced_sources.append(enhanced_source)
        
        enhanced_node = {
            "lbl": node.get("lbl"),
            "term_uuid": term_uuid,
            "sources": enhanced_sources
        }
        enhanced_nodes.append(enhanced_node)
    
    # Build edges — drop any edge whose subj or obj is not a known node.
    # Orphan edges happen when a row was filtered out by `keep=false`, or when
    # `apply_review.py` retired a node that the edge still referenced.
    formatted_edges = []
    orphan_dropped = 0
    for edge in master_edges:
        subj_uuid = edge.get("subj")
        obj_uuid = edge.get("obj")
        if subj_uuid not in uuid_to_label or obj_uuid not in uuid_to_label:
            orphan_dropped += 1
            continue
        formatted_edge = {
            "subj": subj_uuid,
            "pred": edge.get("pred"),
            "obj": obj_uuid,
            "comment": edge.get("comment")
        }
        formatted_edges.append(formatted_edge)
    if orphan_dropped:
        print(f"[BUILD] Dropped {orphan_dropped} orphan edge(s) referencing filtered nodes")
    
    # Build final GSD structure
    gsd = {
        "nodes": enhanced_nodes,
        "edges": formatted_edges
    }
    
    # Write to dictionary.json
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(gsd, f, indent=2, ensure_ascii=False)
    
    print(f"[COMPLETED] Successfully created dictionary.json with {len(enhanced_nodes)} nodes and {len(formatted_edges)} edges")
    print(f"            Output: {output_file.parent.name}/{output_file.name}")
    print("="*80)