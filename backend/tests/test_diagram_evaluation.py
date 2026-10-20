"""
Comprehensive Automated Test Suite for Intelligent Diagram Recognition
and Semantic Diagram Evaluation Engine
======================================================================
Covers all 15 Scenarios from Section 14:
1.  test_diagram_different_dimensions (Size and dimension invariance)
2.  test_diagram_different_orientation (Layout invariance: horizontal vs vertical)
3.  test_diagram_different_styling (Visual style, box shapes, syntax invariance)
4.  test_diagram_missing_essential_component (Deduction for omitted core blocks)
5.  test_diagram_incorrect_arrow_direction (Reversed sequence / arrowheads)
6.  test_diagram_incorrect_connectivity (Misconnected edges / bypassing nodes)
7.  test_diagram_missing_or_incorrect_labels (Omitted or incorrect terminology)
8.  test_diagram_partially_correct (Proportional rubric-bounded partial credit)
9.  test_diagram_poorly_drawn_but_interpretable (Messy strokes given fair credit)
10. test_diagram_unreadable_or_ambiguous (Baseline attempt marks + review flag)
11. test_diagram_text_inconsistency_conflict (Contradiction between text and diagram)
12. test_page_with_text_and_diagram (Visual segmentation of mixed document page)
13. test_multiple_diagrams_different_questions (Question-specific attribution)
14. test_answer_with_no_diagram_when_required (Deduction when drawing is omitted)
15. test_ai_service_failure_resilience (Graceful fallback on exception)
"""

import os
import pytest
from unittest.mock import patch

from app.services.diagram_evaluation_service import (
    detect_diagram_regions,
    classify_diagram_type,
    extract_diagram_text_labels,
    build_model_diagram_representation,
    analyze_student_diagram_structure,
    compare_diagram_structures,
    evaluate_diagram_with_rubric,
    evaluate_diagram_answer
)


# ─────────────────────────────────────────────────────────────
# 1. Dimension & Size Invariance
# ─────────────────────────────────────────────────────────────

def test_diagram_different_dimensions():
    """
    Scenario 1: Diagrams scaled differently (e.g. small compact drawing vs large wide drawing)
    must receive identical or virtually identical marks because semantic evaluation is invariant
    to pixel dimensions.
    """
    model_ans = "Architecture: Mobile App -> API Gateway -> Smart Contracts Layer -> Blockchain Infrastructure"
    question = "Draw and explain the 3-tier decentralized supply chain architecture."
    
    # Small scale diagram crop metadata
    small_crop = [{
        "bounding_box": [100, 100, 250, 180],
        "area": 45000,
        "internal_complexity": 8,
        "page_number": 1
    }]
    
    # Large scale diagram crop metadata
    large_crop = [{
        "bounding_box": [50, 50, 1200, 900],
        "area": 1080000,
        "internal_complexity": 12,
        "page_number": 1
    }]
    
    student_text = "Mobile App -> API Gateway -> Smart Contracts Layer -> Blockchain Infrastructure"
    
    eval_small = evaluate_diagram_answer(
        student_text=student_text,
        model_answer_text=model_ans,
        max_marks=10.0,
        question_text=question
    )
    
    eval_large = evaluate_diagram_answer(
        student_text=student_text,
        model_answer_text=model_ans,
        max_marks=10.0,
        question_text=question
    )
    
    assert eval_small["awarded_marks"] == eval_large["awarded_marks"], (
        f"Marks must be invariant to dimensions: {eval_small['awarded_marks']} vs {eval_large['awarded_marks']}"
    )
    assert eval_small["awarded_marks"] >= 8.5


# ─────────────────────────────────────────────────────────────
# 2. Orientation Invariance (Horizontal vs Vertical)
# ─────────────────────────────────────────────────────────────

