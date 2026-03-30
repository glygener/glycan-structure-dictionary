<a id="readme-top"></a>

<!--
*** This doc is created using the Best-README-Template: https://github.com/othneildrew/Best-README-Template/
-->

<!-- PROJECT SHIELDS -->
<!--
*** I'm using markdown "reference style" links for readability.
*** Reference links are enclosed in brackets [ ] instead of parentheses ( ).
*** See the bottom of this document for the declaration of the reference variables
*** for contributors-url, forks-url, etc. This is an optional, concise syntax you may use.
*** https://www.markdownguide.org/basic-syntax/#reference-style-links
-->

[![Release Notes][release-shield]][release-url]
[![Issues][issues-shield]][issues-url]

[![BiomarkerKB][biomarkerkb-shield]][biomarkerkb-url]
[![GlyGen][glygen-shield]][glygen-url]
[![Wiki Page][wiki-shield]][wiki-url]

<!-- PROJECT LOGO -->
<br />
<div align="center">
  <a href="https://github.com/glygener/glycan-structure-dictionary">   
   <img src="https://github.com/glygener/glycan-structure-dictionary/blob/main/docs/static/logo.png?raw=true)" alt="Logo" width="400" height="200">
  </a>

<h1 align="center">Biomarker Glycan Structure Terms (bGST) Workflow</h1>

  <p align="center">
    LLM-powered pipeline for extracting & normalizing glycan structure terminology
    <br />
    <a href="https://github.com/glygener/glycan-structure-dictionary"><strong>Explore the docs »</strong></a>
    <br />
    <br />
    <a href="https://github.com/glygener/glycan-structure-dictionary">View Demo</a>
    &middot;
    <a href="https://github.com/glygener/glycan-structure-dictionary/issues/new?labels=bug&template=bug-report---.md">Report Bug</a>
    &middot;
    <a href="https://github.com/glygener/glycan-structure-dictionary/issues/new?labels=enhancement&template=feature-request---.md">Contact Us</a>
  </p>
</div>

<!-- TABLE OF CONTENTS -->
<div align="left">
  <div style="display: inline-block; text-align: left; border: 1px solid #888; border-radius: 30px; max-width: 340px;">
    <details style="padding: 10px 20px 0px;">
      <summary><strong>&nbsp&nbspTable of Contents</strong></summary>
      <ol>
        <li><a href="#about-this-project">About this project</a></li>
        <li><a href="#getting-started">Getting started</a></li>
        <li><a href="#usage">Usage</a></li>
        <li><a href="#data-model">Data model</a></li>
        <li><a href="#license">License</a></li>
        <li><a href="#acknowledgements">Acknowledgements</a></li>
      </ol>
    </details>
  </div>
</div>

<!-- ABOUT THE PROJECT -->

## About This Project

