config.py
Central place for configuration loading and validation. It usually reads YAML, JSON, environment variables, model names, paths, thresholds, top-k values, and makes them available in a consistent way.

models.py
Defines the project’s structured data objects. In your case, this would hold things like GlycanMention, MergedTerm, QueryEntity, GSDEntity, ResolutionDecision, and maybe provenance records.
Related concept: this is your data contract. It tells every script what shape the input/output data should have.

utils.py
Small reusable helper functions that do not belong to one specific workflow step. Examples: text normalization, safe JSONL writing, hashing, timestamp generation, sentence tag parsing, and dedup helpers.
Important rule: utils.py should stay boring and generic. If it starts holding major business logic, it becomes a junk drawer.

adapters/ scripts
These are wrappers around external tools or systems, so the rest of your code does not directly depend on their raw APIs.

For example:

gliner.py: run GLiNER NER extraction

ollama.py: send prompts to local Ollama models and parse responses

chroma.py: query/update the ChromaDB vector store

web.py: optional web lookup or URL fetching utilities


