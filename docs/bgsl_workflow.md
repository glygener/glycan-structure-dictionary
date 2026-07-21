# The bGSL workflow

The **Biomarker Glycan Structure Lexicon (bGSL)** is a controlled vocabulary of glycan terms harmonised across many public sources by an LLM-assisted entity-resolution pipeline. This document explains what bGSL is (and is not), how the workflow builds it, and how heterogeneous surface forms collapse into one entry.

Two companion diagrams sit alongside this file:

- [`bgsl_workflow_diagram.svg`](bgsl_workflow_diagram.svg) — the LangGraph pipeline: nodes, conditional edges, fast-paths, and where the LLM enters.
- [`bgsl_merge_example.svg`](bgsl_merge_example.svg) — a worked Class 1A example (`asialo-GM1`) showing how six raw rows from five sources collapse into one node, and how related concepts (`GA1`, `Gangliotetraosylceramide`) stay separate but get linked by edges.

## What bGSL is (and is not)

**bGSL is a lexicon of glycan *terms*, not a database of glycan *structures*.** Every entry is a name or notation people use for a glycan entity — a canonical epitope name, a shorthand code, a linkage-notation fragment, a composition formula, a monosaccharide residue, an umbrella class. Two entries can refer to the same underlying chemistry and still be kept apart when the naming conventions differ (`asialo-GM1` and `GA1` share GlyTouCan `G21856LC`, but they belong to different naming traditions — see the merge diagram).

**Structural annotations (IUPAC condensed strings, GlyTouCan IDs, WURCS, GlycoCT, glycoconjugate type, aglycon) are carried through from the source dataset as-is.** We treat them as *provenance metadata*, not as ground truth we curate. Their accuracy is the responsibility of the upstream source; verifying or re-annotating them is out of scope for this project.

This is a deliberate design choice. bGSL's job is to unify how the community *talks* about glycans, not to redraw the glycans themselves. Structure-focused resources (GlyTouCan, GlyConnect, GlycoMotif) already exist and do that well.

## Why we're building it

The initiative starts from a concrete question: **which glycans (or glycan features) matter biologically?** Textbook chapters, review articles, and clinical assay descriptions constantly refer to glycan structures that convey a specific function or serve as biomarkers — Lewis antigens in blood typing, sialyl-Lewis X in cancer metastasis, IgG G0F glycoforms in autoimmune disease, LacdiNAc as a stomach-cancer marker, and so on.

Two frustrations motivated bGSL:

1. **The biologically meaningful unit is often a glycan *feature*, not a specific atomic structure.** "Core fucosylation," "bisecting GlcNAc," "high mannose," "polysialylation" — these are the terms literature uses. None map cleanly to a single IUPAC sequence or GlyTouCan accession; each corresponds to a *set* of structures that share a feature. bGSL registers the feature-level term as a first-class entry, so downstream lookups can find "hypersialylated IgG" without having to enumerate every underlying glycoform.

2. **Every source names things differently.** `Lewis x`, `LeX`, `Le^x`, `Lex`, `lewis-x` all mean the same epitope; `asialo-GM1`, `aGM1`, `AGM1`, `Asialo-GM1a` are all the same ganglioside; `chondroitin sulfate C` and `chondroitin-6-sulfate` are two names for one GAG. Any downstream biomarker search that only knows one spelling loses the rest of the evidence. Harmonising these is the core value bGSL adds.

## Sources and their overlap

bGSL currently integrates **17 source datasets** (14 external + 3 curated internal). They overlap heavily — for instance, GlycoEpitope is redistributed inside Glycosmos; Cummings' determinant list is a curated subset of the broader GlycoEpitope-style content; GlycoMotif-GDV re-uses entries from GlycoMotif-GGM with additional community keywords.

We do not try to detect these overlaps at the *dataset* level. Instead, every row from every source is treated as an independent surface-form observation, and semantic equivalents are merged at the *term* level by the pipeline. A term that appears in five sources ends up as **one bGSL node with five source-refs attached**; the parent node keeps every raw label + synonym + description + GlyTouCan ID + glycomotif ID + evidence citation any source contributed. Nothing is discarded during the merge — only the redundant *concept identity* is collapsed.

