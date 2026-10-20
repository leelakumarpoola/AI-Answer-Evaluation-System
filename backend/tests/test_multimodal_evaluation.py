"""
Automated Test Suite for Multimodal AI Answer Script Evaluation System
======================================================================
Tests:
1. Valid alternative answer acceptance (different wording, same concept).
2. Valid alternative scientific explanations.
3. Alternative mathematical solution methods & SymPy symbolic checks.
4. Method marks vs accuracy marks (partial credit for correct method with arithmetic slip).
5. Rejection of superficially similar / keyword-stuffed incorrect answers.
6. Diagram and visual answer topological invariance.
7. Contextual OCR reconstruction and uncertainty logging.
8. Strict rubric mark bounds (0.0 <= marks <= max_marks).
"""

import pytest
from app.services.math_evaluation_service import (
    are_expressions_equivalent,
    evaluate_mathematical_answer,
    clean_math_expression
)
from app.services.diagram_evaluation_service import (
    extract_diagram_text_labels,
    evaluate_diagram_answer
)
from app.services.contextual_ocr_engine import (
    generate_word_candidates,
    contextual_reconstruct_text
)
from app.services.semantic_evaluation_service import (
    evaluate_concept_coverage,
    evaluate_single_question
)


# ─────────────────────────────────────────────────────────────
# 1. Alternative Concept & Phrasing Tests
# ─────────────────────────────────────────────────────────────

def test_valid_alternative_phrasing_compiler():
    """
    Test Section 6.1:
    Model answer: 'A compiler translates high-level programming language into machine code.'
    Student answer: 'A compiler converts source code into a lower-level executable representation.'
    Must accept the valid alternative wording and award appropriate credit.
    """
    rubric = [{"id": 1, "criterion": "Compiler Definition and Function", "marks": 5.0, "description": "Translates high-level language to machine code"}]
    
    res = evaluate_single_question(
        question_text="What is the function of a compiler?",
        max_marks=5.0,
        student_answer_text="A compiler converts source code into a lower-level executable representation.",
        model_answer_text="A compiler translates high-level programming language into machine code.",
        rubric_criteria=rubric
    )
    
    assert res["awarded_marks"] >= 4.0, f"Expected >= 4.0 marks for valid alternative, got {res['awarded_marks']}"
    assert "Compiler Definition and Function" in res["concepts_demonstrated"]


def test_valid_alternative_scientific_explanation_conduction():
    """
    Test Section 6.2:
    Model answer: 'Metals contain free electrons that move through the material.'
    Student answer: 'Mobile electrons carry charge when a potential difference is applied across a metal.'
    Must recognize scientifically equivalent explanation.
    """
    rubric = [{"id": 1, "criterion": "Mechanism of Electrical Conduction", "marks": 4.0, "description": "Free electrons moving through metal"}]
    
    res = evaluate_single_question(
        question_text="Explain why metals conduct electricity.",
        max_marks=4.0,
        student_answer_text="Mobile electrons carry charge when a potential difference is applied across a metal.",
        model_answer_text="Metals contain free electrons that move through the material.",
        rubric_criteria=rubric
    )
    
    assert res["awarded_marks"] >= 3.0, f"Expected >= 3.0 marks for valid scientific explanation, got {res['awarded_marks']}"


# ─────────────────────────────────────────────────────────────
# 2. Mathematical Evaluation & SymPy Verification Tests
# ─────────────────────────────────────────────────────────────

def test_sympy_symbolic_expression_equivalence():
    """Test Section 6.3: Accepts mathematically equivalent expressions using SymPy."""
    # Factored vs expanded
    equiv, reason = are_expressions_equivalent("(x + 2)*(x + 3)", "x^2 + 5*x + 6")
    assert equiv is True, f"Failed symbolic equivalence check: {reason}"

    # Fraction simplification
    equiv2, reason2 = are_expressions_equivalent("2/4", "1/2")
    assert equiv2 is True, f"Failed fraction check: {reason2}"

    # Scaled equation
    equiv3, reason3 = are_expressions_equivalent("2*x + 4 = 10", "x + 2 = 5")
    assert equiv3 is True, f"Failed equation scaling check: {reason3}"


