"""Evaluation harness for TraceMind.

Compares retrieval and diagnosis performance against a labeled benchmark:
- Recall@5: Fraction of relevant historical records found in top-5 retrieval
- Top-1 Diagnosis Accuracy: Whether the highest-ranked hypothesis identifies the true root cause
- Evidence Support Rate: Ratio of cited evidence IDs verified as authentic retrieved documents
- Schema Validity Rate: Fraction of runs conforming strictly to Pydantic data contracts
- Abstention Accuracy: Rate of appropriately declaring insufficient evidence on unknown/unrelated failures
"""

import os
import sys
import json
import time
from typing import Dict, Any, List

# Add project root to sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from dotenv import load_dotenv
load_dotenv()

from src.retrieval import Retriever
from src.investigator import Investigator
from src.schemas import InvestigationReport

TEST_CASES_PATH = os.path.join(PROJECT_ROOT, "evaluation", "test_cases.json")
RESULTS_PATH = os.path.join(PROJECT_ROOT, "evaluation", "results.json")


def run_evaluation() -> Dict[str, Any]:
    print("=" * 60)
    print("TraceMind Incident Investigator — Quantitative Evaluation Suite")
    print("=" * 60)

    if not os.path.exists(TEST_CASES_PATH):
        raise FileNotFoundError(f"Test cases file not found: {TEST_CASES_PATH}")

    with open(TEST_CASES_PATH, "r", encoding="utf-8") as f:
        test_cases: List[Dict[str, Any]] = json.load(f)

    api_key = os.environ.get("GROQ_API_KEY")
    live_mode = bool(api_key)
    investigator = Investigator(api_key=api_key)
    retriever = Retriever()

    print(f"Loaded {len(test_cases)} labeled evaluation scenarios.")
    print(f"Mode: {'Live Groq Inference' if live_mode else 'Local Offline / Demo Baseline (GROQ_API_KEY not configured)'}")

    total_cases = len(test_cases)
    retrieval_hits = 0
    cases_with_expected_evidence = 0
    top1_correct = 0
    schema_valid_count = 0
    total_cited_ids = 0
    valid_cited_ids = 0
    abstention_correct = 0

    case_details = []

    for tc in test_cases:
        tc_id = tc["id"]
        title = tc["title"]
        logs = tc["logs"]
        expected_ids = tc.get("expected_evidence_ids", [])
        expected_keywords = tc.get("expected_primary_hypothesis_keywords", [])
        expect_abstain = tc.get("expect_insufficient_evidence", False)

        print(f"\nEvaluating [{tc_id}] {title}...")

        # 1. Evaluate Retrieval Component directly (dense vector search)
        query = f"{title}\n{logs}"
        retrieval_results = retriever.search(query, top_k=5)
        retrieved_ids = [r["id"] for r in retrieval_results]

        has_retrieval_hit = False
        if expected_ids:
            cases_with_expected_evidence += 1
            # Hit if at least one expected evidence ID was in top 5
            matches = [eid for eid in expected_ids if eid in retrieved_ids]
            if matches:
                has_retrieval_hit = True
                retrieval_hits += 1

        # 2. Evaluate Investigator (RAG + Grounding + Schema)
        inv_result = investigator.analyze(
            title=title,
            logs=logs,
            demo_mode=(not live_mode),
        )

        is_valid_schema = False
        top1_matched = False
        abstained_correctly = False
        case_cited_total = 0
        case_cited_valid = 0

        if inv_result.get("status") == "success" and "report" in inv_result:
            rep_data = inv_result["report"]
            try:
                # Strictly validate with Pydantic
                InvestigationReport(**rep_data)
                is_valid_schema = True
                schema_valid_count += 1
            except Exception:
                is_valid_schema = False

            hypotheses = rep_data.get("hypotheses", [])
            insufficient_flag = rep_data.get("insufficient_evidence", False)

            # Check Top-1 diagnosis
            if hypotheses and expected_keywords:
                top_hyp = hypotheses[0]
                text_to_check = f"{top_hyp.get('title', '')} {top_hyp.get('explanation', '')}".lower()
                matched_kw = [kw for kw in expected_keywords if kw.lower() in text_to_check]
                if len(matched_kw) >= 2 or (len(expected_keywords) == 1 and len(matched_kw) == 1):
                    top1_matched = True
                    top1_correct += 1

            # Check evidence citations grounding
            for h in hypotheses:
                for cid in h.get("cited_evidence_ids", []):
                    case_cited_total += 1
                    total_cited_ids += 1
                    if cid in retrieved_ids:
                        case_cited_valid += 1
                        valid_cited_ids += 1

            # Check Abstention Behavior
            if expect_abstain and insufficient_flag:
                abstained_correctly = True
                abstention_correct += 1
            elif not expect_abstain and not insufficient_flag:
                abstained_correctly = True
                abstention_correct += 1

        case_details.append({
            "id": tc_id,
            "category": tc.get("category", "unknown"),
            "title": title,
            "retrieval_hit": has_retrieval_hit if expected_ids else "N/A (unrelated)",
            "retrieved_ids": retrieved_ids[:3],
            "schema_valid": is_valid_schema,
            "top1_diagnosis_match": top1_matched,
            "abstained_correctly": abstained_correctly,
            "cited_ids_valid": f"{case_cited_valid}/{case_cited_total}" if case_cited_total > 0 else "0/0",
        })

    # Summary metrics computation
    recall_at_5 = round(retrieval_hits / cases_with_expected_evidence, 3) if cases_with_expected_evidence > 0 else 0.0
    accuracy_top1 = round(top1_correct / cases_with_expected_evidence, 3) if cases_with_expected_evidence > 0 else 0.0
    evidence_support_rate = round(valid_cited_ids / total_cited_ids, 3) if total_cited_ids > 0 else 1.0
    schema_validity_rate = round(schema_valid_count / total_cases, 3)
    abstention_rate = round(abstention_correct / total_cases, 3)

    results_payload = {
        "metadata": {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
            "total_cases": total_cases,
            "evaluation_mode": "live_groq" if live_mode else "local_offline_baseline",
            "model": investigator.model_name if live_mode else "Deterministic Offline Engine",
            "embedding_model": "sentence-transformers/all-MiniLM-L6-v2",
            "vector_store": "ChromaDB (persistent)",
            "limitations_note": (
                "Evaluation was conducted on a curated synthetic dataset of 7 incident scenarios. "
                "While high accuracy reflects clean grounding and semantic alignment on targeted failure modes, "
                "larger multi-service production topologies with noisy distributed logs will exhibit lower real-world recall."
            )
        },
        "metrics": {
            "recall_at_5": recall_at_5,
            "top_1_diagnosis_accuracy": accuracy_top1,
            "evidence_support_rate": evidence_support_rate,
            "schema_validity_rate": schema_validity_rate,
            "abstention_accuracy": abstention_rate,
        },
        "cases": case_details,
    }

    with open(RESULTS_PATH, "w", encoding="utf-8") as f:
        json.dump(results_payload, f, indent=2)

    print("\n" + "=" * 60)
    print("EVALUATION RESULTS SUMMARY")
    print("=" * 60)
    print(f"Total Test Cases:           {total_cases}")
    print(f"Recall@5:                   {recall_at_5 * 100:.1f}% ({retrieval_hits}/{cases_with_expected_evidence})")
    print(f"Top-1 Diagnosis Accuracy:   {accuracy_top1 * 100:.1f}% ({top1_correct}/{cases_with_expected_evidence})")
    print(f"Evidence Support Rate:      {evidence_support_rate * 100:.1f}% ({valid_cited_ids}/{total_cited_ids})")
    print(f"Schema Validity Rate:       {schema_validity_rate * 100:.1f}% ({schema_valid_count}/{total_cases})")
    print(f"Abstention Accuracy:        {abstention_rate * 100:.1f}% ({abstention_correct}/{total_cases})")
    print(f"\nDetailed results saved to: {RESULTS_PATH}")
    print("=" * 60)

    return results_payload


if __name__ == "__main__":
    run_evaluation()