That means the same bGSL node can (and often does) carry:

- multiple GlyTouCan IDs (different sources cross-referenced different accessions),
- multiple descriptions (kept as a list, source-attributed),
- multiple `raw_term` spellings inside `sources[]`,
- distinct `exact_synonyms` and `abbreviations` slots that curators can browse independently.

## The workflow

The pipeline is a five-node **LangGraph** loop (see [bgsl_workflow_diagram.svg](bgsl_workflow_diagram.svg)). One graph run = one source dataset. The seed vector store grows monotonically: source *N+1* sees every concept locked in by sources 1..N.

**① retrieve.** Similarity search over the bGSL seed store (Chroma + Ollama embeddings). The query is the surface form joined with any known synonyms/abbreviations from the same row. Returns the top-5 candidates with cosine scores.

**② textbook_lookup.** An LLM decides whether to fetch supporting biology context from *Essentials of Glycobiology* (4th edition) via a `query_textbook` RAG tool. Skipped when the top score is either very low (< 0.55 → the LLM will just ADD, no context needed) or very high with a clear margin (≥ 0.7, margin ≥ 0.05 → decision is obvious). Capped at one tool call per term to keep prompts compact.

**③ resolve.** The decision agent. Three deterministic fast-paths short-circuit the LLM:

- **No candidates → ADD.** Nothing to map to.
- **Weak top match with no GTC cross-check → ADD.** Best score below 0.45 *and* the query carries no GlyTouCan ID for the LLM to double-check against.
- **Normalised surface-form match → MAP as `exact_synonym_of`.** After lowercasing, stripping Greek letters, and stripping punctuation, the query equals a candidate's name or one of its synonyms (with vector score ≥ 0.5 as a sanity gate). One case-sensitive carve-out: `i-antigen` (linear poly-LacNAc) vs `I-antigen` (branched poly-LacNAc) — these must stay separate.

When no fast-path fires, the LLM is called with a structured prompt (query + synonyms + candidates + textbook excerpts + curator hints + source metadata) and returns a strict JSON envelope: `{action, mapped_to_uuid, edge_type, rationale}`. The system prompt biases toward **ADD when in doubt** — undoing a wrong merge is much more painful than adding an edge later.

The GlyTouCan-ID fast-path is **disabled** in the current pipeline. Same GTC ID does not mean same concept: the same underlying glycan can be a terminal fragment of an N-glycan in one context and the glycan portion of a glycosphingolipid in another; the resolver treats those as distinct entries.

**④ register.** Persists the decision. **ADD** mints a fresh `GSD:UUID`, inserts a new document into the vector store, and writes to `terms_ai-decisions.jsonl`. **MAP** appends the new surface form to the target node's `exact_synonyms` list, updates the vector-store document in place, writes the decision, and — for `related_synonym_of`, `broad_synonym_of`, `narrow_synonym_of`, `is_a` — also writes an edge to `edges_ai-decisions.jsonl`. `exact_synonym_of` and `abbreviation_of` are handled by attribute update on the parent node, not by emitting a real edge.

**⑤ advance.** Move to the next term, clear per-term messages/candidates, loop. The conditional edge at the bottom of the graph routes back to *retrieve* until every term in the source is processed, then hits END.

## What the merge actually looks like

The [merge example diagram](bgsl_merge_example.svg) walks through `asialo-GM1` end-to-end. The short version:

- Sources like EoG, GSD_GLYGEN_V0, PubDictionaries, Cummings, and GlycoMotif each list "asialo-GM1" (with slightly different casing/formatting).
- The first row registers the node. The next four all hit the surface-form fast-path and get folded into the same node's synonyms.
- Another PubDictionaries row lists `AGM1` — an abbreviation. The LLM fires and returns `action=map, edge_type=abbreviation_of`. `AGM1` lands in the `abbreviations[]` slot on the same node.
- A BioOligo row lists `GA1` — same underlying chemistry, but a distinct name-tradition entity. The LLM returns `action=add, edge_type=has_related_synonym`. `GA1` becomes its own node, linked by a real edge with the comment `"asialo-GM1 has related synonym GA1"`.

