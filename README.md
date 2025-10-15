# Glycan Structure Dictionary (GSD)

This project aims to enrich and update the Glycan Structure Dictionary:
We have developed an large language model (LLM) -based pipeline for curating, normalizing, mapping, and consolidating glycan structure terminology from heterogeneous biomedical sources into a unified, de-duplicated reference knowledgebase.

**Reference** (original publication):

> Vora J, Navelkar R, Vijay-Shanker K, Edwards N, Martinez K, Ding X, Wang T, Su P, Ross K, Lisacek F, Hayes C, Kahsay R, Ranzinger R, Tiemeyer M, Mazumder R. The Glycan Structure Dictionary-a dictionary describing commonly used glycan structure terms. Glycobiology. 2023 Jun 3;33(5):354-357. doi: 10.1093/glycob/cwad014. PMID: 36799723; PMCID: PMC10243773.

---
## Overview
This pipeline builds a master dictionary of glycan structure terms by:
1. Ingesting heterogeneous source term sets (Essentials of Glycobiology, legacy GSD v0, curated publications, composition lists, curator-supplied sets, etc.).
2. Normalizing and formatting raw term JSONL inputs into a canonical intermediate structure.
3. Creating a semantic vector store (Chroma + OpenAI embeddings) for retrieval-augmented AI mapping.
4. Running AI-assisted mapping agents to (a) map synonyms to existing concepts or (b) propose creation of new canonical terms.
5. Reconciling AI action logs into term-to-UUID mappings.
6. Post-processing: merging multiple sources into consolidated node (master_nodes.json) and edge (master_edges.json) registries with quality checks and backups.

> [!notes]
> The supplementary materials documents the identification and extraction of glycan structure terms from 'The Essentials of Glycobiology' (EOG) using LLMs. Those terms serve as one of the main sources used to update and enrich the original GSD.

> Varki A, Cummings RD, Esko JD, et al., editors. Essentials of Glycobiology [Internet]. 4th edition. Cold Spring Harbor (NY): Cold Spring Harbor Laboratory Press; 2022. Available from: https://www.ncbi.nlm.nih.gov/books/NBK579918/ doi: 10.1101/9781621824213

---
## Repository Structure
```
main/
  1_ai-assisted_term_matching/
    01_create_vectordb.py
    02a_ai_mapping_gsdv0.py
    02b_match_gsdv0_ai_mapping_with_uuid.py
    03a_ai_mapping_pubdictionaries.py
    03b_match_pubdict_ai_mapping_with_uuid.py
  2_generate_mappings/
    postprocessing.py
    postprocessing_utils.py
  3_utils/
    util_raw_terms_formatter.py
    util_uuid_formatter.py
    util_related_synonyms_collector.py
    util_gtc2seq.py
    util_glycoct2gtc.py
    util_iupac2gtc.py
  supp_ai-assisted_term_extraction/
    01_vectorize_eog.py
    02_gliner_eog.py
    03_filter_records.py
    04_combine_records.py
    05_summarize_records.py
    utils_supp.py

data/
  raw/                # Editable source-specific JSONL term + edge files
  processed/          # Generated master artifacts (DO NOT EDIT MANUALLY)
    master_nodes.json
    master_edges.json
    backup/           # Indexed backups of prior master files
  supp/               # Supplementary folder (term extraction)
    essentials_of_glycobiology/  # Text files of EOG
    stats/            # Summary of terms extracted from EOG
    vector_store/     # Embeddings of EOG
  vector_store/       # Embeddings of the updated GSD
```

---
## Data Model (JSONL)
Each source terms file (`*terms.jsonl`) after formatting should produce lines like:
```
{
    "lbl": "sialyl Lewis x",
    "term_uuid": "GSD:32e928fb-1550-5e0a-945f-2218ac79b83c",
    "gtc_id": [
      "G00054MO"
    ],
    "sources": [
      {
        "src_lbl": "sialyl Lewis x",
        "src": "SRC:EOG_VARKI_4E",
        "src_uuid": "SRC:66cc8ff8-5b05-4882-8c47-8ab4f036bed3"
      },
      {
        "src_lbl": "sialyl Lewis x",
        "src": "SRC:GSD_GLYGEN_V0",
        "src_uuid": "SRC:0e4ec742-01a0-4d61-b1fb-655f380ac009"
      },
      {
        "src_lbl": "sialyl Lewis x",
        "src": "SRC:PUBDICTIONARIES-GLYCAN-IMAGE",
        "src_uuid": "SRC:5c02589c-9c5e-489f-8863-e0bd2618d901"
      }
    ],
    "gsd_id": "GSD000151"
  },
```
Edges (`*edges.jsonl`) follow:
```
{
    "subj": "GSD:a7868da4-a6c2-4825-97b9-c86700b1c213",
    "pred": "is_a_related_synonym_of",
    "obj": "GSD:8ce1f4e6-8cbe-5167-8ece-a1cfc850d3a5",
    "comment": "GA1 is a related synonym of asialo-GM1"
  },
```

