from pathlib import Path
from datetime import datetime

from postprocessing_utils import backup_existing_file
from postprocessing_utils import create_processing_queue
from postprocessing_utils import quality_check_jsonl_files
from postprocessing_utils import update_master_registered_terms_file
from postprocessing_utils import post_merge_quality_check
from postprocessing_utils import update_master_registered_edges_file
from postprocessing_utils import build_ontology

timestamp = datetime.now().strftime("_%Y%m%d_%H%M%S")

OUTF_NAME_NODES = f"master_nodes{timestamp}.json"
OUTF_NAME_EDGES = f"master_edges{timestamp}.json"
OUTF_NAME_GSD = f"dictionary{timestamp}.json"

SRC_DIR = Path(__file__).parents[2]
RAW_DIR = SRC_DIR / "data" / "raw"
PRC_DIR = SRC_DIR / "data" / "processed"
BCK_DIR = SRC_DIR / "data" / "processed" / "backup" / f"backup_{timestamp}"

BCK_DIR.mkdir(parents=True, exist_ok=True)

json_files = list(PRC_DIR.glob("*.json"))
if json_files:
    for json_file in json_files:
        backup_name = json_file.name
        backup_path = BCK_DIR / backup_name
        json_file.rename(backup_path)
        print(f"- Backed up {json_file.name} to {BCK_DIR.name}/{backup_name}")

OUTF_PATH_NODES = PRC_DIR / OUTF_NAME_NODES
OUTF_PATH_NODES.touch(exist_ok=True)
OUTF_PATH_EDGES = PRC_DIR / OUTF_NAME_EDGES
OUTF_PATH_EDGES.touch(exist_ok=True)
OUTF_PATH_GSD = PRC_DIR / OUTF_NAME_GSD
OUTF_PATH_GSD.touch(exist_ok=True)

QC_MODE = False # Set to True to enable QC mode; False for normal mode

if QC_MODE:
    print("="*80 + "\nRunning in QC mode...")
    def backup_existing_file(SRC_DIR, OUTF_NAME_NODES):
        pass
    # Under development, do QC_MODE = False at this stage
else:
    print("="*80 + "\nRunning in normal mode...")

# "src_eog" should be processed first
PROCESSING_ORDER = ["src_eog", "src_gsdv0", "src_pubdictionaries", "src_n-compo", "src_glygen_curators"]

# Create a processing queue based on the defined order
processing_queue_terms, processing_queue_edges = create_processing_queue(PROCESSING_ORDER, RAW_DIR)

# Quality check for duplicate term_uuid and src_uuid within each jsonl file
MANDATORY_FIELDS_TERMS = ["term", "xref", "term_uuid", "src_uuid"]
MANDATORY_FIELDS_EDGES = ["subj", "pred", "obj", "xref"]
quality_check_jsonl_files(processing_queue_terms, processing_queue_edges, MANDATORY_FIELDS_TERMS, MANDATORY_FIELDS_EDGES)

# Update master_registered_terms.json by merging each terms.jsonl file in the processing queue
for term_file in processing_queue_terms:
    update_master_registered_terms_file(term_file, OUTF_PATH_NODES)
    
# Post-merge quality check for duplicate term_uuid, gsd_id, and src_uuid across the entire master file
post_merge_quality_check(OUTF_PATH_NODES)

# Update master_registered_edges.json by merging each edges.jsonl file in the processing queue    
for edge_file in processing_queue_edges:
    update_master_registered_edges_file(edge_file, OUTF_PATH_EDGES)

# Build the final comprehensive glycan structure dictionary
build_ontology(OUTF_PATH_NODES, OUTF_PATH_EDGES, OUTF_PATH_GSD, processing_queue_terms)