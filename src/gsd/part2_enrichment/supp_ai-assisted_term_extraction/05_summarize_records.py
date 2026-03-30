import json
from typing import List, Dict
from time import sleep
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()

llm = ChatOpenAI(model="gpt-4.1", temperature=0) # N-Linked Composition, N-Linked Code

system_prompt = """You are a glycobiology expert processing glycan terms for the Glycan Structure Dictionary. Given a glycan term, a list of original terms, and a concatenated string of descriptions from multiple entries, generate:
1. exact_synonyms: a list of exact synonyms derived from the normalized term and original terms. If no exact synonyms, return empty string.
2. description: a merged description that covers the ideas from the provided descriptions.
3. classification: one classification tag from: IUPAC String, N-Linked Type, O-Linked Core, Glycolipid, Named Functional Motif, Polysaccharide, Polysaccharide Repeating Unit, Monosaccharide, Disaccharide, Others.

Output a single JSON object: {"exact_synonyms": ["syn1", "syn2"], "classification": "tag", "description": "merged description"}"""

def process_group(glycan_term: str, original_terms_flat: List[str], descriptions_str: str) -> Dict:
    user_prompt = f"Glycan term: {glycan_term}\nOriginal terms: {original_terms_flat}\nDescriptions: {descriptions_str}"
    
    try:
        response = llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ])
        
        response_text = response.content.strip()
        if response_text.startswith("```json"):
            response_text = response_text.split("```json")[1].strip()
        elif response_text.startswith("```"):
            response_text = response_text.split("```")[1].strip()
        
        result = json.loads(response_text)
        return result
    except Exception as e:
        print(f"Error processing group for {glycan_term}: {e}")
        return {"exact_synonyms": [], "classification": "Others", "description": "ERROR"}

def main(input_file: str, output_file: str):
    print("Running main")
    with open(input_file, 'r', encoding='utf-8') as f, open(output_file, 'w', encoding='utf-8') as out_f:
        current_term = None
        group = []
        
        for line in f:
            data = json.loads(line.strip())
            term = data.get("normalized_term")
            
            if term != current_term:
                if current_term and group:
                    # Process previous group
                    original_terms_nested = [g["original_terms"] for g in group]
                    evidence_nested = [g["evidence"] for g in group]
                    descriptions = [g["description"] for g in group]
                    descriptions_str = "\n".join(descriptions)
                    original_terms_flat = list(set(sum(original_terms_nested, [])))  # Flatten and unique
                    
                    llm_result = process_group(current_term, original_terms_flat, descriptions_str)
                    
                    output_dict = {
                        "glycan_term": current_term,
                        "exact_synonyms": llm_result.get("exact_synonyms", []),
                        "classification": llm_result.get("classification", "Others"),
                        "description": llm_result.get("description", ""),
                        "original_terms": original_terms_nested,
                        "evidence": evidence_nested
                    }
                    out_f.write(json.dumps(output_dict, ensure_ascii=False) + "\n")
                    print(f"Processed term: {current_term}")
                    print(f"Exact Synonyms: {llm_result.get('exact_synonyms', [])}")
                    print(f"Classification: {llm_result.get('classification', 'Others')}")
                    print(f"Description: {llm_result.get('description', '')}")
                    print(f"Original Terms: {original_terms_nested}")
                    print(f"Evidence: {evidence_nested}")
                    print("\n\n")
                    sleep(1)

                current_term = term
                group = [data]
            else:
                group.append(data)
        
        # Process last group
        if current_term and group:
            original_terms_nested = [g["original_terms"] for g in group]
            evidence_nested = [g["evidence"] for g in group]
            descriptions = [g["description"] for g in group]
            descriptions_str = "\n".join(descriptions)
            original_terms_flat = list(set(sum(original_terms_nested, [])))
            
            llm_result = process_group(current_term, original_terms_flat, descriptions_str)
            
            output_dict = {
                "glycan_term": current_term,
                "exact_synonyms": llm_result.get("exact_synonyms", []),
                "classification": llm_result.get("classification", "Others"),
                "description": llm_result.get("description", ""),
                "original_terms": original_terms_nested,
                "evidence": evidence_nested
            }
            out_f.write(json.dumps(output_dict, ensure_ascii=False) + "\n")

DATA_DIR = Path(__file__).parents[2] / "data" / "supp"
input_file = DATA_DIR / "terms_normalized8a.jsonl"
output_file = DATA_DIR / "terms_normalized9.jsonl"

if __name__ == "__main__":
    main(input_file, output_file)