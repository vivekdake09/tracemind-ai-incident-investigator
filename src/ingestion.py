"""Data ingestion pipeline for TraceMind.

Loads synthetic incident records (data/incidents.jsonl) and engineering runbooks
(data/runbooks/*.md), generates dense embeddings with sentence-transformers/all-MiniLM-L6-v2,
and writes them into a rebuildable ChromaDB vector collection.
"""

import os
import glob
import json
from typing import List, Dict, Any, Tuple
from sentence_transformers import SentenceTransformer
import chromadb

# Directory constants
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
INCIDENTS_FILE = os.path.join(DATA_DIR, "incidents.jsonl")
RUNBOOKS_DIR = os.path.join(DATA_DIR, "runbooks")
CHROMA_DB_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "chroma_db")
COLLECTION_NAME = "incidents_and_runbooks"


class DataIngestor:
    def __init__(self, collection_name: str = COLLECTION_NAME, db_dir: str = CHROMA_DB_DIR):
        self.db_dir = db_dir
        self.collection_name = collection_name
        self.embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
        self.chroma_client = chromadb.PersistentClient(path=self.db_dir)
        
        # Reset collection for idempotency
        try:
            self.chroma_client.delete_collection(name=self.collection_name)
        except Exception:
            pass
        self.collection = self.chroma_client.create_collection(
            name=self.collection_name,
            metadata={"description": "Historical incident postmortems and engineering runbooks"}
        )

    def _get_embedding(self, text: str) -> List[float]:
        return self.embedding_model.encode(text).tolist()

    def ingest_incidents(self) -> int:
        """Reads incidents.jsonl and registers each post-mortem into ChromaDB."""
        count = 0
        if not os.path.exists(INCIDENTS_FILE):
            return count

        with open(INCIDENTS_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line_str = line.strip()
                if not line_str:
                    continue
                incident = json.loads(line_str)
                inc_id = incident.get("id")
                
                content = (
                    f"Incident Title: {incident.get('title', '')}\n"
                    f"Description: {incident.get('description', '')}\n"
                    f"Root Cause: {incident.get('root_cause', '')}\n"
                    f"Resolution: {incident.get('resolution', '')}\n"
                    f"Related Logs: {incident.get('related_logs', '')}"
                )
                
                doc_id = f"incident_{inc_id}"
                self.collection.add(
                    documents=[content],
                    metadatas=[{
                        "source": "incident",
                        "raw_id": inc_id,
                        "title": incident.get("title", ""),
                    }],
                    ids=[doc_id],
                    embeddings=[self._get_embedding(content)],
                )
                count += 1
        return count

    def ingest_runbooks(self) -> int:
        """Reads markdown runbooks from data/runbooks/ and registers them into ChromaDB."""
        count = 0
        if not os.path.exists(RUNBOOKS_DIR):
            return count

        for filepath in glob.glob(os.path.join(RUNBOOKS_DIR, "*.md")):
            filename = os.path.basename(filepath)
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
                
            # Extract title from markdown header or fallback to filename
            title = filename
            for line in content.splitlines():
                if line.startswith("# "):
                    title = line.replace("# ", "").strip()
                    break

            doc_id = f"runbook_{filename}"
            self.collection.add(
                documents=[content],
                metadatas=[{
                    "source": "runbook",
                    "file": filename,
                    "title": title,
                }],
                ids=[doc_id],
                embeddings=[self._get_embedding(content)],
            )
            count += 1
        return count

    def run(self) -> Tuple[int, int]:
        """Executes full ingestion pipeline and returns (incident_count, runbook_count)."""
        inc_count = self.ingest_incidents()
        run_count = self.ingest_runbooks()
        return inc_count, run_count


def ensure_index_exists() -> bool:
    """
    Checks if ChromaDB contains the indexed collection.
    If not, triggers ingestion automatically. Essential for ephemeral / cloud deploys.
    """
    try:
        client = chromadb.PersistentClient(path=CHROMA_DB_DIR)
        coll = client.get_collection(name=COLLECTION_NAME)
        if coll.count() > 0:
            return True
    except Exception:
        pass

    ingestor = DataIngestor()
    inc, run = ingestor.run()
    return (inc + run) > 0


if __name__ == "__main__":
    print("Running TraceMind data ingestion pipeline...")
    ingestor = DataIngestor()
    incidents, runbooks = ingestor.run()
    print(f"Ingestion finished: {incidents} incidents and {runbooks} runbooks stored in ChromaDB.")
