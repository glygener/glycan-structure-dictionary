# JSON to TSV Converter

## Overview

This script (`convert_to_tsv.py`) converts the glycan structure dictionary from JSON format to TSV (Tab-Separated Values) format. Each row in the TSV file represents a node from the dictionary with carefully extracted and combined fields from multiple sources.

## Output Format

The TSV file contains the following columns:

1. **lbl**: Label of the node (from the node's `lbl` field)
2. **term_uuid**: Unique identifier for the term (from the node's `term_uuid` field)
3. **gtc_id**: Combined GTC IDs from all sources, pipe-separated (|)
4. **exact_synonyms_glygen**: Exact synonyms from `SRC:GSD_GLYGEN_V0` source only, pipe-separated (|)
5. **exact_synonyms_other**: Exact synonyms from all sources except `SRC:GSD_GLYGEN_V0`, pipe-separated (|)
6. **related_synonyms**: Combined related synonyms from all sources, pipe-separated (|)
7. **classification**: Combined classification values from all sources, pipe-separated (|)
8. **sentence**: Placeholder column (empty, reserved for future use)

## Usage

### Basic Usage (with defaults)

```bash
python convert_to_tsv.py
```

This will:
- Read from: `data/processed/dictionary_20251017_160826.json`
- Write to: `data/processed/dictionary_20251017_160826.tsv`

### Specify Input File

```bash
python convert_to_tsv.py path/to/input.json
```

This will:
- Read from: `path/to/input.json`
- Write to: `path/to/input.tsv` (same directory and name, with .tsv extension)

### Specify Both Input and Output Files

```bash
python convert_to_tsv.py path/to/input.json path/to/output.tsv
```

## Features

- **Field Combination**: Values from multiple sources are combined and deduplicated
- **Source Filtering**: Exact synonyms are separated by source (GlyGen vs. others)
- **Pipe Separation**: Multiple values within a field are separated by `|`
- **Alphabetical Sorting**: Combined values are sorted alphabetically
- **Empty Handling**: Empty fields are represented as empty strings (no null values)
- **Progress Indication**: Shows progress while processing large files

## Example Output

```
lbl	term_uuid	gtc_id	exact_synonyms_glygen	exact_synonyms_other	related_synonyms	classification	sentence
6-sulfo-sialyl Lewis x	GSD:1b3b03a6-b82a-52ea-a699-0da8aa1f3abc	G80722US	6-sulfo SLe^x|6-sulfo SLex		Named Functional Motif	
β3-linked glucose	GSD:864352e3-4959-5d32-b9e3-b0973c89c4a1			1-3-linked β-Glc	Polysaccharide Repeating Unit	
```

## Requirements

- Python 3.6 or higher
- Standard library only (no external dependencies)

## Notes

- The script handles both list and string values for fields
- Null values and empty strings are filtered out
- All output is UTF-8 encoded
- The TSV format can be easily imported into spreadsheet applications or databases
