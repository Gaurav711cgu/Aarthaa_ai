import os
import json
import zlib
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import logging
from typing import List, Dict, Any
from app.database import is_postgres_active

logger = logging.getLogger(__name__)

# Derive paths dynamically based on the file location for full ecosystem portability
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
EMBEDDINGS_FILE = os.path.join(BASE_DIR, "app", "models", "reg_embeddings.json")


class LocalVectorStore:
    """Zero-cost local vector store using TF-IDF + cosine similarity.
    Uses scikit-learn (already a core dependency) — no PyTorch required.
    Falls back transparently to NumPy indexing when pgvector is unavailable.
    """
    def __init__(self):
        logger.info("Initializing TF-IDF vectorizer for regulatory corpus search...")
        # Lightweight TF-IDF vectorizer — sublinear_tf improves short-document retrieval
        self.vectorizer = TfidfVectorizer(
            sublinear_tf=True,
            max_features=20_000,
            ngram_range=(1, 2),  # unigrams + bigrams for better regulatory phrase matching
            stop_words="english"
        )
        self.embeddings_db: List[Dict[str, Any]] = []
        self._tfidf_matrix = None   # sparse matrix: shape (n_chunks, n_features)
        self._is_fitted = False

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
        logger.info("TF-IDF vectorizer re-fitted on updated corpus.")

    def search(self, query: str, top_k: int = 4) -> List[Dict[str, Any]]:
        """Returns top_k most relevant chunks using TF-IDF cosine similarity."""
        if not self._is_fitted or not self.embeddings_db:
            logger.warning("Search triggered on empty regulation store — returning empty results.")
            return []

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
