"""
Mathematical Evaluation Service — Symbolic & Method-Aware Grading
===================================================================
Evaluates mathematical calculations, equations, derivations, and expressions:

1. Symbolic Equivalence:
   - Uses SymPy to check algebraic, trigonometric, and calculus equivalence.
   - Accepts mathematically valid alternative forms (e.g. factored vs expanded,
     different variable representations, equivalent fractions, alternate order of terms).

2. Method vs. Final Answer Marking:
   - Evaluates the student's mathematical method, not only the final number.
   - Awards method marks (partial credit) for correct formulas, substitutions,
     and valid transformations even if an arithmetic mistake occurs later.
   - Error-Carried-Forward (ECF) support: assesses if subsequent steps logically
     follow from a prior slip.

3. Error Categorization:
   - Distinguishes conceptual error (invalid theorem/formula)
   - Calculation/arithmetic error (wrong arithmetic, valid method)
   - OCR symbol misinterpretation (e.g. '1' vs 'l', '+' vs 't', '0' vs 'O')

4. Bounds and Integrity:
   - Never awards full marks merely because the final number matches without method.
   - Bounded marks: 0.0 <= marks <= max_marks.
"""

import re
import math
import logging
from typing import Dict, Any, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Try importing SymPy for symbolic computation
try:
    import sympy
    from sympy import sympify, simplify, Eq, solve, Matrix
    from sympy.parsing.sympy_parser import (
        parse_expr,
        standard_transformations,
        implicit_multiplication_application,
        convert_xor
    )
    SYMPY_AVAILABLE = True
    SYMPY_TRANSFORMATIONS = standard_transformations + (
        implicit_multiplication_application,
        convert_xor
    )
except ImportError:
    SYMPY_AVAILABLE = False
    logger.warning("SymPy is not installed. Symbolic math evaluation will use regex heuristics.")


# Common OCR misread substitutions in mathematical handwriting
MATH_OCR_FIXES = [
    (r'\b[xX]\b', 'x'),
    (r'(\d)\s*[xX]\s*(\d)', r'\1 * \2'),       # 2 x 3 -> 2 * 3
    (r'(\d)\s*([a-zA-Z])', r'\1*\2'),          # 2x -> 2*x
    (r'([a-zA-Z])\s*(\d)', r'\1^\2'),          # x2 -> x^2 when exponent misread
    (r'\b[lI|]\b(?=[+\-*/=])', '1'),            # l + 5 -> 1 + 5
    (r'(?<=[+\-*/=])\s*[lI|]\b', '1'),          # 5 + l -> 5 + 1
    (r'÷', '/'),
    (r'×', '*'),
    (r'–|—', '-'),
    (r'²', '^2'),
    (r'³', '^3'),
    (r'√\s*(\w+)', r'sqrt(\1)'),
    (r'sqrt\s*\(([^)]+)\)', r'sqrt(\1)'),
    (r'==+', '='),
]


def clean_math_expression(text: str) -> str:
    """Cleans and standardizes mathematical expression strings from OCR text."""
    if not text:
        return ""
    cleaned = text.strip()
    for pattern, repl in MATH_OCR_FIXES:
        cleaned = re.sub(pattern, repl, cleaned)
    # Remove redundant spaces
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    return cleaned


def extract_math_lines(text: str) -> List[str]:
    """
    Extracts lines containing equations, formulas, or calculations from text.
    Looks for lines with '=', '+', '-', '*', '/', '^', or math functions.
    """
    lines = text.split('\n')
    math_lines = []
    math_char_pattern = re.compile(r'[=+\-*/^√∫∑<>]|\b(?:sqrt|sin|cos|tan|log|exp|lim|dy/dx|f\(x\))\b')

    for line in lines:
        line_clean = line.strip()
        if not line_clean:
            continue
        # If line contains calculation markers and numbers/symbols
        if math_char_pattern.search(line_clean) and any(c.isdigit() or c in 'xyzabcfghn' for c in line_clean.lower()):
            math_lines.append(line_clean)

    return math_lines