<!--
[![Product Name Screen Shot][product-screenshot]](https://placeholder.com)
-->

Biomarker Glycan Structure Terms (bGST) is a controlled vocabulary of glycan structure terms extracted from literature and databases. It captures textual representations of glycans and glycan-related structural features, including full structures, motifs, epitopes, and substructures.

Because glycan structures are described inconsistently across sources, this project uses an LLM-assisted retrieval and entity resolution workflow to map terms to existing [Glycan Structure Dictionary (GSD)](https://wiki.glygen.org/Glycan_structure_dictionary) entries or register new ones when needed. This helps unify heterogeneous glycan terminology into a normalized, de-duplicated reference knowledgebase.

**Previous Work**:

> Vora J, Navelkar R, Vijay-Shanker K, Edwards N, Martinez K, Ding X, Wang T, Su P, Ross K, Lisacek F, Hayes C, Kahsay R, Ranzinger R, Tiemeyer M, Mazumder R. **The Glycan Structure Dictionary**-a dictionary describing commonly used glycan structure terms. Glycobiology. 2023 Jun 3;33(5):354-357. doi: 10.1093/glycob/cwad014. PMID: [36799723](https://pubmed.ncbi.nlm.nih.gov/36799723/); PMCID: PMC10243773.

<br>

<table>
  <tr>
    <td valign="top" width="33%">
      <img src="https://cdn.simpleicons.org/ollama/008080" alt="Ollama" height="40"><br>
      <strong>Local LLM inference</strong><br>
      Run the pipeline entirely locally via Ollama, with configurable model selection and hardware setup.
    </td>
    <td valign="top" width="33%">
      <img src="https://cdn.simpleicons.org/langgraph/simpleicons/008080" alt="LangGraph" height="40"><br>
      <strong>Structured term normalization</strong><br>
      Extract, normalize, and align glycan terminology through a state-driven workflow orchestrated by LangGraph.
    </td>
    <td valign="top" width="33%">
      <img src="https://brandlogos.net/wp-content/uploads/2025/06/chroma-logo_brandlogos.net_1z1qk-512x339.png" alt="Chroma" height="40"><br>
      <strong>Vector search + embeddings</strong><br>
      Build and query vector stores (Chroma) using embedded representations for similarity lookup.
    </td>
  </tr>
</table>

<p align="right"><a href="#readme-top">back to top ▲</a></p>

<!-- GETTING STARTED -->

## Getting Started

Follow these steps to get a local copy up and running.

### Prerequisites

- Install Ollama from [https://ollama.com/download](https://ollama.com/download), or alternatively:

  ```sh
  curl -fsSL https://ollama.com/install.sh | sh
  ```

  - Ollama version `>=v0.15.0` is recommended
  - On servers that run on environment modules (Lmod), use the following to display default version of installation:
    ```sh
    module -d avail ollama
    ```

### Installation

1. **Clone this repo:**

   ```sh
   git clone https://github.com/glygener/glycan-structure-dictionary.git
   cd glycan-structure-dictionary
   ```

2. **Pull the required Ollama models:**

   > A thinking model and an embedding model are required. If you chose to use other models, remember to update the model names at `configs/models.yaml`. This pipeline was developed using a locally hosted Ollama server where GPU acceleration is almost necessary. Otherwise, Ollama also offers cloud models with limited free usage. For accessing cloud models and obtaining a Ollama API key, refer to their [documentation](https://docs.ollama.com/cloud)

   Start your local ollama service at a separate terminal window (close this window after **verifying downloads**):

   **Non-HPC users:**

   ```sh
   ollama serve
   ```

   **For HPC (Slurm) users only:**

   - Load the `ollama` module every time when opening a new terminal window:

     ```sh
     module load ollama
     ollama serve
     ```

   Back to your main terminal window - Download your reasoning model and your embedding model ([more models](https://ollama.com/search)):

   ```sh
   ollama pull gpt-oss:20b
   ollama pull mxbai-embed-large:335m
   ```

   Verify the downloads:

   ```sh
   ollama list
   ```

   ```python
   # NAME                         ID              SIZE      MODIFIED
   # mxbai-embed-large:335m       468836162de7    669 MB    7 weeks ago
   # gpt-oss:20b                  17052f91a42e    13 GB     7 weeks ago
   ```
  
   (You may now close the terminal window that runs the Ollama server)

3. **Install Python dependencies:**

   (Optional) create a virtual environment with `Python 3.12`:

   ```sh
   python3.12 -m venv .venv
   source .venv/bin/activate
   ```

   Install packages:

   ```sh
   python -m pip install -r requirements.txt
   ```

4. Start Ollama server:
  
   **For Non-HPC users:**

   > [!note]
   > Every python script that utilizes LLM requires the hosting of an Ollama server. You may utilize these scripts to start/stop/check a server:

   ```bash
   python scripts/ollama/start_server.py
   python scripts/ollama/stop_server.py
   python scripts/ollama/status_server.py
   ```

   **For HPC (Slurm) users only:**

   Ollama server is managed using the shell script `./main_slurm.sh`. It serves as a template with resource pre-sets. To run a Python LLM script through the Slurm system, use `main_slurm.sh`, passing the target script path as an argument:

   ```bash
   sbatch main_slurm.sh <SCRIPT.PY_PATH>
   ```

   Example:

   ```bash
   sbatch main_slurm.sh src/gsd/part1_textbook/01_ingest.py
   ```

   On successful job submission, you will find the logs at `logs/slurm-<job-id>_output.txt` and `logs/slurm-<job-id>_error.txt`

<p align="right"><a href="#readme-top">back to top ▲</a></p>

<!-- USAGE EXAMPLES -->

## Usage

### Workflow

#### Part 1: Term extraction from EoG and relations mapping

![](https://github.com/glygener/glycan-structure-dictionary/blob/main/docs/static/graph_workflow_extract.png?raw=true)

1. Creating ChromaDB from EoG documents

   ```bash
   unzip data/inputs/eog/raw_chapters/unzip_me_before_running_01_ingest.py.zip -d data/inputs/eog/raw_chapters/
   ```

   ```bash
   python src/gsd/part1_textbook/01_ingest.py
   ```

   - Or for HPC users: `sbatch main_slurm.sh ...`

2. Extract terms from EoG documents (from vectorstore)

   ```bash
   python src/gsd/part1_textbook/02_extract.py
   ```

> Varki A, Cummings RD, Esko JD, et al., editors. Essentials of Glycobiology [Internet]. 4th edition. Cold Spring Harbor (NY): Cold Spring Harbor Laboratory Press; 2022. Available from: https://www.ncbi.nlm.nih.gov/books/NBK579918/ doi: 10.1101/9781621824213

#### Part 2: Incoporating heterogeneous data sources and build a deduplicated master list of terms

![](https://github.com/glygener/glycan-structure-dictionary/blob/main/docs/static/graph_workflow_map.jpg?raw=true)

This part builds a master dictionary of glycan structure terms by:

- Ingesting heterogeneous source term sets (Essentials of Glycobiology, legacy GSD v0, curated publications, composition lists, curator-supplied sets, etc.).
- Normalizing and formatting raw term JSONL inputs into a canonical intermediate structure.
- Creating a semantic vector store (Chroma + OpenAI embeddings) for retrieval-augmented AI mapping.
- Running AI-assisted mapping agents to (a) map synonyms to existing concepts or (b) propose creation of new canonical terms.
- Reconciling AI action logs into term-to-UUID mappings.
- Post-processing: merging multiple sources into consolidated node (`master_nodes.json`) and edge (`master_edges.json`) registries with quality checks and backups.

1. Build embeddings

   ```bash
   python src/gsd/part2_enrichment/1_ai-assisted_term_matching/01_create_vectordb.py
   ```

2. Run AI mapping for a source
   ```bash
   python src/gsd/part2_enrichment/1_ai-assisted_term_matching/02_ai_mapping_gsdv0.py
   ```

3. Reconcile mapping decisions
   ```bash
   python src/gsd/part2_enrichment/1_ai-assisted_term_matching/02_match_gsdv0_ai_mapping_with_uuid.py
   ```

   (Repeat analogous steps for pubdictionaries)

   ```bash
   python src/gsd/part2_enrichment/1_ai-assisted_term_matching/03_ai_mapping_pubdictionaries.py
   python src/gsd/part2_enrichment/1_ai-assisted_term_matching/03_match_pubdict_ai_mapping_with_uuid.py
   ```

4. Merge into master dictionaries
   ```bash
   python src/gsd/part2_enrichment/2_generate_mappings/postprocessing.py
   ```

> [!note]
> An OpenAI API key enables the application to access LLM services. [Where to obtain an API key?](https://www.google.com/url?sa=t&source=web&rct=j&opi=89978449&url=https://platform.openai.com/api-keys&ved=2ahUKEwjE1sX_vqSQAxUZL1kFHe88MkgQFnoECA4QAQ&usg=AOvVaw1YhcGDWJXhiKSfmL59Pnfn)

### Project Structure

```bash
.
├── README.md
├── configs                       # YAML-based configuration for models, paths, and tooling
│   ├── base.yaml
│   ├── chroma.yaml               # Persist directories + retriever params
│   ├── models.yaml               # LLM labels + params
│   ├── ollama.yaml               # Ollama configs
│   ├── paths.yaml
│   ├── schemas                       # JSON/schema definitions for bGST data model
│   └── prompts                   # Collection of system prompts in markdown format
├── data
│   ├── inputs                    # Raw/normalized source data for the pipelines
│   │   ├── _resource_template    # Folder template for integrating new resources
│   │   │   ├── metadata
│   │   │   ├── normalized
│   │   │   └── raw
│   │   └── ...                   # Source data + merging audit records, grouped by folders
│   ├── outputs                   # Mapped terms (current/previous) + vectorstore snapshots (previous)
│   │   └── releases
│   └── workspace                 # Vectorstores of current release
│       └── chroma
├── docs                          # Supplementary documentation + notes
├── requirements.txt
├── scripts
│   └── ollama                    # Ollama server helpers (env var + pid management)
│       ├── start_server.py
│       ├── status_server.py
│       └── stop_server.py
├── src                           # Python library code for the GSD pipeline
│   └── gsd
│       ├── __init__.py
│       ├── adapters              # Higher level adapter tools
│       ├── part1_textbook        # EoG term extraction pipeline
│       ├── part2_enrichment      # GSD resource enrichment pipeline
│       ├── cli.py
│       ├── config.py             # Config loaders
│       ├── models.py
│       └── utils.py
└── tests                         # Unit tests
```

### LLM Workflows

| Workflow                          | Description                                                                                                                                                                                                                                                                                                                                                                                                                                                                 | Directory                            |
| --------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------ |
| GST Extraction                    | Extracts and classifies GST from a preprocessed text document, and creates sentence-level citations as supporting evidence. Identify GST entity pairs (i.e. `has_abbr`, `has_formula`). Example parses _Essentials of Glycobiology 4e_ as a Chroma document.                                                                                                                                                                                                                | `src/gsd/part1_textbook/02_extract/` |
| RAG For Term Generation           | Starts with deduplicated glycan structure terms. Retrieve top-k document chunks from the _Essentials of Glycobiology 4e_, and synthesize a term summary in terms of `definition`, `cellular component`, `molecular function`, and `biological process`.                                                                                                                                                                                                                     | `src/gsd/part1_textbook/04_annotate` |
| bGST Enrichment With New Datasets | Starts with a seed GST vectorstore (persist*directory = `src/data/workspace/chroma/gsd/`). Parses query GST entities one at a time - searches against existing term entries from the vectorstore, and decides to i. \_link query to existing entity* or ii. _register new entity_. The vector store is dynamically updated in the iteration, whilst a list of AI term-linking audits is generated for human review (before incorporating into the production GST datasets). | `src/gsd/part2_enrichment/02_link/`  |

<p align="right"><a href="#readme-top">back to top ▲</a></p>

<!-- DATA MODEL -->

## Data

### Data Source

| Resource     | URL                                                    | Entities | Notes                                                       |
| ------------ | ------------------------------------------------------ | -------- | ----------------------------------------------------------- |
| GlycoMotif   | https://glycomotif.glyomics.org/                       | 701      | Secondary: Glydin, UniCarbKB, GlyTouCan, CCRC, GlyGen       |
| Glydin       | https://glycoproteome.expasy.org/epitopes/             |          | Secondary: SugarbindDB, GlycoEpitope, Cummings, BioOligo-DB |
| SugarbindDB  | https://sugarbind.expasy.org/                          | 204      |                                                             |
| GlycoEpitope | https://www.glycoepitope.jp/                           | 173      | Also available at https://glycosmos.org/glycoepitope        |
| Cummings     | https://pubmed.ncbi.nlm.nih.gov/19756298/              |          |                                                             |
| BioOligo-DB  | https://glyco3d.cermav.cnrs.fr/search.php?type=bioligo |          |                                                             |
| Monosac-DB   | https://glycopedia.eu/resources/presentation/          |          |                                                             |
| UniLectin3D  | https://unilectin.unige.ch/unilectin3D/                |          |                                                             |
| GlycoMaple   | https://glycosmos.org/glycomaple/Human                 |          |                                                             |

### Data Model

Describe the core data model(s) used by this project, including how glycan structure terms are represented, stored, and linked to external resources.

- **Primary storage:** (e.g., JSONL, SQLite)

- **Key entities:**

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

<p align="right"><a href="#readme-top">back to top ▲</a></p>

<!-- LICENSE -->

## License

MIT License. Copyright (c) 2025 GlyGen

See `LICENSE` for more details.

<p align="right"><a href="#readme-top">back to top ▲</a></p>

<!-- ACKNOWLEDGEMENTS -->

## Acknowledgements

Placeholder

- Placeholder for contributor/organization 1
- Placeholder for contributor/organization 2
- Placeholder for contributor/organization 3

<p align="right"><a href="#readme-top">back to top ▲</a></p>

<!-- MARKDOWN LINKS & IMAGES -->
<!-- https://www.markdownguide.org/basic-syntax/#reference-style-links -->

[release-shield]: https://img.shields.io/github/release/glygener/glycan-structure-dictionary.svg?style=for-the-badge
[release-url]: https://github.com/glygener/glycan-structure-dictionary/
[issues-shield]: https://img.shields.io/github/issues/glygener/glycan-structure-dictionary.svg?style=for-the-badge
[issues-url]: https://github.com/glygener/glycan-structure-dictionary/issues
[biomarkerkb-shield]: https://img.shields.io/badge/biomarkerkb-link-critical?style=for-the-badge&logo=semantic%20web&logoColor=teal&color=mediumaquamarine
[biomarkerkb-url]: https://biomarkerkb.org/biomarker-search/
[glygen-shield]: https://img.shields.io/badge/glygen-link-critical?style=for-the-badge&logo=semantic%20web&logoColor=teal&color=mediumaquamarine
[glygen-url]: https://www.glygen.org/disease-search/
[wiki-shield]: https://img.shields.io/badge/wiki-link-critical?style=for-the-badge&logo=wikipedia&logoColor=teal&color=mediumaquamarine
[wiki-url]: https://wiki.glygen.org/Glycan_structure_dictionary
[product-screenshot]: bgst_logo.png
[image-shield]: graph.png
[image-url]: graph.png
