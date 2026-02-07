import os
import chromadb
from sentence_transformers import SentenceTransformer
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

# Persistence settings
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
CHROMA_PATH = os.path.join(DATA_DIR, "chroma_db")
MANUALS_DIR = os.path.join(DATA_DIR, "manuals")

# Ensure directories exist
os.makedirs(CHROMA_PATH, exist_ok=True)
os.makedirs(MANUALS_DIR, exist_ok=True)

class RAGEngine:
    def __init__(self):
        try:
            self.client = chromadb.PersistentClient(path=CHROMA_PATH)
            self.collection = self.client.get_or_create_collection(name="manuals")
            # Load embedding model (lightweight)
            self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
            logger.info("RAG Engine initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize RAG Engine: {e}")
            self.collection = None
            self.embedding_model = None

    def retrieve(self, query: str, n_results: int = 3, device_filter: str = None) -> List[str]:
        """
        Retrieves relevant manual chunks for the query.
        """
        if not self.collection or not self.embedding_model:
            logger.warning("RAG Engine not initialized, returning empty context.")
            return []

        try:
            if self.collection.count() == 0:
                return []

            query_embedding = self.embedding_model.encode([query]).tolist()
            
            # Prepare filters if needed
            where_filter = {}
            if device_filter:
                where_filter = {"device_type": device_filter}

            results = self.collection.query(
                query_embeddings=query_embedding,
                n_results=n_results,
                # where=where_filter if device_filter else None # Optional: Filter by device type if we have that metadata
            )

            # Flatten documents list
            documents = results['documents'][0] if results['documents'] else []
            return documents

        except Exception as e:
            logger.error(f"RAG retrieval failed: {e}")
            return []

rag_engine = RAGEngine()