def test_mathematical_method_marks_with_arithmetic_slip():
    """
    Test Section 4: Award method marks when method is valid even if an arithmetic mistake occurs.
    """
    model_calc = (
        "f(n) = g(n) + h(n)\n"
        "Via A: cost = 2 + 5 = 7\n"
        "Via B: cost = 4 + 2 = 6\n"
        "Therefore path S > B > G has minimum cost 6"
    )
    # Student has correct formula and steps, but slips on arithmetic (writes 4 + 2 = 7 instead of 6)
    student_calc = (
        "Evaluation formula is f(n) = g(n) + h(n)\n"
        "Via A: cost = 2 + 5 = 7\n"
        "Via B: cost = 4 + 2 = 7\n"
        "Therefore path S > B > G is chosen"
    )

    eval_res = evaluate_mathematical_answer(
        student_text=student_calc,
        model_answer_text=model_calc,
        max_marks=10.0
    )

    # Method score should be recognized and credited (> 50%)
    assert eval_res["method_score"] >= 0.50
    assert eval_res["awarded_marks"] >= 5.0
    assert eval_res["needs_review"] is True  # Flagged for professor verification due to arithmetic slip


# ─────────────────────────────────────────────────────────────
# 3. Anti-Gaming / Factually Incorrect Detection Tests
# ─────────────────────────────────────────────────────────────

def test_rejection_of_superficially_similar_incorrect_answer():
    """
    Test Section 14: Factually incorrect answer is not accepted merely because it contains keywords.
    """
    # Student asserts the direct opposite / incorrect statement using keywords
    nonsense_answer = "A compiler is a hardware machine that does not convert software into executable instructions."
    
    rubric = [{"id": 1, "criterion": "Compiler Definition", "marks": 5.0, "description": "Software tool translating source code to machine code"}]

    res = evaluate_single_question(
        question_text="What is the function of a compiler?",
        max_marks=5.0,
        student_answer_text=nonsense_answer,
        model_answer_text="A compiler translates high-level programming language into machine code.",
        rubric_criteria=rubric
    )

    # Should NOT receive full marks
    assert res["awarded_marks"] < 3.0, f"Expected < 3.0 marks for incorrect assertion, got {res['awarded_marks']}"


# ─────────────────────────────────────────────────────────────
# 4. Diagram & Visual Answer Understanding Tests
# ─────────────────────────────────────────────────────────────

def test_diagram_topological_label_extraction():
    """Test Section 5: Diagram labels, nodes, and transitions are extracted and matched."""
    diagram_text = (
        "State graph contains Start node S.\n"
        "Transitions: S -> A with cost 2, S -> B with cost 4.\n"
        "From A -> G cost is 5, B -> G cost is 2.\n"
        "Goal node G is reached."
    )
    labels = extract_diagram_text_labels(diagram_text)
    assert any("S->A" in l for l in labels)
    assert any("B->G" in l for l in labels)
    assert "Start" in labels

    model_diagram = "S -> A, A -> G, S -> B, B -> G"
    res = evaluate_diagram_answer(
        student_text=diagram_text,
        model_answer_text=model_diagram,
        max_marks=5.0
    )
    assert res["label_score"] >= 0.75
    assert res["awarded_marks"] >= 3.5


# ─────────────────────────────────────────────────────────────
# 5. Contextual OCR & Uncertainty Tracking Tests
# ─────────────────────────────────────────────────────────────

def test_contextual_ocr_reconstruction():
    """Test Section 2 & 3: Resolves ambiguous OCR words without inventing unwritten answers."""
    raw_ocr = "A* uses an admisible heurislic functon to find an optmal path."
    
    result = contextual_reconstruct_text(
        raw_ocr_text=raw_ocr,
        question_text="Explain A* search algorithm heuristic optimality",
        model_answer_text="A* uses an admissible heuristic function to find an optimal path."
    )
    
    # Corrections should be documented
    corrected_words = [c["corrected"].lower() for c in result["corrections"]]
    assert "admissible" in corrected_words or "heuristic" in corrected_words
    assert result["overall_confidence"] > 0.0


# ─────────────────────────────────────────────────────────────
# 6. Rubric Bounds & Multi-Criterion Aggregation Tests
# ─────────────────────────────────────────────────────────────

def test_rubric_marks_strictly_bounded():
    """Test Section 8: Total awarded marks never exceed question max_marks and never negative."""
    rubric = [
        {"id": 1, "criterion": "Definition", "marks": 2.0},
        {"id": 2, "criterion": "Evaluation function", "marks": 3.0},
        {"id": 3, "criterion": "Optimality", "marks": 5.0}
    ]
    
    res = evaluate_single_question(
        question_text="Explain A* search",
        max_marks=10.0,
        student_answer_text="A* search algorithm is an optimal heuristic search algorithm with f(n) = g(n) + h(n).",
        model_answer_text="A* is an informed search algorithm using f(n) = g(n) + h(n) that guarantees optimality with admissible heuristic.",
        rubric_criteria=rubric
    )
    
    assert 0.0 <= res["awarded_marks"] <= 10.0
    assert len(res["criterion_evaluations"]) == 3
    for crit in res["criterion_evaluations"]:
        assert 0.0 <= crit["awarded_marks"] <= crit["max_marks"]
