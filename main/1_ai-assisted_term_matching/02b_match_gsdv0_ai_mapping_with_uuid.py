"""
Script to match source terms from AI results with original terms file
and add term_uuid field based on mapped_to_uuid values for gsdv0_reviewed data.
"""

import json
import sys
from pathlib import Path
from typing import Dict, List

def load_jsonl(file_path: str) -> List[Dict]:
    """Load JSONL file and return list of dictionaries."""
    data = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if line:  # Skip empty lines
                    try:
                        data.append(json.loads(line))
                    except json.JSONDecodeError as e:
                        print(f"Error parsing JSON on line {line_num} in {file_path}: {e}")
                        sys.exit(1)
    except FileNotFoundError:
        print(f"Error: File not found: {file_path}")
        sys.exit(1)
    except Exception as e:
        print(f"Error reading file {file_path}: {e}")
        sys.exit(1)
    
    return data

def save_jsonl(data: List[Dict], file_path: str) -> None:
    """Save list of dictionaries to JSONL file."""
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            for item in data:
                f.write(json.dumps(item, ensure_ascii=False) + '\n')
        print(f"Successfully saved {len(data)} records to {file_path}")
    except Exception as e:
        print(f"Error saving file {file_path}: {e}")
        sys.exit(1)

def main():
    src_path = Path(__file__).parents[2]
    ai_results_path = src_path / "data/raw/gsdv0/archive/terms_ai-decisions_demo.jsonl"
    original_terms_path = src_path / "data/raw/gsdv0/archive/terms_edited.jsonl"
    output_path = src_path / "data/raw/gsdv0/archive/terms_demo.jsonl"

    # Load AI results
    print("Loading AI results...")
    ai_results = load_jsonl(ai_results_path)
    print(f"Loaded {len(ai_results)} AI result entries")
    
    # Load original terms
    print("Loading original terms...")
    original_terms = load_jsonl(original_terms_path)
    print(f"Loaded {len(original_terms)} original term entries")
    
    # Create mapping from source_term to mapped_to_uuid
    term_to_uuid = {}
    for entry in ai_results:
        source_term = entry.get("source_term", "").strip()
        mapped_uuid = entry.get("mapped_to_uuid", "").strip()
        
        if not source_term:
            print(f"Warning: Empty source_term found in AI results: {entry}")
            continue
            
        if not mapped_uuid:
            print(f"Warning: Empty mapped_to_uuid found for source_term '{source_term}': {entry}")
            continue
            
        term_to_uuid[source_term] = mapped_uuid
    
    print(f"Created mapping for {len(term_to_uuid)} terms")
    
    # Track matching statistics
    matched_count = 0
    unmatched_terms = []
    updated_terms = []
    
    # Process each original term
    for term_entry in original_terms:
        normalized_term = term_entry.get("normalized_term", "").strip()
        
        if not normalized_term:
            print(f"Warning: Empty normalized_term found in original terms: {term_entry}")
            continue
        
        # Skip deprecated terms marked as [DISCARD]
        if normalized_term == "[DISCARD]":
            print(f"⚠️  Skipping deprecated term: {term_entry.get('raw_term', 'Unknown')}")
            updated_terms.append(term_entry)  # Keep the entry but don't try to match it
            continue
        
        # Try to find matching UUID
        if normalized_term in term_to_uuid:
            # Add term_uuid field (without mapping_action)
            term_entry["term_uuid"] = term_to_uuid[normalized_term]
            matched_count += 1
            print(f"✓ Matched '{normalized_term}' -> {term_to_uuid[normalized_term]}")
        else:
            unmatched_terms.append(normalized_term)
        
        updated_terms.append(term_entry)
    
    # Check if all AI results were matched
    ai_terms_set = set(term_to_uuid.keys())
    matched_terms_set = set()
    
    for term_entry in original_terms:
        normalized_term = term_entry.get("normalized_term", "").strip()
        if normalized_term in term_to_uuid:
            matched_terms_set.add(normalized_term)
    
    unmatched_ai_terms = ai_terms_set - matched_terms_set
    
    # Count non-discarded terms for accurate statistics
    non_discarded_original_terms = [t for t in original_terms if t.get("normalized_term", "").strip() != "[DISCARD]"]
    
    # Print summary
    discarded_count = len(original_terms) - len(non_discarded_original_terms)
    print(f"\n=== MATCHING SUMMARY ===")
    print(f"Total original terms: {len(original_terms)}")
    print(f"Discarded terms ([DISCARD]): {discarded_count}")
    print(f"Active original terms: {len(non_discarded_original_terms)}")
    print(f"Total AI result entries: {len(ai_results)}")
    print(f"Successfully matched: {matched_count}")
    print(f"Unmatched original terms: {len(unmatched_terms)}")
    print(f"Unmatched AI terms: {len(unmatched_ai_terms)}")
    
    # Report unmatched terms
    if unmatched_terms:
        print(f"\n=== UNMATCHED ORIGINAL TERMS ===")
        for term in sorted(unmatched_terms):
            print(f"  - {term}")
    
    if unmatched_ai_terms:
        print(f"\n=== UNMATCHED AI TERMS ===")
        for term in sorted(unmatched_ai_terms):
            print(f"  - {term}")
    
    # Raise error if there are unmatched terms
    if unmatched_terms or unmatched_ai_terms:
        error_msg = f"Matching failed! Found {len(unmatched_terms)} unmatched original terms and {len(unmatched_ai_terms)} unmatched AI terms."
        print(f"\n❌ ERROR: {error_msg}")
        
        # Optionally save partial results for debugging
        debug_output_path = output_path.replace('.jsonl', '_partial_debug.jsonl')
        save_jsonl(updated_terms, debug_output_path)
        print(f"Partial results saved to {debug_output_path} for debugging")
        
        sys.exit(1)
    
    # Save results if all terms matched
    print(f"\n✅ SUCCESS: All terms matched successfully!")
    save_jsonl(updated_terms, output_path)
    
    # Show some example matches
    print(f"\n=== SAMPLE MATCHES ===")
    for i, term in enumerate(updated_terms[:3]):
        if "term_uuid" in term:
            print(f"{i+1}. '{term['normalized_term']}' -> {term['term_uuid']}")

if __name__ == "__main__":
    main()
