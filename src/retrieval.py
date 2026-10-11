"""Retrieval engine for TraceMind.

Performs dense semantic search over ChromaDB using sentence-transformers/all-MiniLM-L6-v2,
formats evidence for LLM prompt grounding, and computes retrieval similarity metrics.
"""

import os
from typing import List, Dict, Any
from sentence_transformers import SentenceTransformer
import chromadb

from .ingestion import CHROMA_DB_DIR, COLLECTION_NAME, ensure_index_exists

# Minimum cosine/L2 relevance threshold to consider a record related
RELEVANCE_DISTANCE_THRESHOLD = 1.35


class Retriever:
    def __init__(self, collection_name: str = COLLECTION_NAME, db_dir: str = CHROMA_DB_DIR):
        self.db_dir = db_dir
        self.collection_name = collection_name
        self.embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
        self.chroma_client = chromadb.PersistentClient(path=self.db_dir)
        
        # Ensure collection exists; auto-ingest if running on a fresh container
        try:
            self.collection = self.chroma_client.get_collection(name=self.collection_name)
        except Exception:
            ensure_index_exists()
            try:
                self.collection = self.chroma_client.get_collection(name=self.collection_name)
            except Exception:
                self.collection = None

    def search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Queries ChromaDB for semantically similar incident records and runbooks.
        Returns a list of structured evidence items with distance and similarity scores.
        """
        if not self.collection:
            ensure_index_exists()
            try:
                self.collection = self.chroma_client.get_collection(name=self.collection_name)
            except Exception:
                return []

        clean_query = query.strip()
        if not clean_query:
            return []

        query_embedding = self.embedding_model.encode(clean_query).tolist()
        
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
        )

        formatted_results: List[Dict[str, Any]] = []
        if results and results.get("documents") and len(results["documents"]) > 0:
            for idx, doc in enumerate(results["documents"][0]):
                meta = results["metadatas"][0][idx] if results.get("metadatas") else {}
                doc_id = results["ids"][0][idx] if results.get("ids") else f"doc_{idx}"
                dist = results["distances"][0][idx] if results.get("distances") else 0.0
                
                # Approximate semantic confidence score from distance (lower distance = higher similarity)
                # Chroma uses L2/squared L2 by default; normalize to 0.0 - 1.0 range
                sim_score = max(0.0, min(1.0, round(1.0 - (dist / 2.0), 3)))
                is_relevant = dist <= RELEVANCE_DISTANCE_THRESHOLD

                formatted_results.append({
                    "id": doc_id,
                    "title": meta.get("title", doc_id),
                    "source": meta.get("source", "unknown"),
                    "content": doc,
                    "metadata": meta,
                    "distance": round(dist, 4),
                    "similarity_score": sim_score,
                    "is_relevant": is_relevant,
                })

        return formatted_results

    def format_for_prompt(self, results: List[Dict[str, Any]]) -> str:
        """Formats retrieved documents into a structured markdown block for LLM prompt context."""
        if not results:
            return "No historical incidents or runbooks found in knowledge base."

        lines = ["### RETRIEVED HISTORICAL EVIDENCE & RUNBOOKS ###\n"]
        lines.append(
            "CRITICAL INSTRUCTION: You may ONLY cite IDs that appear in this list. "
            "Do not invent citation IDs. If none of these documents explain the failure, "
            "explicitly declare insufficient evidence.\n"
        )

        for i, item in enumerate(results, 1):
            lines.append(f"--- Evidence Record {i} ---")
            lines.append(f"DOCUMENT ID: {item['id']}")
            lines.append(f"SOURCE TYPE: {item['source']}")
            lines.append(f"TITLE: {item['title']}")
            lines.append(f"CONTENT:\n{item['content']}\n")

        return "\n".join(lines)

    def is_evidence_sufficient(self, results: List[Dict[str, Any]]) -> bool:
        """
        Returns False if retrieval returned zero records or if all retrieved
        records exceed the distance threshold (meaning no genuinely relevant context).
        """
        if not results:
            return False
        return any(item.get("is_relevant", False) for item in results)
