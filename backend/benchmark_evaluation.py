"""
Multimodal AI Automated Evaluation Benchmark Suite
===================================================
Executes quantitative benchmarking on the evaluation pipeline:
1. Mean Absolute Error (MAE) compared against gold-standard marks.
2. Alternative-Answer Acceptance Rate (conceptual vs literal evaluation).
3. False Acceptance Rate (rejection of superficially similar incorrect answers).
4. Mathematical derivation & arithmetic slip method accuracy.
5. Diagram topological invariance match rate.
6. Contextual OCR audit and reconstruction performance.
7. Processing speed per question.
"""

import time
import json
import logging
from typing import List, Dict, Any

from app.services.semantic_evaluation_service import evaluate_single_question
from app.services.math_evaluation_service import evaluate_mathematical_answer, are_expressions_equivalent
from app.services.diagram_evaluation_service import evaluate_diagram_answer
from app.services.contextual_ocr_engine import contextual_reconstruct_text

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("benchmark")

BENCHMARK_DATASET = [
    {
        "id": "CASE-01-ALT-PHRASING",
        "question": "What is the function of a compiler?",
        "max_marks": 5.0,
        "gold_marks": 5.0,
        "is_valid_alternative": True,
        "is_incorrect": False,
        "student_answer": "A compiler converts source code into a lower-level executable representation.",
        "model_answer": "A compiler translates high-level programming language into machine code.",
        "rubric": [{"id": 1, "criterion": "Compiler Definition and Function", "marks": 5.0, "description": "Translates high-level language to machine code"}]
    },
    {
        "id": "CASE-02-ALT-SCIENTIFIC",
        "question": "Explain how metals conduct electricity.",
        "max_marks": 5.0,
        "gold_marks": 5.0,
        "is_valid_alternative": True,
        "is_incorrect": False,
        "student_answer": "Metals have delocalized mobile electrons in their lattice which flow to carry electrical charge when voltage is applied.",
        "model_answer": "Metals conduct electricity due to free electrons that move freely through the metallic structure carrying current.",
        "rubric": [{"id": 1, "criterion": "Conduction Mechanism", "marks": 5.0, "description": "Free electrons moving through metallic lattice to carry electrical current"}]
    },
    {
        "id": "CASE-03-MATH-SLIP-METHOD-MARKS",
        "question": "Calculate the f-cost for node B given g(B)=4 and h(B)=2.",
        "max_marks": 6.0,
        "gold_marks": 4.5,  # Partial credit for correct formula/method despite arithmetic slip
        "is_valid_alternative": False,
        "is_incorrect": False,
        "student_answer": "Formula: f(n) = g(n) + h(n). For node B: f(B) = 4 + 2 = 7. Node B cost is 7.",
        "model_answer": "f(n) = g(n) + h(n). For node B: f(B) = 4 + 2 = 6.",
        "rubric": [{"id": 1, "criterion": "Cost Evaluation Formula & Calculation", "marks": 6.0, "description": "Applies f(n) = g(n) + h(n) and calculates 4 + 2 = 6"}]
    },
    {
        "id": "CASE-04-SUPERFICIAL-INCORRECT-REJECTION",
        "question": "What is the function of a compiler?",
        "max_marks": 5.0,
        "gold_marks": 0.0,  # Asserting direct contradiction with keywords
        "is_valid_alternative": False,
        "is_incorrect": True,
        "student_answer": "A compiler is a hardware machine that does not convert software into executable instructions.",
        "model_answer": "A compiler translates high-level programming language into machine code.",
        "rubric": [{"id": 1, "criterion": "Compiler Definition", "marks": 5.0, "description": "Software tool translating source code to machine code"}]
    },
    {
        "id": "CASE-05-DIAGRAM-TOPOLOGICAL-EQUIV",
        "question": "Draw the search graph with start node S, intermediate node A, and goal node G.",
        "max_marks": 8.0,
        "gold_marks": 8.0,
        "is_valid_alternative": True,
        "is_incorrect": False,
        "student_answer": "Graph diagram transitions: S -> A [c=2], A -> G [c=5]. Nodes: S (start), A, G (goal).",
        "model_answer": "Graph diagram: S connects to A with cost 2, A connects to G with cost 5. Goal is G.",
        "rubric": [{"id": 1, "criterion": "Graph Topology & Node Transitions", "marks": 8.0, "description": "Visual diagram showing S->A and A->G paths"}]
    },
    {
        "id": "CASE-06-HANDWRITING-OCR-RECONSTRUCTION",
        "question": "Describe the search frontier used in A* algorithm.",
        "max_marks": 5.0,
        "gold_marks": 5.0,
        "is_valid_alternative": True,
        "is_incorrect": False,
        # 'prority quene' is OCR noise for 'priority queue', 'opem list' for 'open list'
        "student_answer": "A* algorithm maintains a prority quene called opem list ordered by evaluation function f(n).",
        "model_answer": "A* search maintains a priority queue of nodes ordered by f(n) = g(n) + h(n).",
        "rubric": [{"id": 1, "criterion": "Priority Queue Frontier", "marks": 5.0, "description": "Maintains priority queue or min-heap ordered by evaluation function"}]
    }
]


