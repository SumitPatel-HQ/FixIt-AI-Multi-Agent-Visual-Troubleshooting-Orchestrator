import os
import sys
import glob
from pypdf import PdfReader
import chromadb
from sentence_transformers import SentenceTransformer
import logging

# Setup Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Paths
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BACKEND_DIR, "data")
MANUALS_DIR = os.path.join(DATA_DIR, "manuals")
CHROMA_PATH = os.path.join(DATA_DIR, "chroma_db")

def chunk_text(text, chunk_size=500, overlap=50):
    words = text.split()
    chunks = []
    for i in range(0, len(words), chunk_size - overlap):
        chunk = " ".join(words[i:i + chunk_size])
        if len(chunk) > 100: # Filter tiny chunks
            chunks.append(chunk)
    return chunks

def process_pdfs():
    logger.info(f"Checking for manuals in: {MANUALS_DIR}")
    pdf_files = glob.glob(os.path.join(MANUALS_DIR, "*.pdf"))
    
    if not pdf_files:
        logger.warning("No PDF manuals found.")
        return

    # Initialize ChromaDB
    client = chromadb.PersistentClient(path=CHROMA_PATH)
    # Delete existing to rebuild index (for simplicity in dev)
    try:
        client.delete_collection("manuals")
    except:
        pass
    collection = client.get_or_create_collection(name="manuals")

    # Initialize Embedding Model
    model = SentenceTransformer('all-MiniLM-L6-v2')

    total_chunks = 0

    for pdf_path in pdf_files:
        filename = os.path.basename(pdf_path)
        logger.info(f"Processing: {filename}")
        
        try:
            reader = PdfReader(pdf_path)
            full_text = ""
            for page in reader.pages:
                full_text += page.extract_text() + "\n"
            
            chunks = chunk_text(full_text)
            if not chunks:
                continue

            embeddings = model.encode(chunks).tolist()
            ids = [f"{filename}_{i}" for i in range(len(chunks))]
            metadatas = [{"source": filename} for _ in range(len(chunks))]

            collection.add(
                documents=chunks,
                embeddings=embeddings,
                metadatas=metadatas,
                ids=ids
            )
            
            total_chunks += len(chunks)
            logger.info(f"Added {len(chunks)} chunks from {filename}")

        except Exception as e:
            logger.error(f"Failed to process {filename}: {e}")

    logger.info(f"Finished processing. Total chunks indexed: {total_chunks}")

if __name__ == "__main__":
    process_pdfs()