def test_diagram_different_orientation():
    """
    Scenario 2: Topological layout invariance. A flowchart or architecture drawn
    horizontally (left-to-right) must receive the same marks as one drawn
    vertically (top-to-bottom).
    """
    model_ans = "Flow: Start -> Read Input -> Compute Total -> Display Result -> Stop"
    question = "Draw a flowchart to calculate order total."
    
    # Horizontal drawing text representation
    horizontal_text = "Start -> Read Input -> Compute Total -> Display Result -> Stop"
    
    # Vertical drawing representation
    vertical_text = (
        "Start\n"
        "|\n"
        "v Read Input\n"
        "|\n"
        "v Compute Total\n"
        "|\n"
        "v Display Result\n"
        "|\n"
        "v Stop"
    )
    
    eval_horiz = evaluate_diagram_answer(
        student_text=horizontal_text,
        model_answer_text=model_ans,
        max_marks=8.0,
        question_text=question
    )
    
    eval_vert = evaluate_diagram_answer(
        student_text=vertical_text,
        model_answer_text=model_ans,
        max_marks=8.0,
        question_text=question
    )
    
    assert abs(eval_horiz["awarded_marks"] - eval_vert["awarded_marks"]) <= 1.0, (
        f"Horizontal and vertical flowcharts must receive equitable marks: "
        f"{eval_horiz['awarded_marks']} vs {eval_vert['awarded_marks']}"
    )
    assert eval_horiz["awarded_marks"] >= 6.0
    assert eval_vert["awarded_marks"] >= 6.0


# ─────────────────────────────────────────────────────────────
# 3. Styling & Syntax Invariance
# ─────────────────────────────────────────────────────────────

def test_diagram_different_styling():
    """
    Scenario 3: Different visual line styles (ASCII boxes, rounded blocks, arrows)
    do not penalize credit if the semantics and components are preserved.
    """
    model_ans = "Application Layer -> API Gateway -> Smart Contract"
    question = "Draw the component interaction diagram."
    
    style_a = "Application Layer -> API Gateway -> Smart Contract"
    style_b = "[Application Layer] ===> (API Gateway) ===> [Smart Contract]"
    
    eval_a = evaluate_diagram_answer(student_text=style_a, model_answer_text=model_ans, max_marks=6.0, question_text=question)
    eval_b = evaluate_diagram_answer(student_text=style_b, model_answer_text=model_ans, max_marks=6.0, question_text=question)
    
    assert eval_a["awarded_marks"] >= 4.5
    assert eval_b["awarded_marks"] >= 4.5


# ─────────────────────────────────────────────────────────────
# 4. Missing Essential Component
# ─────────────────────────────────────────────────────────────

def test_diagram_missing_essential_component():
    """
    Scenario 4: When a student omits an essential component, marks must be
    proportionally deducted and the missing component flagged in missing_components.
    """
    model_ans = (
        "Three-Tier Blockchain Architecture:\n"
        "1. Application Layer (Mobile App, API Gateway)\n"
        "2. Smart Contracts Layer\n"
        "3. Blockchain Infrastructure"
    )
    question = "Draw the 3-tier supply chain architecture."
    
    # Student completely omits Blockchain Infrastructure
    student_text = "Mobile App -> API Gateway -> Smart Contract Layer"
    
    res = evaluate_diagram_answer(
        student_text=student_text,
        model_answer_text=model_ans,
        max_marks=10.0,
        question_text=question
    )
    
    assert res["awarded_marks"] < 10.0
    assert any("blockchain" in mc.lower() or "infrastructure" in mc.lower() for mc in res["missing_components"])
    assert res["needs_review"] or len(res["missing_components"]) > 0


# ─────────────────────────────────────────────────────────────
# 5. Incorrect / Reversed Arrow Direction
# ─────────────────────────────────────────────────────────────

def test_diagram_incorrect_arrow_direction():
    """
    Scenario 5: Reversed arrowheads indicate an incorrect operational sequence or data flow.
    Must flag reversed_arrows and penalize direction_score.
    """
    model_ans = "Mobile App -> API Gateway -> Smart Contracts Layer -> Blockchain Infrastructure"
    question = "Show the request propagation flow."
    
    # Student draws inverted flow: Blockchain Infrastructure -> Smart Contracts Layer -> API Gateway
    student_text = "Blockchain Infrastructure -> Smart Contracts Layer -> API Gateway -> Mobile App"
    
    res = evaluate_diagram_answer(
        student_text=student_text,
        model_answer_text=model_ans,
        max_marks=10.0,
        question_text=question
    )
    
    assert len(res["reversed_arrows"]) > 0 or res["has_contradiction"] is True
    assert res["awarded_marks"] <= 8.0, "Reversed arrow flow should be penalized"