The result: one entry for `asialo-GM1` with five sources, five exact synonyms, three abbreviations, two GlyTouCan IDs, and two outgoing relation edges to sibling naming traditions.

## Statistics — v2.0.0-draft (curated, 2026-06-18)

The most recent curated release lives at [`data/outputs/releases/gsd_v2.0.0-draft/master_nodes_curated.json`](../data/outputs/releases/gsd_v2.0.0-draft/master_nodes_curated.json).

| | Count |
|---|---|
| Curated nodes | **1,202** |
| Curated edges | **260** |
| Nodes referencing ≥ 2 sources (i.e. cross-source merged) | **518** (43%) |
| Raw source references | **2,933** |
| Effective collapse ratio | **2,933 → 1,202 (2.4×)** |
| Source datasets integrated | 17 |

### Concept coverage by class (bGSL v1.4.0 classification scheme)

| Tier | Class | Count | Share |
|---|---|---:|---:|
| 1 (canonical named entities) | 1A canonical named glycan entity | 415 | 35% |
| | 1B named recurrent structural / motif-like feature | 92 | 8% |
| | 1C non-GAG homo/hetero-polymer | 57 | 5% |
| 2 (structural descriptors / encodings) | 2A linkage-specified substructure | 138 | 12% |
| | 2B glycan substructure as structural modifier | 42 | 3% |
| | 2C composite descriptive glycan phrase | 28 | 2% |
| | 2D glycoform shorthand code | 86 | 7% |
| | 2E composition formula | 4 | <1% |
| 3 (background vocabulary) | 3A umbrella class / glycoconjugate type | 40 | 3% |
| | 3B monosaccharide / monosaccharide derivative | 124 | 10% |
| | 3C association-defined glycan marker | 16 | 1% |
| — | unclassified / pending review | 160 | 13% |

Class 1A is by far the largest bucket — as expected, since named entities (Lewis antigens, gangliosides, blood group determinants, GAGs) are also the most commonly referenced across sources and see the highest cross-source merge rate.

### Relations captured as edges

| Predicate | Count |
|---|---:|
| `related_synonym_of` | 96 |
| `broad_synonym_of` | 74 |
| `narrow_synonym_of` | 58 |
| `has_related_synonym` | 32 |

These edges capture cross-node relationships the LLM (or a curator hint) determined were real but not synonymous — e.g., `sialyl Lewis a → CA19-9 antigen` (`has_related_synonym`), `blood group H type 3 → H antigen` (`broad_synonym_of`), `Lewis a → Lewis antigens` (`narrow_synonym_of`).

### Source dataset contributions (top 10 by node count)

| Source | Nodes |
|---|---:|
| `SRC:PUBDICT_GLYCAN_MOTIF` | 438 |
| `SRC:EOG_VARKI_4E` (Essentials of Glycobiology 4e) | 322 |
| `SRC:BIOOLIGO` | 238 |
| `SRC:PUBDICT_GLYCONAVI_NAME` | 234 |
| `SRC:PUBDICTIONARIES-GLYCAN-IMAGE` | 222 |
| `SRC:PUBDICT_GLYCOSMOS` | 218 |
| `SRC:GSD_GLYGEN_V0` (legacy GSD v0) | 182 |
| `SRC:GLYCOEPITOPE` | 173 |
| `SRC:GLYCOMOTIF_GGM` | 156 |
| `SRC:SUGARBIND` | 155 |

## What's next

bGSL to date is a **data integration** project: every entry came from an existing public resource, resolved and harmonised by LLM agents. The next phase adds a **literature-mining** stream — our own team's extraction of glycan terms from biomedical texts, feeding new candidate terms into the same pipeline. That work will flow through the same LangGraph resolver (with the seed vectorstore now containing all v2 entries), and the same review-and-merge loop with human curators. From bGSL's perspective, the internal literature stream is just another `SRC:` prefix; the harmonisation machinery is unchanged.
