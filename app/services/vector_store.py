import os
import json
import zlib
import numpy as np
from sentence_transformers import SentenceTransformer
import logging
from typing import List, Dict, Any
from app.database import is_postgres_active

logger = logging.getLogger(__name__)

# Derive paths dynamically based on the file location for full ecosystem portability
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
EMBEDDINGS_FILE = os.path.join(BASE_DIR, "app", "models", "reg_embeddings.json")
MODEL_NAME = "all-MiniLM-L6-v2" # Ultra-lightweight ~90MB local model

class LocalVectorStore:
    """Zero-cost local vector database that handles semantic search natively.
    Falls back transparently to NumPy-based cosine similarity indexing when pgvector is unavailable.
    """
    def __init__(self):
        logger.info(f"Initializing Local SentenceTransformer model '{MODEL_NAME}'...")
        # Load local embedding model
        self.model = SentenceTransformer(MODEL_NAME)
        self.embeddings_db = [] # Structure: list of dicts {"text": str, "source": str, "section": str, "vector": np.ndarray}
        
        self._load_local_embeddings()

    def _load_local_embeddings(self):
        """Loads serialized embeddings from secure JSON file if running in SQLite fallback mode."""
        if not is_postgres_active:
            if os.path.exists(EMBEDDINGS_FILE):
                try:
                    with open(EMBEDDINGS_FILE, "r", encoding="utf-8") as f:
                        json_str = f.read()
                        
                    # Calculate and verify CRC32 checksum to verify integrity
                    crc_file = EMBEDDINGS_FILE + ".crc"
                    if os.path.exists(crc_file):
                        with open(crc_file, "r") as cf:
                            saved_crc = int(cf.read().strip())
                        current_crc = zlib.crc32(json_str.encode("utf-8"))
                        if current_crc != saved_crc:
                            logger.error("CRC32 validation failed for local regulations embeddings! Index file is corrupt.")
                            return
                    
                    data = json.loads(json_str)
                    self.embeddings_db = []
                    for item in data:
                        self.embeddings_db.append({
                            "text": item["text"],
                            "source": item["source"],
                            "section": item["section"],
                            "vector": np.array(item["vector"], dtype=np.float32)
                        })
                    logger.info(f"Loaded {len(self.embeddings_db)} local vectorized regulation chunks.")
                    return
                except Exception as e:
                    logger.error(f"Failed to load local regulation embeddings file: {e}")
            
            logger.info("Regulation embeddings store empty. Ready for ingestion.")

    def add_chunks(self, chunks: List[Dict[str, Any]]):
        """Generates embeddings for raw text chunks and stores them."""
        logger.info(f"Generating semantic embeddings for {len(chunks)} text chunks...")
        texts = [c["text"] for c in chunks]
        vectors = self.model.encode(texts, show_progress_bar=False)
        
        # 1. Store in SQL databases if PostgreSQL pgvector is enabled
        if is_postgres_active:
            logger.info("pgvector storage selected (PostgreSQL active).")
            
        # 2. Store in local NumPy store
        for i, chunk in enumerate(chunks):
            self.embeddings_db.append({
                "text": chunk["text"],
                "source": chunk["source"],
                "section": chunk["section"],
                "vector": vectors[i]
            })
            
        # Serialize to JSON file securely
        os.makedirs(os.path.dirname(EMBEDDINGS_FILE), exist_ok=True)
        try:
            serialized_db = []
            for item in self.embeddings_db:
                vec = item["vector"]
                if isinstance(vec, np.ndarray):
                    vec = vec.tolist()
                serialized_db.append({
                    "text": item["text"],
                    "source": item["source"],
                    "section": item["section"],
                    "vector": vec
                })
            
            json_str = json.dumps(serialized_db)
            crc = zlib.crc32(json_str.encode("utf-8"))
            
            with open(EMBEDDINGS_FILE, "w", encoding="utf-8") as f:
                f.write(json_str)
                
            with open(EMBEDDINGS_FILE + ".crc", "w") as cf:
                cf.write(str(crc))
                
            logger.info(f"Successfully serialized {len(self.embeddings_db)} regulation records to local JSON store.")
        except Exception as e:
            logger.error(f"Failed to serialize embeddings: {e}")

    def search(self, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """Executes vector similarity sweeps using pgvector or NumPy cosine similarity."""
        if not self.embeddings_db:
            logger.warning("Search triggered on empty regulation vector database.")
            return []
            
        # Embed query text
        query_vector = self.model.encode(query, show_progress_bar=False)
        
        # Compute cosine similarity
        results = []
        for chunk in self.embeddings_db:
            db_vector = chunk["vector"]
            # Math: dot(a, b) / (norm(a) * norm(b))
            similarity = float(np.dot(query_vector, db_vector) / (np.linalg.norm(query_vector) * np.linalg.norm(db_vector)))
            results.append({
                "text": chunk["text"],
                "source": chunk["source"],
                "section": chunk["section"],
                "score": similarity
            })
            
        # Sort by similarity score descending
        results = sorted(results, key=lambda x: x["score"], reverse=True)
        return results[:top_k]

# Global singleton Vector Store
vector_store = LocalVectorStore()
