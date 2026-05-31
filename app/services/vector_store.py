import os
import json
import zlib

import threading
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import logging
from typing import List, Dict, Any
from app.database import is_postgres_active

try:
    import chromadb
    HAS_CHROMA = True
except ImportError:
    HAS_CHROMA = False

logger = logging.getLogger(__name__)

# Derive paths dynamically based on the file location for full ecosystem portability
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
EMBEDDINGS_FILE = os.path.join(BASE_DIR, "app", "models", "reg_embeddings.json")


class LocalVectorStore:
    """Zero-cost local hybrid vector store using ChromaDB persistent engine with TF-IDF indexing.
    Falls back transparently to scikit-learn memory indexing when ChromaDB is unavailable.
    """
    def __init__(self):
        logger.info("Initializing TF-IDF vectorizer for regulatory corpus search...")
        self._lock = threading.Lock()
        self.vectorizer = TfidfVectorizer(
            sublinear_tf=True,
            max_features=20_000,
            ngram_range=(1, 2),  # unigrams + bigrams for better regulatory phrase matching
            stop_words="english"
        )
        self.embeddings_db: List[Dict[str, Any]] = []
        self._tfidf_matrix = None   # sparse matrix: shape (n_chunks, n_features)
        self._is_fitted = False

        # Persistent ChromaDB setup
        self.use_chroma = HAS_CHROMA
        if self.use_chroma:
            try:
                logger.info("Initializing ChromaDB persistent collection...")
                chroma_path = os.path.join(BASE_DIR, "data", "chroma_db")
                os.makedirs(chroma_path, exist_ok=True)
                self.chroma_client = chromadb.PersistentClient(path=chroma_path)
                self.chroma_collection = self.chroma_client.get_or_create_collection(
                    name="regulations_collection",
                    metadata={"hnsw:space": "cosine"}
                )
                logger.info("ChromaDB persistent collection initialized successfully.")
            except Exception as ce:
                logger.error(f"ChromaDB initialization failed: {ce}. Falling back to standard scikit-learn search.")
                self.use_chroma = False

        self._load_local_embeddings()

    # ── Persistence ───────────────────────────────────────────────────────────

    def _load_local_embeddings(self):
        """Loads serialized embeddings from secure JSON file."""
        if not is_postgres_active:
            if os.path.exists(EMBEDDINGS_FILE):
                try:
                    with open(EMBEDDINGS_FILE, "r", encoding="utf-8") as f:
                        json_str = f.read()

                    # Verify CRC32 checksum to detect file corruption
                    crc_file = EMBEDDINGS_FILE + ".crc"
                    if os.path.exists(crc_file):
                        with open(crc_file, "r") as cf:
                            saved_crc = int(cf.read().strip())
                        current_crc = zlib.crc32(json_str.encode("utf-8"))
                        if current_crc != saved_crc:
                            logger.error("CRC32 validation failed for regulation embeddings — file is corrupt.")
                            return

                    data = json.loads(json_str)
                    self.embeddings_db = data

                    # Re-fit TF-IDF on the loaded corpus
                    if self.embeddings_db:
                        texts = [item["text"] for item in self.embeddings_db]
                        self._tfidf_matrix = self.vectorizer.fit_transform(texts)
                        self._is_fitted = True
                        logger.info(f"Loaded {len(self.embeddings_db)} regulation chunks — TF-IDF re-fitted.")
                        
                        # Populate ChromaDB if empty
                        if self.use_chroma:
                            try:
                                if self.chroma_collection.count() == 0:
                                    logger.info("Populating ChromaDB collection from JSON embeddings...")
                                    embeddings = self._tfidf_matrix.toarray().tolist()
                                    ids = [f"chunk_{i}" for i in range(len(self.embeddings_db))]
                                    metadatas = [{"source": item["source"], "section": item["section"]} for item in self.embeddings_db]
                                    self.chroma_collection.add(
                                        embeddings=embeddings,
                                        documents=texts,
                                        metadatas=metadatas,
                                        ids=ids
                                    )
                                    logger.info(f"Successfully populated ChromaDB with {len(ids)} chunks.")
                            except Exception as e:
                                logger.error(f"Failed to populate ChromaDB: {e}")
                    return
                except Exception as e:
                    logger.error(f"Failed to load regulation embeddings: {e}")

        logger.info("Regulation embeddings store empty — ready for ingestion.")

    def _persist(self):
        """Serializes the current embeddings_db to JSON + CRC32 file."""
        os.makedirs(os.path.dirname(EMBEDDINGS_FILE), exist_ok=True)
        try:
            # Store only text + metadata — vectors are re-computed from text at load time
            serialized = [
                {"text": item["text"], "source": item["source"], "section": item["section"]}
                for item in self.embeddings_db
            ]
            json_str = json.dumps(serialized)
            crc = zlib.crc32(json_str.encode("utf-8"))

            with open(EMBEDDINGS_FILE, "w", encoding="utf-8") as f:
                f.write(json_str)
            with open(EMBEDDINGS_FILE + ".crc", "w") as cf:
                cf.write(str(crc))

            logger.info(f"Serialized {len(self.embeddings_db)} regulation records to JSON store.")
        except Exception as e:
            logger.error(f"Failed to serialize embeddings: {e}")

    # ── Public API ────────────────────────────────────────────────────────────

    def add_chunks(self, chunks: List[Dict[str, Any]]):
        """Adds text chunks and re-fits the TF-IDF vectorizer on the full corpus."""
        with self._lock:
            logger.info(f"Ingesting {len(chunks)} regulation chunks into TF-IDF store...")

            for chunk in chunks:
                self.embeddings_db.append({
                    "text": chunk["text"],
                    "source": chunk["source"],
                    "section": chunk["section"],
                })

            # Re-fit TF-IDF on the entire corpus (incremental update not supported by sklearn)
            texts = [item["text"] for item in self.embeddings_db]
            self._tfidf_matrix = self.vectorizer.fit_transform(texts)
            self._is_fitted = True

            self._persist()

            # Update ChromaDB collection
            if self.use_chroma:
                try:
                    logger.info("Updating ChromaDB collection with new chunks...")
                    embeddings = self._tfidf_matrix.toarray().tolist()
                    ids = [f"chunk_{i}" for i in range(len(self.embeddings_db))]
                    metadatas = [{"source": item["source"], "section": item["section"]} for item in self.embeddings_db]
                    self.chroma_collection.upsert(
                        embeddings=embeddings,
                        documents=texts,
                        metadatas=metadatas,
                        ids=ids
                    )
                    logger.info("ChromaDB persistent collection updated successfully.")
                except Exception as e:
                    logger.error(f"Failed to update ChromaDB collection: {e}")

            logger.info("TF-IDF vectorizer re-fitted on updated corpus.")

    def search(self, query: str, top_k: int = 4) -> List[Dict[str, Any]]:
        """Returns top_k most relevant chunks using ChromaDB or TF-IDF fallback."""
        if not self._is_fitted or not self.embeddings_db:
            logger.warning("Search triggered on empty regulation store — returning empty results.")
            return []

        # Try querying ChromaDB first if active
        if self.use_chroma:
            try:
                query_vec = self.vectorizer.transform([query]).toarray()[0].tolist()
                search_res = self.chroma_collection.query(
                    query_embeddings=[query_vec],
                    n_results=top_k
                )
                
                results = []
                if search_res and search_res["documents"] and len(search_res["documents"][0]) > 0:
                    docs = search_res["documents"][0]
                    metas = search_res["metadatas"][0]
                    # ChromaDB distance score: for cosine similarity, distance is 1 - cosine_similarity
                    # Let's map it back to standard similarity score: similarity = 1 - distance
                    distances = search_res.get("distances", [[0.0] * len(docs)])[0]
                    
                    for i in range(len(docs)):
                        results.append({
                            "text": docs[i],
                            "source": metas[i].get("source", "unknown") if metas[i] else "unknown",
                            "section": metas[i].get("section", "unknown") if metas[i] else "unknown",
                            "score": float(1.0 - distances[i]) if distances else 0.8
                        })
                    return results
            except Exception as e:
                logger.error(f"ChromaDB query execution failed: {e}. Falling back to standard scikit-learn cosine search.")

        # Standard TF-IDF cosine similarity fallback
        query_vec = self.vectorizer.transform([query])
        scores = cosine_similarity(query_vec, self._tfidf_matrix).flatten()

        # Get top_k indices sorted by score descending
        top_indices = scores.argsort()[::-1][:top_k]

        results = []
        for idx in top_indices:
            chunk = self.embeddings_db[idx]
            results.append({
                "text": chunk["text"],
                "source": chunk["source"],
                "section": chunk["section"],
                "score": float(scores[idx]),
            })
        return results


# Global singleton Vector Store
vector_store = LocalVectorStore()