---
## Workflow
### 1. Prepare Environment
Create `.env` in repo root:
```
OPENAI_API_KEY=your_key_here
```
> [!note]
> An OpenAI API key enables the application to access LLM services. [Where to obtain an API key?](https://www.google.com/url?sa=t&source=web&rct=j&opi=89978449&url=https://platform.openai.com/api-keys&ved=2ahUKEwjE1sX_vqSQAxUZL1kFHe88MkgQFnoECA4QAQ&usg=AOvVaw1YhcGDWJXhiKSfmL59Pnfn)

Install dependencies:
```
pip install langchain langchain-openai langchain-chroma python-dotenv requests
```

### 2. Build Vector Store
Run `main/1_ai-assisted_term_matching/01_create_vectordb.py` to:
- Read `terms_edited.jsonl` from a source (e.g., `src_gsdv0`)
- Embed term + synonyms + description
- Persist Chroma collection under `data/vector_store/`

### 3. AI-Assisted Mapping
Two agent scripts:
- `02a_ai_mapping_gsdv0.py` – processes legacy GSD v0 terms.
- `03a_ai_mapping_pubdictionaries.py` – processes curated publication dictionaries.

Agents:
- Retrieve top-k similar entries via vector store
- Decide: map to existing UUID (append as synonym) or add new term
- Append action records to `terms_ai-decisions_*.jsonl`
- Log reasoning to `ai_mapping_demo.log`

### 4. Reconcile AI Decisions
Scripts:
- `02b_match_gsdv0_ai_mapping_with_uuid.py`
- `03b_match_pubdict_ai_mapping_with_uuid.py`

They join AI action outputs back onto original `terms_edited.jsonl` to produce enriched `terms_demo.jsonl` with definitive `term_uuid` field assignments.

### 5. Post-Processing Merge
`2_generate_mappings/postprocessing.py` orchestrates consolidation:
1. Backup existing `master_nodes.json` / `master_edges.json` (indexed copies in `processed/backup/`).
2. Determine processing order: `src_eog` → `src_gsdv0` → `src_pubdictionaries` → `src_n-compo` → `src_glygen_curators`.
3. Quality control via `quality_check_jsonl_files()`:
   - Mandatory fields present
   - Proper UUID prefixes (`GSD:` / `SRC:`)
   - No duplicate `term_uuid` / `src_uuid` inside individual files
4. Incrementally merge each `*terms.jsonl` with `update_master_registered_terms_file()`:
   - Create/update concept entries
   - Accumulate `gtc_id` lists
   - Append source provenance blocks `{src_lbl, src, src_uuid}`
5. Post-merge QC: duplicate labels or `gsd_id` warnings.
6. Process edges with `update_master_registered_edges_file()` (skip `[DISCARD]`).

### 6. Outputs
- `data/processed/master_nodes.json` – canonical glycan structure concept catalog.
- `data/processed/master_edges.json` – semantic relations (currently synonym-like edges, extensible).

---
## Quality & Validation
Pre-merge checks abort on:
- Missing mandatory fields
- Duplicate `term_uuid` or `src_uuid` in a single file
- Incorrect prefix formatting
Post-merge checks warn on duplicated labels or `gsd_id` values (for curator review).

---
## Utilities Summary
| Script | Purpose |
| ------ | ------- |
| `util_raw_terms_formatter.py` | Normalize heterogeneous raw term JSONL into canonical schema |
| `util_uuid_formatter.py` | Enforce UUID prefix conventions and clean embedded newline encodings |
| `util_related_synonyms_collector.py` | Generate edge records from `related_synonym` metadata |
| `util_gtc2seq.py` | Resolve GlyTouCan accession → IUPAC condensed sequence via GlyCosmos APIs |
| `util_glycoct2gtc.py` | Convert GlycoCT → WURCS & obtain GlyTouCan ID (format converter) |
| `util_iupac2gtc.py` | Convert IUPAC condensed → WURCS/GlyTouCan ID (older API version) |

---
## Quickstart
### Generate Vector Store & Map Terms
```bash
# 1. Build embeddings
python main/1_ai-assisted_term_matching/01_create_vectordb.py

# 2. Run AI mapping for a source
python main/1_ai-assisted_term_matching/02_ai_mapping_gsdv0.py

# 3. Reconcile mapping decisions
python main/1_ai-assisted_term_matching/02_match_gsdv0_ai_mapping_with_uuid.py

# (Repeat analogous steps for pubdictionaries)
python main/1_ai-assisted_term_matching/03_ai_mapping_pubdictionaries.py
python main/1_ai-assisted_term_matching/03_match_pubdict_ai_mapping_with_uuid.py

# 4. Merge into master dictionaries
python main/2_generate_mappings/postprocessing.py
```

---
## Extending the Pipeline
To add a new source (e.g., `src_NEWSOURCENAME`):
1. Place `terms.jsonl` (and optionally `edges.jsonl`) under `data/raw/src_newsource/`.
2. Ensure formatted schema (run formatter if needed).
3. Add its identifier to `PROCESSING_ORDER` in `postprocessing.py` at the appropriate precedence.
4. Re-run postprocessing.

---
## AI Decision Logging
Logs (`ai_mapping_demo.log`) capture agent tool calls and rationales. These are intended for curator audit and reproducibility of synonym decisions.

---
## Automatic Backups
Each run of `postprocessing.py` creates indexed backups of prior master files in `data/processed/backup/`, e.g.:
```
master_nodes_001.json
master_nodes_002.json
...
```
> [!WARNING]
> Never manually edit files in `processed/`; regenerate them through the pipeline.

---
## Notes
- Data under `data/raw` is editable.
- All artifacts under `data/processed` are generated programmatically and MUST NOT be edited manually.