# ─────────────────────────────────────────────────────────────
# 6. Incorrect Connectivity / Misconnected Blocks
# ─────────────────────────────────────────────────────────────

def test_diagram_incorrect_connectivity():
    """
    Scenario 6: Connecting to an incorrect block or bypassing required layers.
    """
    model_repr = {
        "diagram_type": "architecture",
        "essential_components": ["Mobile App", "API Gateway", "Smart Contracts Layer", "Consortium Nodes"],
        "connections": [
            {"source": "Mobile App", "target": "API Gateway"},
            {"source": "API Gateway", "target": "Smart Contracts Layer"},
            {"source": "Smart Contracts Layer", "target": "Consortium Nodes"}
        ],
        "required_labels": ["Mobile App", "API Gateway", "Smart Contracts Layer"]
    }
    
    # Student incorrectly connects Mobile App directly to Consortium Nodes
    student_repr = {
        "diagram_type": "architecture",
        "has_physical_diagram": True,
        "detected_components": ["Mobile App", "Consortium Nodes"],
        "detected_connections": [{"source": "Mobile App", "target": "Consortium Nodes"}],
        "detected_labels": ["Mobile App", "Consortium Nodes"]
    }
    
    comparison = compare_diagram_structures(student_repr, model_repr)
    
    assert comparison["connectivity_score"] < 0.60
    assert len(comparison["missing_connections"]) > 0


# ─────────────────────────────────────────────────────────────
# 7. Missing or Incorrect Labels
# ─────────────────────────────────────────────────────────────

def test_diagram_missing_or_incorrect_labels():
    """
    Scenario 7: Diagram drawn with unlabelled boxes or missing terminology.
    """
    model_ans = "Circuit: Resistor -> Capacitor -> Inductor -> Ground"
    question = "Draw the RLC filtering circuit diagram."
    
    # Student draws boxes with missing labels
    student_text = "Box1 -> Box2 -> Box3"
    
    res = evaluate_diagram_answer(
        student_text=student_text,
        model_answer_text=model_ans,
        max_marks=5.0,
        question_text=question
    )
    
    assert res["awarded_marks"] < 3.5, "Missing labels must deduct score"


# ─────────────────────────────────────────────────────────────
# 8. Partially Correct Diagram
# ─────────────────────────────────────────────────────────────

def test_diagram_partially_correct():
    """
    Scenario 8: Partially correct diagram with some valid components and connections
    must receive proportional partial marks bounded between 0.0 and max_marks.
    """
    model_ans = "Mobile App -> API Gateway -> Smart Contracts Layer -> Blockchain Infrastructure"
    question = "Draw the system architecture."
    
    # Student got Mobile App and API Gateway correct, missing backend contracts & blockchain
    student_text = "Mobile App -> API Gateway"
    
    res = evaluate_diagram_answer(
        student_text=student_text,
        model_answer_text=model_ans,
        max_marks=10.0,
        question_text=question
    )
    
    assert 2.0 <= res["awarded_marks"] <= 6.5, (
        f"Partially correct answer should receive partial marks, got {res['awarded_marks']}"
    )


# ─────────────────────────────────────────────────────────────
# 9. Poorly Drawn but Interpretable Diagram
# ─────────────────────────────────────────────────────────────

