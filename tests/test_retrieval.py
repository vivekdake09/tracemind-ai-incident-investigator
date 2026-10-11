"""Unit tests for src/retrieval.py and ChromaDB semantic search."""

import pytest
from src.retrieval import Retriever


@pytest.fixture(scope="module")
def retriever():
    return Retriever()


def test_retriever_initialization(retriever):
    assert retriever.collection is not None
    assert retriever.collection.count() >= 13  # 8 incidents + 5 runbooks


def test_retriever_search_database_timeout(retriever):
    query = "Database connection timeout expired FATAL connection to database payments failed"
    results = retriever.search(query, top_k=3)
    assert len(results) > 0
    
    # Verify top result is either incident INC-001 or runbook db_timeouts.md
    top_ids = [r["id"] for r in results]
    assert "incident_INC-001" in top_ids or "runbook_db_timeouts.md" in top_ids
    
    # Check fields in result item
    top = results[0]
    assert "id" in top
    assert "similarity_score" in top
    assert "distance" in top
    assert top["similarity_score"] > 0.0


def test_retriever_search_auth_jwt(retriever):
    query = "401 Unauthorized Invalid signature for JWT token mobile API"
    results = retriever.search(query, top_k=3)
    top_ids = [r["id"] for r in results]
    assert "incident_INC-003" in top_ids or "runbook_auth_errors.md" in top_ids


def test_format_for_prompt(retriever):
    results = retriever.search("timeout", top_k=2)
    prompt_str = retriever.format_for_prompt(results)
    assert "### RETRIEVED HISTORICAL EVIDENCE & RUNBOOKS ###" in prompt_str
    assert "DOCUMENT ID:" in prompt_str
    assert "SOURCE TYPE:" in prompt_str


def test_empty_query(retriever):
    results = retriever.search("", top_k=3)
    assert results == []
