import os
from pathlib import Path

from postprocessing_utils import backup_existing_file
from postprocessing_utils import create_processing_queue
from postprocessing_utils import quality_check_jsonl_files
from postprocessing_utils import update_master_registered_terms_file
from postprocessing_utils import post_merge_quality_check
from postprocessing_utils import update_master_registered_edges_file

OUTF_NAME_NODES = "master_nodes.json"
OUTF_NAME_EDGES = "master_edges.json"
SRC_DIR = Path(os.path.abspath(__file__)).parent.parent.parent
RAW_DIR = SRC_DIR / r"data/raw"

QC_MODE = False # Set to True to enable QC mode; False for normal mode

if QC_MODE:
    print("="*80 + "\nRunning in QC mode...")
    def backup_existing_file(SRC_DIR, OUTF_NAME_NODES):
        pass
    # Under development, do QC_MODE = False at this stage
else:
    print("="*80 + "\nRunning in normal mode...")

# If master_nodes.json already exists, create a new file with an indexed suffix and move it to backup
backup_existing_file(SRC_DIR, OUTF_NAME_NODES)
output_term_file = SRC_DIR / "data/processed" / OUTF_NAME_NODES

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
    update_master_registered_terms_file(term_file, output_term_file)
    
# Post-merge quality check for duplicate term_uuid, gsd_id, and src_uuid across the entire master file
post_merge_quality_check(output_term_file)

# If master_edges.json already exists, create a new file with an indexed suffix and move it to backup
backup_existing_file(SRC_DIR, OUTF_NAME_EDGES)
output_edge_file = SRC_DIR / "data/processed" / OUTF_NAME_EDGES

# Update master_registered_edges.json by merging each edges.jsonl file in the processing queue    
for edge_file in processing_queue_edges:
    update_master_registered_edges_file(edge_file, output_edge_file)