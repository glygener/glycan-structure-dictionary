import json
import os
from typing import List, Dict
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()

# Initialize ChatOpenAI with GPT-4.1 (GPT-5 was not available yet)
llm = ChatOpenAI(model="gpt-4.1", temperature=0)

def extract_term_and_first_sentence_term(line_data: dict) -> tuple:
    """Extract the main term and first term from sentence."""
    term = line_data.get("term", "")
    sentence = line_data.get("sentence", "")
    
    # Extract first term from sentence
    first_sentence_term = sentence.split()[0] if sentence else ""
    
    return term, first_sentence_term

def process_batch_with_llm(batch_terms: List[str]) -> List[Dict[str, str]]:
    """Process a batch of terms with ChatOpenAI to determine if they are glycan structures and normalize them."""
    
    system_prompt = """You are a glycobiology expert filtering glycan terms from JSONL data for the Glycan Structure Dictionary (GSD). The goal is to retain terms that directly specify a singular glycan's structure, composition, linkage pattern, biosynthetic class (N-, O-, glycolipid, polysaccharide, GPI), well-defined structural features (e.g., bisecting GlcNAc, core fucose), established motifs (e.g., Lewis antigens, CA markers), or precise modification steps (e.g., core-fucosylation, α2,3-sialylation). Retain only if the entire term is relevant and unambiguous; remove if entirely irrelevant (non-structural or vague). Use sentence context to disambiguate. Do not normalize, split, group, or classify yet.
"""

    instructions = """Inclusion Criteria:

Retain if specifies composition (e.g., NeuAc(2)Hex(3)HexNAc(2)), connectivity/linkages (e.g., Neu5Acα2-6Galβ1-4GlcNAc, α2,6-linked sialic acid), classes (e.g., high-mannose N-glycan, core-2 O-glycan), features (e.g., bisecting GlcNAc), motifs (e.g., sialyl Lewis X, Tn antigen, poly-LacNAc), or precise processes (e.g., core-fucosylation, α2,3-sialylation).
Retain pure IUPAC forms if structural (will be handled later).
Retain structural cores extracted implicitly, but for now, decide on the term as given (e.g., retain "core-glycosylation" if structural).

Exclusion Criteria:

Remove non-glycan: glycoproteins (e.g., MUC1), antibodies (anti-glycan Ab), enzymes (galectin-3), metrics (GlycA, M2BPGi), MS peaks (GP1/GP2).
Remove generic: no structural info (e.g., glycan, glycoform, acidic glycans, oligosaccharide without qualifier).
Remove carriers/vague modifiers: e.g., "hyperglycosylated hCG", "IgG glycosylation" if vague; "large asialylated biantennary" if non-structural dominates.
Remove monosaccharides/activated forms (e.g., GlcNAc, UDP-GlcNAc) unless part of larger structural descriptor.
Remove pure linkages without context (but retain linkage-specific like "α2,6-linked sialic acid").

Input: List of ~10 JSON objects: {"term": "...", "term_in_sentence": "...", "metadata": {"source": "...", "pmid": null}}.
Output: JSONL (one line per input term). Each line: JSON with keys "original_term" (the input term unchanged), "decision" ("retain" or "remove").
Output only JSONL lines, starting directly with {"""

    user_prompt = f"Instructions: {instructions}\nPlease analyze these terms:\n" + "\n".join([f"- {term}" for term in batch_terms])

    try:
        response = llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ])
        
        # Parse the JSON response
        response_text = response.content.strip()
        if response_text.startswith("```json"):
            response_text = response_text.split("```json")[1].split("```")[0].strip()
        elif response_text.startswith("```"):
            response_text = response_text.split("```")[1].strip()
            
        results = json.loads(response_text)
        return results
        
    except Exception as e:
        print(f"Error processing batch: {e}")
        # Return default format if parsing fails
        return [{"original_term": term, "normalized_term": "ERROR"} for term in batch_terms]

def append_to_output_file(results: List[Dict[str, str]], output_file: str):
    """Append results to the output JSONL file, preserving Unicode (e.g., Greek letters)."""
    with open(output_file, 'a', encoding='utf-8') as f:
        for result in results:
            f.write(json.dumps(result, ensure_ascii=False) + '\n')

def main():
    DATA_DIR = Path(__file__).parents[2] / "data" / "supp"
    input_file = DATA_DIR / "eog_grouped_terms.jsonl"
    output_file = DATA_DIR / "eog_normalized_terms.jsonl"
    batch_size = 5
    
    # Clear output file if it exists
    if os.path.exists(output_file):
        os.remove(output_file)
    
    print(f"Processing {input_file} in batches of {batch_size}...")
    
    with open(input_file, 'r', encoding='utf-8') as f:
        batch_terms = []
        processed_count = 0
        
        for line_num, line in enumerate(f, 1):
            try:
                data = json.loads(line.strip())
                term, first_sentence_term = extract_term_and_first_sentence_term(data)
                
                # Will use main term for processing
                batch_terms.append(term)
                
                # Process batch when we reach batch_size
                if len(batch_terms) == batch_size:
                    print(f"Processing batch {processed_count // batch_size + 1} (lines {processed_count + 1}-{processed_count + len(batch_terms)})...")
                    
                    results = process_batch_with_llm(batch_terms)
                    append_to_output_file(results, output_file)
                    
                    processed_count += len(batch_terms)
                    batch_terms = []
                    
                    print(f"Processed {processed_count} terms so far...")
                    
            except json.JSONDecodeError as e:
                print(f"Error parsing line {line_num}: {e}")
                continue
        
        # Process remaining terms in the last batch
        if batch_terms:
            print(f"Processing final batch (lines {processed_count + 1}-{processed_count + len(batch_terms)})...")
            results = process_batch_with_llm(batch_terms)
            append_to_output_file(results, output_file)
            processed_count += len(batch_terms)
    
    print(f"Complete! Processed {processed_count} terms.")
    print(f"Results saved to {output_file}")

if __name__ == "__main__":
    main()
