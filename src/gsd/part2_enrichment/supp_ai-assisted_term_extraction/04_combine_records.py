import json
import os
from typing import List, Dict
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from dotenv import load_dotenv
from pathlib import Path

# pip install chardet

load_dotenv()

# Initialize ChatOpenAI
llm = ChatOpenAI(model="gpt-4.1", temperature=0)

def process_batch_with_llm(batch_data: List[Dict]) -> List[Dict[str, str]]:
    """Process a batch of terms with ChatOpenAI to group, split, normalize, and describe them."""
    
    system_prompt = """You are a glycobiology expert building the Glycan Structure Dictionary (GSD)."""

    # Build the formatted input text
    formatted_text = """Your task is to process batches of glycan-related terms extracted from scientific text, using provided sentence contexts to group, split, normalize, and describe them. Focus on terms that specify singular glycan structures, compositions, linkages, classes (e.g., N-/O-glycan, glycolipid), features (e.g., bisecting GlcNAc), or motifs (e.g., Lewis antigens).

These terms may be similar/equivalent or compound. Use sentences to disambiguate, confirm relevance, derive definitions/biosynthetic origins, and gather evidence UUIDs.

Task:
1. **Group equivalents**: Merge terms with literally equivalent glycan components into one normalized entry, listing all originals in the output.
2. **Split compounds**: Break compound terms into individual normalized entries if they reference multiple distinct structures.
3. **Normalize**:
   - For IUPAC-like terms , they may be structures or repeating units of a glycan class mentioned in sentence contexts if available; discard if no such name is evident to avoid raw notations.
   - Discard chemically modified monosaccharides.
   - Discard terms characterized by organisms/organ/tissue/cell-specificity.
   - Retain only if the normalized term meets GSD criteria (specific structure/composition/linkage/class/feature/motif/modification); discard irrelevant ones silently. Do not conflate distinct structures based on context.
4. **Describe**: Provide a concise definition or biosynthetic origin based on sentence contexts.
5. **Evidence**: List unique UUIDs from sentences supporting the normalized term/description.

Output:
Pure JSONL (one line per normalized term, separated by new line). Each: {"normalized_term": "normalized term", "original_terms": ["original1", "original2", ...], "description": "definition or origin", "evidence": ["uuid1", "uuid2", ...]}
Output only valid normalized terms; no extras. If no valid terms, output {}. Start directly with {.

"""

    for idx, data in enumerate(batch_data, 1):
        term = data.get("original_term", "")
        sentences = data.get("term_in_sentence", [])
        metadata = data.get("metadata", [])
        
        formatted_text += f'Term {idx}: "{term}"\n\nEvidence sentence(s):\n'
        for sent, meta in zip(sentences, metadata):
            uuid = meta.get("uuid", "")
            formatted_text += f'"{sent}" (sentence uuid: "{uuid}")\n'
        formatted_text += '\n\n'
    
    user_prompt = formatted_text
    #print(user_prompt)
    #quit()
    
    try:
        response = llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ])
        
        # Parse the JSON response
        response_text = response.content.strip()
        if response_text.startswith("```json"):
            response_text = response_text.split("```")
        elif response_text.startswith("```"):
            response_text = response_text.split("```")[1].strip()
            
        # Parse as JSONL: split by lines and load each
        results = []
        for line in response_text.splitlines():
            line = line.strip()
            if line:
                try:
                    result = json.loads(line)
                    results.append(result)
                except json.JSONDecodeError as parse_err:
                    print(f"Failed to parse line: {line}. Error: {parse_err}")
                    # Optionally, append an error entry
                    results.append({"normalized_term": "UNKNOWN", "description": "ERROR", "evidence": []})
        
        return results
        
    except Exception as e:
        print(f"Error processing batch: {e}")
        # Return default format if parsing fails
        return [{"normalized_term": data["term"], "description": "ERROR", "evidence": []} for data in batch_data]

def append_to_output_file(results: List[Dict[str, str]], output_file: str):
    """Append results to the output JSONL file."""
    with open(output_file, 'a', encoding='utf-8') as f:
        for result in results:
            f.write(json.dumps(result, ensure_ascii=False) + '\n')

def main():
    DATA_DIR = Path(__file__).parents[2] / "data" / "supp"
    input_file = DATA_DIR / "terms_normalized3.jsonl"
    output_file = DATA_DIR / "terms_normalized4.jsonl"
    
    # Clear output file if it exists
    if os.path.exists(output_file):
        os.remove(output_file)
    
    print(f"Processing {input_file}...")
    
    with open(input_file, 'r', encoding='utf-8') as f:
        data_list = []
        for line_num, line in enumerate(f, 1):
            try:
                data = json.loads(line.strip())
                data_list.append(data)
            except json.JSONDecodeError as e:
                print(f"Error parsing line {line_num}: {e}")
                continue
    
    processed_count = 0
    i = 0
    while i < len(data_list):
        batch = []
        minimum_size = 5
        maximum_size = 12
        # Add minimum n terms or until end
        while len(batch) < minimum_size and i < len(data_list):
            batch.append(data_list[i])
            i += 1

        # Extend if next is similar, up to maximum_size
        while i < len(data_list) and len(batch) < maximum_size:
            next_data = data_list[i]
            last_term = batch[-1]["original_term"].lower()
            next_term = next_data["original_term"].lower()
            if next_term[:4] == last_term[:4] or next_term == last_term:
                batch.append(next_data)
                i += 1
            else:
                break
        
        if batch:
            print(f"Processing batch of {len(batch)} terms (starting from term {processed_count + 1})...")
            results = process_batch_with_llm(batch)
            append_to_output_file(results, output_file)
            processed_count += len(batch)
            print(f"Processed {processed_count} terms so far...")
    
    print(f"Complete! Processed {processed_count} terms.")
    print(f"Results saved to {output_file}")

if __name__ == "__main__":
    main()