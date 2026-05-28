import os
import re
import logging
from app.services.vector_store import vector_store

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CORPUS_PATH = os.path.join(base_dir, "data", "regulations_corpus.txt")

def parse_section_aware_corpus(file_path: str):
    """Parses text document using [DOCUMENT: ...] and [SECTION: ...] headers."""
    logger.info(f"Opening corpus file at {file_path}...")
    
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Corpus file not found: {file_path}")
        
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
        
    # Split content by [DOCUMENT: tags
    doc_splits = content.split("[DOCUMENT: ")
    chunks = []
    
    for split in doc_splits:
        if not split.strip():
            continue
            
        # Extract document source name
        doc_match = re.match(r"^([A-Za-z0-9_]+)\]", split)
        if not doc_match:
            continue
            
        doc_source = doc_match.group(1)
        doc_body = split[doc_match.end():]
        
        # Split document by [SECTION: tags
        section_splits = doc_body.split("[SECTION: ")
        for sec_split in section_splits:
            if not sec_split.strip():
                continue
                
            sec_match = re.match(r"^([^\]]+)\]", sec_split)
            if not sec_match:
                continue
                
            section_name = sec_match.group(1)
            text_body = sec_split[sec_match.end():].strip()
            
            # Formulate cohesive RAG context chunk
            chunks.append({
                "text": f"Source: {doc_source} | Section: {section_name}\nContent: {text_body}",
                "source": doc_source,
                "section": section_name
            })
            
    logger.info(f"Parsed {len(chunks)} discrete section-aware regulation chunks.")
    return chunks

def run_ingestion():
    try:
        chunks = parse_section_aware_corpus(CORPUS_PATH)
        # Vectorize and save via local vector store
        vector_store.add_chunks(chunks)
        logger.info("Regulation ingestion completed successfully.")
    except Exception as e:
        logger.error(f"Failed to ingest regulations: {e}")

if __name__ == "__main__":
    run_ingestion()