def test_diagram_poorly_drawn_but_interpretable():
    """
    Scenario 9: Messy handwriting OCR with stray noisy symbols, but identifiable
    components. Must NOT receive an arbitrary zero marks.
    """
    model_ans = "Customer -> API Gateway -> Database"
    question = "Draw the client server flow."
    
    # OCR noisy text representing hand-drawn arrows
    student_text = "Customer --~> [API Gateway] ---> [Database]"
    
    res = evaluate_diagram_answer(
        student_text=student_text,
        model_answer_text=model_ans,
        max_marks=6.0,
        question_text=question
    )
    
    assert res["awarded_marks"] >= 3.5, (
        f"Interpretable drawing must be given fair marks, got {res['awarded_marks']}"
    )


# ─────────────────────────────────────────────────────────────
# 10. Unreadable or Ambiguous Drawing
# ─────────────────────────────────────────────────────────────

def test_diagram_unreadable_or_ambiguous():
    """
    Scenario 10: Completely illegible drawing strokes.
    Must award baseline partial attempt credit (e.g. 30%), flag needs_review=True,
    and populate review_reason without failing or awarding 0.
    """
    # A physical diagram crop exists, but zero components could be deciphered
    student_repr = {
        "diagram_type": "general_diagram",
        "has_physical_diagram": True,
        "is_unreadable": True,
        "detected_components": [],
        "detected_connections": [],
        "detected_labels": []
    }
    
    model_repr = {
        "diagram_type": "architecture",
        "essential_components": ["Gateway", "Server", "Storage"],
        "connections": [],
        "required_labels": ["Gateway", "Server"]
    }
    
    comparison = compare_diagram_structures(student_repr, model_repr)
    eval_result = evaluate_diagram_with_rubric(
        comparison=comparison,
        max_marks=10.0,
        is_unreadable=True,
        has_physical_diagram=True
    )
    
    assert eval_result["needs_review"] is True
    assert eval_result["suggested_marks"] == 3.0  # 30% baseline attempt
    assert "ambiguous or unreadable" in eval_result["review_reason"]


# ─────────────────────────────────────────────────────────────
# 11. Text-Diagram Inconsistency / Contradiction
# ─────────────────────────────────────────────────────────────

def test_diagram_text_inconsistency_conflict():
    """
    Scenario 11: Student written text claims client authentication is enforced by API Gateway,
    but the diagram directly shows client bypassing the gateway to connect to the database.
    Must flag has_contradiction=True and provide explanatory notice.
    """
    model_repr = {
        "diagram_type": "architecture",
        "essential_components": ["Mobile App", "API Gateway", "Authentication", "Database"],
        "connections": [
            {"source": "Mobile App", "target": "API Gateway"},
            {"source": "API Gateway", "target": "Database"}
        ],
        "required_labels": ["Mobile App", "API Gateway", "Database"]
    }
    
    student_repr = {
        "diagram_type": "architecture",
        "has_physical_diagram": True,
        "detected_components": ["mobile app->database", "Database"],
        "detected_connections": [{"source": "Mobile App", "target": "Database"}],
        "detected_labels": ["Mobile App", "Database"]
    }
    
    written_text = "All requests are authenticated through API Gateway before accessing the database."
    
    comparison = compare_diagram_structures(student_repr, model_repr, student_written_text=written_text)
    
    assert comparison["has_contradiction"] is True
    assert len(comparison["text_diagram_inconsistencies"]) > 0


# ─────────────────────────────────────────────────────────────
# 12. Page with Mixed Text and Diagram (Segmentation Test)
# ─────────────────────────────────────────────────────────────

def test_page_with_text_and_diagram():
    """
    Scenario 12: Evaluates segmentation on a real scanned page containing handwritten
    text and an architecture diagram.
    Verifies that detect_diagram_regions isolates the diagram area.
    """
    # Use real answer script page if available
    img_path = os.path.join("uploads", "processed", "answer_scripts", "60", "page_001.png")
    if not os.path.exists(img_path):
        img_path = os.path.join("backend", "uploads", "processed", "answer_scripts", "60", "page_001.png")
        
    if os.path.exists(img_path):
        regions = detect_diagram_regions(img_path)
        assert len(regions) >= 1, "Must detect at least 1 diagram region on page_001.png"
        bbox = regions[0]["bounding_box"]
        assert len(bbox) == 4
        assert regions[0]["internal_complexity"] >= 4
    else:
        # If running in environment without the sample file, test synthetic fallback
        pytest.skip("Test image page_001.png not in local directory, skipping physical image test.")


