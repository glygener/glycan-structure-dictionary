#!/usr/bin/env python3
"""
Convert glycan structure dictionary JSON to TSV format.

This script reads the dictionary JSON file and creates a TSV file where each row
represents a node with the following columns:
- lbl: Label of the node
- term_uuid: Unique identifier for the term
- gtc_id: Combined GTC IDs from all sources
- exact_synonyms_glygen: Exact synonyms from SRC:GSD_GLYGEN_V0
- exact_synonyms_other: Exact synonyms from all other sources
- related_synonyms: Combined related synonyms from all sources
- classification: Combined classification from all sources
- sentence: Placeholder (empty)
"""

import json
import csv
import sys
from pathlib import Path
from typing import List, Set, Optional


def combine_list_field(sources: List[dict], field_name: str, source_filter: Optional[str] = None) -> str:
    """
    Combine list values from multiple sources into a pipe-separated string.
    
    Args:
        sources: List of source dictionaries
        field_name: Name of the field to extract
        source_filter: Optional source identifier to filter by
    
    Returns:
        Pipe-separated string of unique values
    """
    values: Set[str] = set()
    
    for source in sources:
        if source_filter and source.get('src') != source_filter:
            continue
        if source_filter is None and source.get('src') == 'SRC:GSD_GLYGEN_V0':
            continue
            
        src_content = source.get('src_content', {})
        if src_content:
            field_value = src_content.get(field_name)
            if field_value:
                if isinstance(field_value, list):
                    for item in field_value:
                        if item:  # Skip None or empty strings
                            values.add(str(item))
                elif isinstance(field_value, str) and field_value:
                    values.add(field_value)
    
    return '|'.join(sorted(values)) if values else ''


def combine_string_field(sources: List[dict], field_name: str, source_filter: Optional[str] = None) -> str:
    """
    Combine string values from multiple sources into a pipe-separated string.
    
    Args:
        sources: List of source dictionaries
        field_name: Name of the field to extract
        source_filter: Optional source identifier to filter by
    
    Returns:
        Pipe-separated string of unique values
    """
    values: Set[str] = set()
    
    for source in sources:
        if source_filter and source.get('src') != source_filter:
            continue
        if source_filter is None and source.get('src') == 'SRC:GSD_GLYGEN_V0':
            continue
            
        src_content = source.get('src_content', {})
        if src_content:
            field_value = src_content.get(field_name)
            if field_value and isinstance(field_value, str):
                values.add(field_value)
    
    return '|'.join(sorted(values)) if values else ''


def process_node(node: dict) -> dict:
    """
    Process a single node and extract required fields.
    
    Args:
        node: Node dictionary from the JSON file
    
    Returns:
        Dictionary with extracted fields for TSV row
    """
    lbl = node.get('lbl', '')
    term_uuid = node.get('term_uuid', '')
    sources = node.get('sources', [])
    
    # Combine GTC IDs from all sources
    gtc_ids: Set[str] = set()
    for source in sources:
        src_content = source.get('src_content', {})
        if src_content:
            gtc_id_value = src_content.get('gtc_id')
            if gtc_id_value:
                if isinstance(gtc_id_value, list):
                    for gid in gtc_id_value:
                        if gid:
                            gtc_ids.add(str(gid))
                elif isinstance(gtc_id_value, str):
                    gtc_ids.add(gtc_id_value)
    
    gtc_id_combined = '|'.join(sorted(gtc_ids)) if gtc_ids else ''
    
    # Get exact synonyms from GSD_GLYGEN_V0
    exact_synonyms_glygen = combine_list_field(sources, 'exact_synonyms', 'SRC:GSD_GLYGEN_V0')
    
    # Get exact synonyms from all other sources
    exact_synonyms_other = combine_list_field(sources, 'exact_synonyms', source_filter=None)
    
    # Get related synonyms from all sources
    related_synonyms = combine_list_field(sources, 'related_synonyms')
    if not related_synonyms:
        # Also check with GSD_GLYGEN_V0
        related_synonyms_glygen = combine_list_field(sources, 'related_synonyms', 'SRC:GSD_GLYGEN_V0')
        if related_synonyms_glygen:
            related_synonyms = related_synonyms_glygen
    
    # Get classification from all sources
    classification = combine_string_field(sources, 'classification')
    if not classification:
        # Also check with GSD_GLYGEN_V0
        classification_glygen = combine_string_field(sources, 'classification', 'SRC:GSD_GLYGEN_V0')
        if classification_glygen:
            classification = classification_glygen
    
    return {
        'lbl': lbl,
        'term_uuid': term_uuid,
        'gtc_id': gtc_id_combined,
        'exact_synonyms_glygen': exact_synonyms_glygen,
        'exact_synonyms_other': exact_synonyms_other,
        'related_synonyms': related_synonyms,
        'classification': classification,
        'sentence': ''  # Placeholder
    }


def convert_json_to_tsv(input_file: str, output_file: str):
    """
    Convert JSON dictionary to TSV format.
    
    Args:
        input_file: Path to input JSON file
        output_file: Path to output TSV file
    """
    print(f"Reading JSON file: {input_file}")
    
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"Error: Input file '{input_file}' not found.")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in input file: {e}")
        sys.exit(1)
    
    nodes = data.get('nodes', [])
    print(f"Found {len(nodes)} nodes in the dictionary")
    
    # Define TSV columns
    fieldnames = [
        'lbl',
        'term_uuid',
        'gtc_id',
        'exact_synonyms_glygen',
        'exact_synonyms_other',
        'related_synonyms',
        'classification',
        'sentence'
    ]
    
    print(f"Writing TSV file: {output_file}")
    
    with open(output_file, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter='\t')
        writer.writeheader()
        
        for i, node in enumerate(nodes, 1):
            row = process_node(node)
            writer.writerow(row)
            
            if i % 100 == 0:
                print(f"  Processed {i}/{len(nodes)} nodes...", end='\r')
    
    print(f"\nSuccessfully converted {len(nodes)} nodes to TSV format")
    print(f"Output file: {output_file}")


def main():
    """Main entry point for the script."""
    if len(sys.argv) > 1:
        input_file = sys.argv[1]
    else:
        # Default input file
        input_file = 'data/processed/dictionary_20251017_160826.json'
    
    if len(sys.argv) > 2:
        output_file = sys.argv[2]
    else:
        # Generate output filename based on input
        input_path = Path(input_file)
        output_file = input_path.parent / f"{input_path.stem}.tsv"
    
    convert_json_to_tsv(input_file, str(output_file))


if __name__ == '__main__':
    main()