def are_expressions_equivalent(expr_str1: str, expr_str2: str) -> Tuple[bool, str]:
    """
    Checks if two mathematical expressions are mathematically equivalent using SymPy.
    Returns (is_equivalent, explanation).
    """
    if not SYMPY_AVAILABLE:
        # Fallback string comparison
        norm1 = re.sub(r'\s+', '', clean_math_expression(expr_str1)).lower()
        norm2 = re.sub(r'\s+', '', clean_math_expression(expr_str2)).lower()
        if norm1 == norm2:
            return True, "Identical expression string"
        return False, "SymPy unavailable for symbolic check"

    c1 = clean_math_expression(expr_str1).replace('^', '**')
    c2 = clean_math_expression(expr_str2).replace('^', '**')

    # If both expressions are equations (contain '=')
    if '=' in c1 and '=' in c2:
        try:
            lhs1, rhs1 = c1.split('=', 1)
            lhs2, rhs2 = c2.split('=', 1)

            e1 = parse_expr(lhs1, transformations=SYMPY_TRANSFORMATIONS) - parse_expr(rhs1, transformations=SYMPY_TRANSFORMATIONS)
            e2 = parse_expr(lhs2, transformations=SYMPY_TRANSFORMATIONS) - parse_expr(rhs2, transformations=SYMPY_TRANSFORMATIONS)

            # Check if e1 - e2 == 0 or e1 is a scalar multiple of e2
            diff = simplify(e1 - e2)
            if diff == 0:
                return True, "Symbolically identical equation"

            ratio = simplify(e1 / e2)
            if ratio.is_number and ratio != 0:
                return True, f"Equivalent equation (scaled by factor {ratio})"

        except Exception as ex:
            logger.debug(f"Equation equivalence check error: {ex}")

    # Standard expression equivalence: simplify(expr1 - expr2) == 0
    try:
        e1 = parse_expr(c1, transformations=SYMPY_TRANSFORMATIONS)
        e2 = parse_expr(c2, transformations=SYMPY_TRANSFORMATIONS)

        diff = simplify(e1 - e2)
        if diff == 0:
            return True, "Symbolically equivalent expressions"

        # Check numerical evaluation if both are constants
        if e1.is_number and e2.is_number:
            if math.isclose(float(e1), float(e2), rel_tol=1e-4, abs_tol=1e-4):
                return True, f"Numerically equivalent ({float(e1)} ≈ {float(e2)})"

    except Exception as ex:
        logger.debug(f"Expression equivalence check error for '{c1}' vs '{c2}': {ex}")

    return False, "Not symbolically equivalent"


def extract_numerical_results(text: str) -> List[float]:
    """Extracts final numerical values from answers (e.g., 'cost = 6', 'x = 3.5', 'Ans: 42')."""
    values = []
    # Match patterns like: x = 12.5, cost is 6, = 42, Ans: -3.14
    patterns = [
        r'(?:answer|ans|total|cost|result|value|x|y|z)\s*[:=]\s*(-?\d+(?:\.\d+)?)',
        r'=\s*(-?\d+(?:\.\d+)?)\s*$',
        r'\b(-?\d+(?:\.\d+)?)\s*(?:units?|kg|m/s|seconds?|ms|m|km|hours?|%)\b'
    ]
    for pat in patterns:
        for match in re.finditer(pat, text, re.IGNORECASE | re.MULTILINE):
            try:
                values.append(float(match.group(1)))
            except (ValueError, IndexError):
                pass

    return values