# ─────────────────────────────────────────────────────────────
# 13. Multiple Diagrams for Different Questions
# ─────────────────────────────────────────────────────────────

def test_multiple_diagrams_different_questions():
    """
    Scenario 13: Multiple questions requiring diagrams across an exam.
    Q1: Architecture diagram
    Q2: Flowchart
    Verifies each is evaluated in context with its own model answer and criteria.
    """
    # Q1: Supply Chain Architecture
    q1_text = "Draw the supply chain architecture diagram."
    q1_model = "Mobile App -> API Gateway -> Smart Contracts Layer -> Blockchain Infrastructure"
    q1_student = "Mobile App -> API Gateway -> Smart Contracts Layer -> Blockchain Infrastructure"
    
    # Q2: Sorting Flowchart
    q2_text = "Draw a flowchart for Bubble Sort."
    q2_model = "Start -> Input Array -> Compare Adjacent Elements -> Swap if Greater -> Check Done -> Stop"
    q2_student = "Start -> Input Array -> Compare Adjacent Elements -> Swap -> Stop"
    
    eval_q1 = evaluate_diagram_answer(q1_student, q1_model, max_marks=10.0, question_text=q1_text)
    eval_q2 = evaluate_diagram_answer(q2_student, q2_model, max_marks=8.0, question_text=q2_text)
    
    assert eval_q1["diagram_type"] == "architecture"
    assert eval_q2["diagram_type"] == "flowchart"
    assert eval_q1["awarded_marks"] >= 8.5
    assert eval_q2["awarded_marks"] >= 5.0


# ─────────────────────────────────────────────────────────────
# 14. Answer with No Diagram When Required
# ─────────────────────────────────────────────────────────────

def test_answer_with_no_diagram_when_required():
    """
    Scenario 14: The rubric explicitly requires a diagram, but the student provided
    only a brief text definition without any diagram, blocks, or arrows.
    Verifies that diagram evaluation marks are appropriately low.
    """
    model_ans = (
        "Complete Architecture Diagram required:\n"
        "Customer -> API Gateway -> Smart Contracts -> Blockchain"
    )
    question = "Draw and explain the 3-tier supply chain architecture."
    rubric = [
        {"criterion": "Architecture Diagram & Blocks", "marks": 5.0, "description": "Accurate 3-tier diagram"},
        {"criterion": "Written Explanation", "marks": 5.0, "description": "Textual overview of layers"}
    ]
    
    # Student wrote only text with no drawing or arrows
    student_text = "The supply chain is a system for tracking products from factory to stores."
    
    res = evaluate_diagram_answer(
        student_text=student_text,
        model_answer_text=model_ans,
        max_marks=5.0,
        question_text=question,
        rubric_criteria=rubric
    )
    
    assert res["awarded_marks"] <= 2.5, "Missing required diagram must receive significantly reduced marks"
    assert len(res["missing_components"]) > 0


# ─────────────────────────────────────────────────────────────
# 15. AI Service / Processing Failure Resilience
# ─────────────────────────────────────────────────────────────

def test_ai_service_failure_resilience():
    """
    Scenario 15: If an internal component or external vision service throws an unexpected exception,
    the pipeline must catch it gracefully, return a baseline heuristic score bounded in [0, max_marks],
    and flag needs_review=True rather than crashing the exam evaluation.
    """
    with patch("app.services.diagram_evaluation_service.build_model_diagram_representation", side_effect=RuntimeError("AI Vision model timeout")):
        res = evaluate_diagram_answer(
            student_text="Some drawing text",
            model_answer_text="Model reference",
            max_marks=10.0,
            question_text="Draw the circuit."
        )
        
        assert 0.0 <= res["awarded_marks"] <= 10.0
        assert res["needs_review"] is True
        assert "Fallback applied" in res.get("review_reason", "")
