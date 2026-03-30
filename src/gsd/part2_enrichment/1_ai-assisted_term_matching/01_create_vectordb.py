# Create a Chroma vector database from the raw Essentials of Glycobiology JSONL file
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma
#from langchain_graph_retriever.transformers import ShreddingTransformer
from dotenv import load_dotenv

import json
from uuid import uuid4
from pathlib import Path

load_dotenv()
### In the root directory of your project, create a file named .env and add your environment variables in a KEY=VALUE format.
# Example:
# OPENAI_API_KEY="xxxxx"

INPUT_FILE_NAME = "terms_edited.jsonl"
OUTPUT_FILE_NAME = "terms_demo.jsonl"
COLLECTION_NAME = "glycan_structure_dictionary" # Vector store collection name
EMBEDDING_MODEL = "text-embedding-3-small"

src_dir = Path(__file__).parents[2]
input_file = src_dir / "data/raw/src_gsdv0/archive" / INPUT_FILE_NAME
persist_dir = src_dir / "data/vector_store"

embeddings = OpenAIEmbeddings(model=EMBEDDING_MODEL)

# Convert JSON entries to Document objects
documents = []
with open(input_file, 'r', encoding='utf-8') as f:
    for line in f:
        entry = json.loads(line)

        # Create page_content by combining term, description, and synonyms
        term = entry.get("sub_term", "")
        exact_synonyms = entry.get("exact_synonyms", "")
        description = entry.get("description", "")
        term_uuid = entry.get("term_id", str(uuid4()))

        page_content = f"Term: {term}\nExact Synonyms: {exact_synonyms}\nDescription: {description}\nTerm UUID: {term_uuid}"

        # Combine content and metadata for document metadata
        doc_metadata = {
            "term": term,
            "term_uuid": term_uuid,
        }
    
        # Create document
        doc = Document(
            page_content=page_content,
            metadata=doc_metadata,
            id=term_uuid
        )
        documents.append(doc)

print(f"Created {len(documents)} documents")

# Create vector store
#shredder = ShreddingTransformer()
try:
    vector_store = Chroma.from_documents(
        documents=documents,
        embedding=embeddings,
        COLLECTION_NAME=COLLECTION_NAME,
        persist_directory=persist_dir,
        collection_metadata ={"hnsw:space": "cosine"}
    )
    print(f"Successfully created vector database with {len(documents)} documents")
    print(f"Database saved to: {persist_dir}")
    print(f"Collection name: {COLLECTION_NAME}")
    
    # Test retrieval
    print("\n--- Testing retrieval ---")
    retriever = vector_store.as_retriever(search_kwargs={"k": 2})
    test_query = "lewis antigen A"
    results = retriever.invoke(test_query)
    print(f"Test query: '{test_query}'")
    print(f"Found {len(results)} relevant documents:")
    for i, doc in enumerate(results, 1):
        print(f"{i}. {doc.metadata['term']} (UUID: {doc.id})")
        print(f"Page Content:\n{doc.page_content}")
        print(f"Metadata:\n{doc.metadata}")

except Exception as e:
    print(f"Error creating vector database: {e}")


