from langchain_core.tools import tool
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate

from dotenv import load_dotenv
from uuid import uuid4
from pathlib import Path
import ast
import json

from llm_prompts import MAPPING_PROMPT

load_dotenv()

INPUT_FILE_NAME = "terms_edited.jsonl"
OUTPUT_FILE_NAME = "terms_ai-decisions_demo.jsonl"
COLLECTION_NAME = "glycan_structure_dictionary"
EMBEDDING_MODEL = "text-embedding-3-small"
LARGE_LANGUAGE_MODEL = "gpt-4.1"
LOG_FILE_NAME = "ai_mapping_demo.log"

src_dir = Path(__file__).parents[2]
input_file = src_dir / "data/raw/src_pubdictionaries/archive" / INPUT_FILE_NAME
output_file = src_dir / "data/raw/src_pubdictionaries/archive" / OUTPUT_FILE_NAME
log_file = src_dir / "data/raw/src_pubdictionaries" / LOG_FILE_NAME
persist_dir = src_dir / "data/vector_store"

embeddings = OpenAIEmbeddings(model=EMBEDDING_MODEL)
vector_store = Chroma(
    persist_directory=persist_dir,
    collection_name=COLLECTION_NAME,
    embedding_function=embeddings
)
print("Loaded existing Chroma vector store...")


def search_glycan_structure(query: str):
    res = vector_store.similarity_search_with_relevance_scores(
        query=query,
        k=5,
        score_threshold=0.3
    )
    retrieval_res = ""
    for doc, score in res:
        retrieval_res += f"{doc.page_content}\n\n"
    return retrieval_res

@tool
def add_new_term(term_name: str) -> dict:
    """
    Adds a new glycan structure to the vector store.
    
    Args:
        vector_store (Chroma): The Chroma vector store instance.
        structure (dict): A dictionary containing glycan structure information.
    """
    
    ### VECTOR STORE HANDLING
    global vector_store
    term_uuid = str(uuid4())

    page_content = f"Term: {term_name}\nExact Synonyms: []\nDescription: \nTerm UUID: {term_uuid}"

    document = Document(
        page_content=page_content,
        metadata={"term": term_name, "uuid": term_uuid},
        id=term_uuid
    )

    vector_store.add_documents(ids = [term_uuid], documents = [document])
    
    ### MAPPING FILE HANDLING
    result = {"source_term": term_name, "mapped_to_uuid": term_uuid, "action": "add"}
    
    # Write to output file
    with open(output_file, 'a', encoding='utf-8') as outfile:
        outfile.write(json.dumps(result, ensure_ascii=False) + "\n")
    
    return result

@tool
def map_to_existing_term(term_name: str, term_uuid: str) -> dict:
    """
    Maps a new term to an existing term in the vector store.
    Args:
        term_name (str): The name of the glycan structure to be updated.
        term_uuid (str): The UUID of the existing glycan structure to map to.
    """
    # VECTOR STORE HANDLING
    global vector_store
    
    retrieved_doc = vector_store.get(ids=[term_uuid])
    retrieved_meta = retrieved_doc['metadatas'][0]
    retrieved_term = retrieved_doc["documents"][0].split("\n")[0].split("Term: ")[1]
    retrieved_synonyms = retrieved_doc["documents"][0].split("\n")[1].split("Exact Synonyms: ")[1]
    if retrieved_synonyms != "":
        retrieved_synonyms = ast.literal_eval(retrieved_synonyms)
    else:
        retrieved_synonyms = []

    if term_name not in retrieved_synonyms or term_name != retrieved_term:
        if len(retrieved_synonyms) == 0:
            updated_synonyms = [term_name]
        else:
            updated_synonyms = retrieved_synonyms + [term_name]
        updated_content = retrieved_doc["documents"][0].replace(str(retrieved_synonyms), str(updated_synonyms))
    else:
        updated_content = retrieved_doc["documents"][0]

    updated_doc = Document(
        page_content=updated_content,
        metadata=retrieved_meta,
        id=term_uuid
        )
    
    vector_store.update_document(document_id=updated_doc.id, document=updated_doc)
    
    ### MAPPING FILE HANDLING
    result = {"source_term": term_name, "mapped_to_uuid": term_uuid, "action": "map"}
    
    # Write to output file
    with open(output_file, 'a', encoding='utf-8') as outfile:
        outfile.write(json.dumps(result, ensure_ascii=False) + "\n")
    
    return result

tools = [add_new_term, map_to_existing_term]
llm = ChatOpenAI(model="gpt-4.1", temperature=0)

# Create the prompt template
prompt = ChatPromptTemplate.from_messages(
    [
        ("system", MAPPING_PROMPT),
        ("human", "{input}"),
        ("placeholder", "{agent_scratchpad}"),
    ]
)


agent = create_tool_calling_agent(llm, tools, prompt)
agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)


with open(input_file, 'r', encoding='utf-8') as infile:
    for line in infile:
        entry = json.loads(line)
        term = entry.get("normalized_term", "[DISCARD]")
        
        # If the term is labeled as "[DISCARD]" or unlabeled, skip the term
        if term == "[DISCARD]":
            continue
        synonyms = entry.get("exact_synonyms", [])
        if synonyms == []:
            synonyms = ""
        else:
            synonyms = "It has synonyms: " + ", ".join(synonyms) + " (do not map synonyms to database)"

        print(f"[System] Processing term: {term}")
        
        # Create a prompt for the agent
        input_text = f"""
        Candidate term: "{term}"
        {synonyms}    
        Potential matches in database:
        {search_glycan_structure(term)}
        
        Analyze the candidate term against potential matches and decide whether to map it to an existing term or add it as a new term.
        """

        response = agent_executor.invoke({"input": input_text}) # Move to LangGraph in next attempt
        
        # Append to log file
        with open(log_file, 'a', encoding='utf-8') as log:
            log.write(f"Processing term: {term}\n")
            log.write(json.dumps(response['output'], ensure_ascii=False) + "\n\n")