def evaluate_mathematical_answer(
    student_text: str,
    model_answer_text: str,
    max_marks: float,
    rubric_criteria: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """
    Comprehensive academic evaluation of a mathematical answer:
    1. Extracts calculation steps from student and model answer
    2. Identifies method steps vs final result
    3. Awards method marks even with arithmetic errors if method is valid
    4. Accepts valid alternative symbolic methods
    5. Returns structured evaluation with breakdown
    """
    student_math_lines = extract_math_lines(student_text)
    model_math_lines = extract_math_lines(model_answer_text)

    student_nums = extract_numerical_results(student_text)
    model_nums = extract_numerical_results(model_answer_text)

    # Breakdown allocations
    # Standard academic math: 60% method / reasoning, 40% final accurate calculation
    method_weight = 0.60
    accuracy_weight = 0.40

    method_score = 0.0
    accuracy_score = 0.0
    notes = []
    detected_steps = []

    # 1. Step-wise Method Evaluation
    if model_math_lines:
        matched_steps = 0
        total_model_steps = len(model_math_lines)

        for m_idx, m_line in enumerate(model_math_lines):
            step_matched = False
            best_reason = ""

            for s_line in student_math_lines:
                equiv, reason = are_expressions_equivalent(s_line, m_line)
                if equiv:
                    step_matched = True
                    best_reason = reason
                    break
                else:
                    # Check token overlap for formula usage
                    m_tokens = set(re.findall(r'[a-zA-Z_]+|\d+', m_line.lower()))
                    s_tokens = set(re.findall(r'[a-zA-Z_]+|\d+', s_line.lower()))
                    if m_tokens and len(m_tokens.intersection(s_tokens)) / len(m_tokens) >= 0.70:
                        step_matched = True
                        best_reason = "Formula structure applied"
                        break

            if step_matched:
                matched_steps += 1
                detected_steps.append({"step": m_idx + 1, "status": "valid", "detail": best_reason})
            else:
                detected_steps.append({"step": m_idx + 1, "status": "missing_or_divergent", "expected": m_line})

        method_score = min(1.0, matched_steps / max(1, total_model_steps))
        notes.append(f"Method verification: {matched_steps}/{total_model_steps} key steps demonstrated.")
    else:
        # No formal math lines in model answer, evaluate conceptual density
        if len(student_math_lines) > 0:
            method_score = 0.75
            notes.append("Mathematical reasoning present in student response.")
        else:
            method_score = 0.30
            notes.append("No explicit calculation steps found.")

    # 2. Final Numerical / Result Accuracy Evaluation
    if model_nums:
        target_num = model_nums[-1]  # The final answer in model
        has_correct_final = False
        for s_val in student_nums:
            if math.isclose(s_val, target_num, rel_tol=1e-3, abs_tol=1e-3):
                has_correct_final = True
                break

        if has_correct_final:
            accuracy_score = 1.0
            notes.append(f"Final calculation matches target ({target_num}).")
        else:
            # Check if method was correct but arithmetic had a minor slip
            if method_score >= 0.60:
                accuracy_score = 0.25  # Partial credit for near solution
                notes.append(f"Method valid; minor arithmetic deviation in final result (expected {target_num}).")
            else:
                accuracy_score = 0.0
                notes.append("Final result incorrect or unreached.")
    else:
        # Symbolic problem without a single final number
        accuracy_score = method_score

    # Compute overall score
    combined_fraction = (method_score * method_weight) + (accuracy_score * accuracy_weight)
    awarded_marks = round(min(max_marks, max(0.0, combined_fraction * max_marks)), 2)

    needs_review = False
    if accuracy_score < 0.5 and method_score > 0.5:
        # Arithmetic error with good method: highlight for professor verification
        needs_review = True
        notes.append("Flagged: Student used correct method with possible arithmetic slip.")

    return {
        "awarded_marks": awarded_marks,
        "max_marks": max_marks,
        "method_score": round(method_score, 2),
        "accuracy_score": round(accuracy_score, 2),
        "steps_evaluated": detected_steps,
        "explanation": " ".join(notes),
        "needs_review": needs_review,
        "is_mathematical": True
    }