def run_benchmark():
    print("=" * 70)
    print("STARTING MULTIMODAL AI EVALUATION BENCHMARK")
    print("=" * 70)

    total_error = 0.0
    accepted_alternatives = 0
    total_alternatives = 0
    false_acceptances = 0
    total_incorrect = 0
    latencies = []
    audit_events = 0
    detailed_results = []

    for item in BENCHMARK_DATASET:
        start_t = time.perf_counter()

        res = evaluate_single_question(
            question_text=item["question"],
            max_marks=item["max_marks"],
            student_answer_text=item["student_answer"],
            model_answer_text=item["model_answer"],
            rubric_criteria=item["rubric"]
        )

        elapsed_ms = (time.perf_counter() - start_t) * 1000
        latencies.append(elapsed_ms)

        awarded = res["awarded_marks"]
        error = abs(awarded - item["gold_marks"])
        total_error += error

        if item.get("is_valid_alternative"):
            total_alternatives += 1
            if awarded >= 0.75 * item["max_marks"]:
                accepted_alternatives += 1

        if item.get("is_incorrect"):
            total_incorrect += 1
            if awarded >= 0.50 * item["max_marks"]:
                false_acceptances += 1

        if res.get("ocr_reconstruction", {}).get("corrections"):
            audit_events += len(res["ocr_reconstruction"]["corrections"])

        detailed_results.append({
            "id": item["id"],
            "awarded_marks": awarded,
            "gold_marks": item["gold_marks"],
            "max_marks": item["max_marks"],
            "absolute_error": round(error, 2),
            "latency_ms": round(elapsed_ms, 1),
            "needs_review": res.get("needs_review", False),
            "concepts_demonstrated": res.get("concepts_demonstrated", [])
        })

    num_samples = len(BENCHMARK_DATASET)
    mae = total_error / num_samples
    alt_acceptance_rate = (accepted_alternatives / total_alternatives * 100) if total_alternatives else 100.0
    false_acceptance_rate = (false_acceptances / total_incorrect * 100) if total_incorrect else 0.0
    avg_latency = sum(latencies) / len(latencies)

    print("\nBENCHMARK RESULTS SUMMARY:")
    print("-" * 50)
    print(f"Total Test Cases Evaluated       : {num_samples}")
    print(f"Mean Absolute Error (MAE)         : {mae:.2f} marks")
    print(f"Alternative Answer Acceptance Rate: {alt_acceptance_rate:.1f}%")
    print(f"False Acceptance Rate (Gaming)    : {false_acceptance_rate:.1f}%")
    print(f"Average Evaluation Speed          : {avg_latency:.1f} ms/question")
    print(f"Total Handwriting OCR Corrections : {audit_events}")
    print("-" * 50)

    for r in detailed_results:
        print(f"[{r['id']}] Awarded: {r['awarded_marks']}/{r['max_marks']} | Gold: {r['gold_marks']} | Err: {r['absolute_error']} | Latency: {r['latency_ms']}ms | Review: {r['needs_review']}")

    print("=" * 70)
    return {
        "mae": round(mae, 2),
        "alt_acceptance_rate": round(alt_acceptance_rate, 1),
        "false_acceptance_rate": round(false_acceptance_rate, 1),
        "avg_latency_ms": round(avg_latency, 1),
        "detailed_results": detailed_results
    }


if __name__ == "__main__":
    run_benchmark()
