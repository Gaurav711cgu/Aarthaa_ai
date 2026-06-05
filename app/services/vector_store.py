import os
import json
import zlib
import numpy as np
import threading
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import logging
from typing import List, Dict, Any
from sqlalchemy import text
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
    """Hybrid vector store supporting pgvector in PostgreSQL, ChromaDB persistent store,
    and a lightweight TF-IDF memory fallback for local execution limits.
    """
    def __init__(self):
        logger.info("Initializing vectorizer for regulatory corpus search...")
        self._lock = threading.Lock()
        self.vectorizer = TfidfVectorizer(
            sublinear_tf=True,
            max_features=20_000,
            ngram_range=(1, 2),  # unigrams + bigrams for better regulatory phrase matching
            stop_words="english"
        )
        self.embeddings_db: List[Dict[str, Any]] = []
        self._tfidf_matrix = None   # sparse matrix
        self._is_fitted = False

        # pgvector Setup
        self.use_pgvector = is_postgres_active
        if self.use_pgvector:
            try:
                logger.info("Attempting to connect to PostgreSQL to initialize pgvector...")
                from app.database import engine
                with engine.begin() as conn:
                    # Create vector extension if possible
                    try:
                        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
                    except Exception as ext_err:
                        logger.warning(f"Could not enable pgvector extension (non-superuser context?): {ext_err}")
                    
                    # Create table regulations
                    conn.execute(text("""
                        CREATE TABLE IF NOT EXISTS regulations (
                            id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                            doc_id      TEXT UNIQUE,
                            chunk_text  TEXT NOT NULL,
                            source      TEXT,
                            section     TEXT,
                            embedding   vector(768),
                            metadata    JSONB DEFAULT '{}'
                        );
                    """))
                    
                    # Create HNSW index
                    try:
                        conn.execute(text("""
                            CREATE INDEX IF NOT EXISTS regs_hnsw ON regulations
                            USING hnsw (embedding vector_cosine_ops)
                            WITH (m = 16, ef_construction = 64);
                        """))
                    except Exception as idx_err:
                        logger.warning(f"Could not create HNSW index: {idx_err}. Falling back to standard index.")
                        conn.execute(text("CREATE INDEX IF NOT EXISTS regs_source_sec ON regulations (source, section);"))
                logger.info("pgvector table regulations and indexes initialized successfully.")
            except Exception as pe:
                logger.error(f"pgvector initialization failed: {pe}. Falling back to ChromaDB/TF-IDF.")
                self.use_pgvector = False

        # Persistent ChromaDB setup (only if pgvector is inactive)
        self.use_chroma = HAS_CHROMA and not self.use_pgvector
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

    # ── Persistence & Fallback ────────────────────────────────────────────────

    def _load_local_embeddings(self):
        """Loads serialized embeddings from secure JSON file."""
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
                    
                    # Populate ChromaDB if empty and active
                    if self.use_chroma:
                        try:
                            if self.chroma_collection.count() == 0:
                                logger.info("Populating ChromaDB collection from JSON embeddings...")
                                embeddings = self._tfidf_matrix.toarray().tolist()
                                ids = [f"chunk_{i}" for i in range(len(self.embeddings_db))]
                                metadatas = [{"source": item["source"], "section": item["section"]} for item in self.embeddings_db]
                                try:
                                    self.chroma_collection.add(
                                        embeddings=embeddings,
                                        documents=texts,
                                        metadatas=metadatas,
                                        ids=ids
                                    )
                                except Exception as add_err:
                                    logger.warning(f"ChromaDB add failed ({add_err}). Recreating collection...")
                                    self.chroma_client.delete_collection("regulations_collection")
                                    self.chroma_collection = self.chroma_client.create_collection(
                                        name="regulations_collection",
                                        metadata={"hnsw:space": "cosine"}
                                    )
                                    self.chroma_collection.add(
                                        embeddings=embeddings,
                                        documents=texts,
                                        metadatas=metadatas,
                                        ids=ids
                                    )
                                logger.info(f"Successfully populated ChromaDB with {len(ids)} chunks.")
                        except Exception as e:
                            logger.error(f"Failed to populate ChromaDB: {e}")
                    
                    # Populate pgvector if empty and active
                    if self.use_pgvector:
                        self._populate_pgvector_from_db()
                return
            except Exception as e:
                logger.error(f"Failed to load regulation embeddings: {e}")

        logger.info("Regulation embeddings store empty — ready for ingestion.")

    def _populate_pgvector_from_db(self):
        """Populates pgvector database table from local index store if database is currently empty."""
        try:
            from app.database import engine
            with engine.connect() as conn:
                count = conn.execute(text("SELECT COUNT(*) FROM regulations")).scalar()
                if count and int(count) > 0:
                    return
            
            logger.info("Populating pgvector table from local regulation index store...")
            vocab_size = len(self.vectorizer.vocabulary_)
            np.random.seed(2026)
            W = np.random.normal(0, 1.0 / np.sqrt(768), (vocab_size, 768))
            
            with engine.begin() as conn:
                for i, chunk in enumerate(self.embeddings_db):
                    text_val = chunk["text"]
                    source_val = chunk["source"]
                    section_val = chunk["section"]
                    doc_id = f"{source_val}_{section_val}_{i}"
                    
                    tfidf_vec = self.vectorizer.transform([text_val]).toarray()
                    dense_vec = (tfidf_vec @ W)[0].tolist()
                    vec_str = "[" + ",".join(map(str, dense_vec)) + "]"
                    
                    conn.execute(text("""
                        INSERT INTO regulations (doc_id, chunk_text, source, section, embedding, metadata)
                        VALUES (:doc_id, :chunk_text, :source, :section, cast(:embedding AS vector), :metadata)
                        ON CONFLICT (doc_id) DO NOTHING;
                    """), {
                        "doc_id": doc_id,
                        "chunk_text": text_val,
                        "source": source_val,
                        "section": section_val,
                        "embedding": vec_str,
                        "metadata": json.dumps({"source": source_val, "section": section_val})
                    })
            logger.info("pgvector table population completed successfully.")
        except Exception as e:
            logger.error(f"Failed to populate pgvector on startup: {e}")

    def _persist(self):
        """Serializes the current embeddings_db to JSON + CRC32 file."""
        os.makedirs(os.path.dirname(EMBEDDINGS_FILE), exist_ok=True)
        try:
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
        """Adds text chunks and fits the TF-IDF vectorizer on the full corpus."""
        with self._lock:
            logger.info(f"Ingesting {len(chunks)} regulation chunks into TF-IDF store...")

            for chunk in chunks:
                self.embeddings_db.append({
                    "text": chunk["text"],
                    "source": chunk["source"],
                    "section": chunk["section"],
                })

            # Re-fit TF-IDF on the entire corpus
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
                    try:
                        self.chroma_collection.upsert(
                            embeddings=embeddings,
                            documents=texts,
                            metadatas=metadatas,
                            ids=ids
                        )
                    except Exception as upsert_err:
                        logger.warning(f"ChromaDB upsert failed ({upsert_err}). Recreating collection...")
                        self.chroma_client.delete_collection("regulations_collection")
                        self.chroma_collection = self.chroma_client.create_collection(
                            name="regulations_collection",
                            metadata={"hnsw:space": "cosine"}
                        )
                        self.chroma_collection.add(
                            embeddings=embeddings,
                            documents=texts,
                            metadatas=metadatas,
                            ids=ids
                        )
                    logger.info("ChromaDB persistent collection updated successfully.")
                except Exception as e:
                    logger.error(f"Failed to update ChromaDB collection: {e}")

            # Update pgvector PostgreSQL DB
            if self.use_pgvector:
                try:
                    from app.database import engine
                    vocab_size = len(self.vectorizer.vocabulary_)
                    np.random.seed(2026)
                    W = np.random.normal(0, 1.0 / np.sqrt(768), (vocab_size, 768))
                    
                    logger.info("Updating pgvector table with new chunks...")
                    with engine.begin() as conn:
                        for i, chunk in enumerate(chunks):
                            text_val = chunk["text"]
                            source_val = chunk["source"]
                            section_val = chunk["section"]
                            doc_id = f"{source_val}_{section_val}_{i}"
                            
                            tfidf_vec = self.vectorizer.transform([text_val]).toarray()
                            dense_vec = (tfidf_vec @ W)[0].tolist()
                            vec_str = "[" + ",".join(map(str, dense_vec)) + "]"
                            
                            conn.execute(text("""
                                INSERT INTO regulations (doc_id, chunk_text, source, section, embedding, metadata)
                                VALUES (:doc_id, :chunk_text, :source, :section, cast(:embedding AS vector), :metadata)
                                ON CONFLICT (doc_id) DO UPDATE SET
                                    chunk_text = EXCLUDED.chunk_text,
                                    embedding = EXCLUDED.embedding,
                                    metadata = EXCLUDED.metadata;
                            """), {
                                "doc_id": doc_id,
                                "chunk_text": text_val,
                                "source": source_val,
                                "section": section_val,
                                "embedding": vec_str,
                                "metadata": json.dumps({"source": source_val, "section": section_val})
                            })
                    logger.info("pgvector table update completed successfully.")
                except Exception as e:
                    logger.error(f"Failed to update pgvector database: {e}")

            logger.info("Vectorizer re-fitted on updated corpus.")

    def search(self, query: str, top_k: int = 4) -> List[Dict[str, Any]]:
        """Returns top_k most relevant chunks using pgvector, ChromaDB, or TF-IDF fallback."""
        if not self._is_fitted or not self.embeddings_db:
            logger.warning("Search triggered on empty regulation store — returning empty results.")
            return []

        # Try querying pgvector first if active
        if self.use_pgvector:
            try:
                from app.database import engine
                vocab_size = len(self.vectorizer.vocabulary_)
                np.random.seed(2026)
                W = np.random.normal(0, 1.0 / np.sqrt(768), (vocab_size, 768))
                
                query_tfidf = self.vectorizer.transform([query]).toarray()
                query_dense = (query_tfidf @ W)[0].tolist()
                query_vec_str = "[" + ",".join(map(str, query_dense)) + "]"
                
                results = []
                with engine.connect() as conn:
                    # Cosine distance: <=>
                    # Cosine similarity = 1 - Cosine distance
                    sql_res = conn.execute(text("""
                        SELECT chunk_text, source, section, 
                               1.0 - (embedding <=> cast(:query_vec AS vector)) as similarity
                        FROM regulations
                        ORDER BY embedding <=> cast(:query_vec AS vector) ASC
                        LIMIT :top_k;
                    """), {
                        "query_vec": query_vec_str,
                        "top_k": top_k
                    }).fetchall()
                    
                    for row in sql_res:
                        results.append({
                            "text": row[0],
                            "source": row[1],
                            "section": row[2],
                            "score": float(row[3]) if row[3] is not None else 0.8
                        })
                    return results
            except Exception as e:
                logger.error(f"pgvector query execution failed: {e}. Falling back to standard search.")

        # Try querying ChromaDB
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
