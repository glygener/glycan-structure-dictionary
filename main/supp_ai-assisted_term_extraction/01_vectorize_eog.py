from uuid import uuid4
import os
import json
import glob
from pathlib import Path

from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma
from langchain_text_splitters import RecursiveCharacterTextSplitter

#quit() # Stop: this script is only meant to be run once - to create the vector store.

DATA_DIR = Path(__file__).parents[2] / "data" / "supp"

# Directory for ChromaDB
persist_directory = DATA_DIR / "vector_store"

input_directory = DATA_DIR / "essentials_of_glycobiology" / "raw_txt"

embeddings = OpenAIEmbeddings(model="text-embedding-3-small")

chapter_files = sorted(glob.glob(str(input_directory / "ch*.txt")))
if not chapter_files:
    raise FileNotFoundError(f"No chapter files found in {input_directory}")

raw_docs = []
for fp in chapter_files:
    chapter_id = os.path.splitext(os.path.basename(fp))[0]
    with open(fp, "r", encoding="utf-8") as f:
        text = f.read()
    raw_docs.append(
        Document(
            page_content=text,
            metadata={"chapter": chapter_id}
        )
    )
print(f"Loaded {len(raw_docs)} chapters.")

#############################################################################

text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=200,
    separators=["\n\n", "\n", ". ", ", ", " ", ""],
    keep_separator='end',
)

chunks = text_splitter.split_documents(raw_docs)
print(f"Split into {len(chunks)} chunks.")

for chunk in chunks:
    chunk.metadata["id"] = str(uuid4())
    
#print first 3 chunks
for i, chunk in enumerate(chunks[:3]):
    print(f"Chunk {i+1}:\n{chunk.page_content}.\nMetadata: {chunk.metadata}\n")

##############################################################################

os.makedirs(persist_directory, exist_ok=True)
jsonl_path = DATA_DIR / "eog_chunks.jsonl"
with open(jsonl_path, "w", encoding="utf-8") as f:
    for chunk in chunks:
        record = {
            "content": chunk.page_content,
            "metadata": chunk.metadata,
        }
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
        
print(f"Saved {len(chunks)} chunks to {jsonl_path}.")

##############################################################################

vector_store = Chroma.from_documents(
    collection_name="essentials_of_glycobiology",
    embedding=embeddings,
    persist_directory=persist_directory,
    documents=chunks,
)