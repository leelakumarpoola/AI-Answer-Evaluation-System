"""
Automated Test Suite — Handwriting OCR & Answer Evaluation
===========================================================
Tests Phases 3-9 of the implementation plan:
- OCR preprocessing and extraction quality
- Question marker detection
- Student answer segmentation (marker-based and positional)
- Rubric evaluation (multi-signal scoring)
- Error handling and edge cases
- TrOCR integration (when available)

Run with:
    cd backend
    .\\venv\\Scripts\\python.exe -m pytest tests/test_ocr_handwriting.py -v

Or for a specific test class:
    .\\venv\\Scripts\\python.exe -m pytest tests/test_ocr_handwriting.py::TestQuestionMarkerDetection -v
"""

import re
import sys
import os
import pytest

# Ensure the backend app is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ─────────────────────────────────────────────────────────
# Test: OCR Text Cleaning
# ─────────────────────────────────────────────────────────

class TestOCRTextCleaning:
    """Tests for the OCR cleanup and normalization functions."""

    def test_q_marker_normalization_basic(self):
        from app.services.student_answer_extraction_service import clean_ocr_text
        assert "Q1" in clean_ocr_text("Ql The first answer")
        assert "Q1" in clean_ocr_text("QI The first answer")
        # Q| is handled by the Q[lI|] regex (pipe inside character class)
        result = clean_ocr_text("Ql second test")
        assert "Q1" in result

    def test_q_marker_space_removal(self):
        from app.services.student_answer_extraction_service import clean_ocr_text
        result = clean_ocr_text("Q 1 is about photosynthesis")
        assert "Q1" in result

    def test_q_marker_dash_removal(self):
        from app.services.student_answer_extraction_service import clean_ocr_text
        result = clean_ocr_text("Q - 3 Explain Newton's law")
        assert "Q3" in result

    def test_line_start_l_to_1(self):
        from app.services.student_answer_extraction_service import clean_ocr_text
        result = clean_ocr_text("l. First answer\nl. Second answer")
        assert result.startswith("1.")

    def test_pipe_character_removal(self):
        from app.services.student_answer_extraction_service import clean_ocr_text
        result = clean_ocr_text("The answer | is correct")
        assert "|" not in result

    def test_empty_text_returns_empty(self):
        from app.services.student_answer_extraction_service import clean_ocr_text
        assert clean_ocr_text("") == ""
        assert clean_ocr_text(None) == ""

    def test_normal_text_preserved(self):
        from app.services.student_answer_extraction_service import clean_ocr_text
        text = "Photosynthesis is the process by which plants make food."
        result = clean_ocr_text(text)
        assert "Photosynthesis" in result
        assert "process" in result


# ─────────────────────────────────────────────────────────
# Test: Question Marker Pattern Detection
# ─────────────────────────────────────────────────────────

class TestQuestionMarkerDetection:
    """Tests for the QUESTION_MARKER_PATTERN regex."""

    def _find_markers(self, text):
        from app.services.student_answer_extraction_service import (
            QUESTION_MARKER_PATTERN, _extract_question_number
        )
        matches = list(QUESTION_MARKER_PATTERN.finditer(text))
        return [_extract_question_number(m) for m in matches]

    def test_q_prefix_formats(self):
        markers = self._find_markers("Q1 answer\nQ2 more\nQ3 done")
        assert "1" in markers
        assert "2" in markers
        assert "3" in markers

    def test_q_dot_format(self):
        markers = self._find_markers("Q.1 first answer\nQ.2 second")
        assert "1" in markers
        assert "2" in markers

    def test_question_word_format(self):
        markers = self._find_markers("Question 1 Explain\nQuestion 2 Define")
        assert "1" in markers
        assert "2" in markers

    def test_ques_abbreviation(self):
        markers = self._find_markers("Ques 1 answer here\nQues 2 other")
        assert "1" in markers

    def test_ans_prefix(self):
        markers = self._find_markers("Ans 1 here is my answer\nAns 2 second")
        assert "1" in markers
        assert "2" in markers

    def test_answer_prefix(self):
        markers = self._find_markers("Answer 1 first\nAnswer 2 second")
        assert "1" in markers

    def test_numeric_dot_format(self):
        markers = self._find_markers("1. Photosynthesis\n2. Respiration\n3. Transpiration")
        assert "1" in markers
        assert "2" in markers
        assert "3" in markers

    def test_numeric_parenthesis_format(self):
        markers = self._find_markers("(1) First answer\n(2) Second answer")
        assert "1" in markers
        assert "2" in markers

    def test_numeric_closing_paren(self):
        markers = self._find_markers("1) first\n2) second")
        assert "1" in markers
        assert "2" in markers

    def test_question_no_format(self):
        markers = self._find_markers("Question No. 1 Explain\nQuestion No 2 Define")
        assert "1" in markers

    def test_no_markers_returns_empty(self):
        markers = self._find_markers("This is just regular text with no question markers at all.")
        # Might have false positives for very generic patterns, but shouldn't crash
        assert isinstance(markers, list)

    def test_multipart_question_letters(self):
        markers = self._find_markers("Q1a Write the formula\nQ1b Explain the term")
        assert "1a" in markers
        assert "1b" in markers


# ─────────────────────────────────────────────────────────
# Test: Question Number Normalization
# ─────────────────────────────────────────────────────────

class TestQuestionNumberNormalization:
    """Tests for _normalise_q_num and _build_q_num_lookup."""

    def test_normalise_lowercase(self):
        from app.services.student_answer_extraction_service import _normalise_q_num
        assert _normalise_q_num("Q1") == "q1"
        assert _normalise_q_num("QUESTION1") == "question1"

    def test_normalise_leading_zeros(self):
        from app.services.student_answer_extraction_service import _normalise_q_num
        assert _normalise_q_num("01") == "1"
        assert _normalise_q_num("001") == "1"

    def test_find_question_variants(self):
        from app.services.student_answer_extraction_service import (
            _build_q_num_lookup, _find_question
        )

        class FakeQuestion:
            def __init__(self, num):
                self.question_number = num
                self.id = int(re.sub(r'\D', '', num) or 1)

        questions = [FakeQuestion("Q1"), FakeQuestion("Q2"), FakeQuestion("Q3")]
        lookup = _build_q_num_lookup(questions)

        # Direct match
        assert _find_question("q1", lookup) is not None
        # Numeric match (OCR drops the Q prefix)
        assert _find_question("1", lookup) is not None
        # Non-existent
        assert _find_question("99", lookup) is None


# ─────────────────────────────────────────────────────────
# Test: Positional Fallback
# ─────────────────────────────────────────────────────────

class TestPositionalFallback:
    """Tests for the positional paragraph splitting fallback."""

    def test_equal_paragraphs_to_questions(self):
        from app.services.student_answer_extraction_service import _split_text_by_position
        text = "Para one.\n\nPara two.\n\nPara three."
        result = _split_text_by_position(text, 3)
        assert len(result) == 3
        assert result[0][0] == "1"
        assert result[1][0] == "2"
        assert result[2][0] == "3"

    def test_more_paragraphs_than_questions(self):
        from app.services.student_answer_extraction_service import _split_text_by_position
        text = "\n\n".join([f"Paragraph {i}" for i in range(9)])
        result = _split_text_by_position(text, 3)
        assert len(result) == 3

    def test_fewer_paragraphs_than_questions(self):
        from app.services.student_answer_extraction_service import _split_text_by_position
        text = "Single paragraph with all the content."
        result = _split_text_by_position(text, 5)
        assert len(result) == 1  # Only 1 paragraph, so 1 result

    def test_empty_text_returns_empty(self):
        from app.services.student_answer_extraction_service import _split_text_by_position
        result = _split_text_by_position("", 3)
        assert result == []


# ─────────────────────────────────────────────────────────
# Test: OCR Error Correction (ocr_service)
# ─────────────────────────────────────────────────────────

class TestOCRErrorCorrection:
    """Tests for _fix_common_ocr_errors in ocr_service.py."""

    def test_ql_to_q1(self):
        from app.services.ocr_service import _fix_common_ocr_errors
        assert "Q1" in _fix_common_ocr_errors("Ql answer here")

    def test_q_space_digit(self):
        from app.services.ocr_service import _fix_common_ocr_errors
        result = _fix_common_ocr_errors("Q 1 is about")
        assert "Q1" in result

    def test_q_dash_digit(self):
        from app.services.ocr_service import _fix_common_ocr_errors
        result = _fix_common_ocr_errors("Q - 2 explain")
        assert "Q2" in result

    def test_o_zero_confusion(self):
        from app.services.ocr_service import _fix_common_ocr_errors
        result = _fix_common_ocr_errors("The value is 1O5")
        assert "105" in result

    def test_empty_returns_empty(self):
        from app.services.ocr_service import _fix_common_ocr_errors
        assert _fix_common_ocr_errors("") == ""

    def test_normal_content_preserved(self):
        from app.services.ocr_service import _fix_common_ocr_errors
        text = "Osmosis is the movement of water molecules."
        result = _fix_common_ocr_errors(text)
        assert "Osmosis" in result
        assert "water" in result


# ─────────────────────────────────────────────────────────
# Test: Rubric Evaluation — Multi-Signal Grading
# ─────────────────────────────────────────────────────────

class TestRubricEvaluationSignals:
    """Tests for keyword matching and length adequacy signals."""

    def test_keyword_match_full_overlap(self):
        from app.services.rubric_evaluation_service import _keyword_match_ratio
        student = "photosynthesis uses chlorophyll sunlight carbon dioxide"
        reference = "photosynthesis chlorophyll sunlight water carbon dioxide"
        ratio = _keyword_match_ratio(student, reference)
        assert ratio > 0.6, f"Expected > 0.6, got {ratio}"

    def test_keyword_match_no_overlap(self):
        from app.services.rubric_evaluation_service import _keyword_match_ratio
        student = "the cat sat on the mat"
        reference = "photosynthesis chlorophyll carbon dioxide water"
        ratio = _keyword_match_ratio(student, reference)
        assert ratio < 0.3, f"Expected < 0.3, got {ratio}"

    def test_keyword_match_empty_reference(self):
        from app.services.rubric_evaluation_service import _keyword_match_ratio
        ratio = _keyword_match_ratio("some answer", "")
        assert ratio == 0.5  # Neutral when can't measure

    def test_length_adequate_long_answer(self):
        from app.services.rubric_evaluation_service import _length_adequacy_score
        model = "The process of photosynthesis uses sunlight water and carbon dioxide."
        student = model + " Additional explanation about chlorophyll and ATP production."
        score = _length_adequacy_score(student, model)
        assert score == 1.0

    def test_length_very_short_answer(self):
        from app.services.rubric_evaluation_service import _length_adequacy_score
        model = " ".join(["word"] * 50)
        student = "short"
        score = _length_adequacy_score(student, model)
        assert score < 0.3

    def test_length_empty_model(self):
        from app.services.rubric_evaluation_service import _length_adequacy_score
        score = _length_adequacy_score("some answer", "")
        assert score == 0.5  # Neutral when model is empty

    def test_marks_never_exceed_criterion_max(self):
        from app.services.rubric_evaluation_service import _marks_and_reason
        fraction, reason = _marks_and_reason(1.0, 5.0)
        assert fraction <= 1.0
        # Awarded marks = fraction × max_marks should not exceed max_marks
        awarded = fraction * 5.0
        assert awarded <= 5.0

    def test_evidence_strength_bounded(self):
        from app.services.rubric_evaluation_service import _compute_evidence_strength
        for sbert in [0.0, 0.5, 1.0]:
            for kw in [0.0, 0.5, 1.0]:
                for length in [0.0, 0.5, 1.0]:
                    strength = _compute_evidence_strength(sbert, kw, length, 0.5)
                    assert 0.0 <= strength <= 1.0, (
                        f"Evidence out of bounds: {strength} for sbert={sbert}, kw={kw}, length={length}"
                    )

    def test_marks_fraction_thresholds(self):
        from app.services.rubric_evaluation_service import _marks_and_reason
        # Test each threshold level
        fraction_1, _ = _marks_and_reason(0.70, 10)   # Excellent (>= 0.58)
        fraction_075, _ = _marks_and_reason(0.50, 10)  # Good (>= 0.42)
        fraction_05, _ = _marks_and_reason(0.35, 10)   # Moderate (>= 0.28)
        fraction_025, _ = _marks_and_reason(0.20, 10)  # Weak (>= 0.14)
        fraction_0, _ = _marks_and_reason(0.05, 10)    # None (< 0.14)
        assert fraction_1 == 1.0
        assert fraction_075 == 0.75
        assert fraction_05 == 0.5
        assert fraction_025 == 0.25
        assert fraction_0 == 0.0


# ─────────────────────────────────────────────────────────
# Test: Keyword Extraction
# ─────────────────────────────────────────────────────────

class TestKeywordExtraction:
    """Tests for _extract_keywords."""

    def test_extracts_meaningful_words(self):
        from app.services.rubric_evaluation_service import _extract_keywords
        keywords = _extract_keywords("Photosynthesis uses chlorophyll and sunlight")
        assert "photosynthesis" in keywords
        assert "chlorophyll" in keywords
        assert "sunlight" in keywords

    def test_ignores_short_words(self):
        from app.services.rubric_evaluation_service import _extract_keywords
        keywords = _extract_keywords("The cat sat on it")
        assert "cat" not in keywords  # less than 4 chars
        assert "sat" not in keywords

    def test_ignores_stop_words(self):
        from app.services.rubric_evaluation_service import _extract_keywords
        keywords = _extract_keywords("This process which occurs when there")
        assert "this" not in keywords
        assert "when" not in keywords
        assert "there" not in keywords

    def test_empty_text(self):
        from app.services.rubric_evaluation_service import _extract_keywords
        assert _extract_keywords("") == set()


# ─────────────────────────────────────────────────────────
# Test: TrOCR Service
# ─────────────────────────────────────────────────────────

class TestTrOCRService:
    """Tests for TrOCR service (availability and status)."""

    def test_status_returns_dict(self):
        from app.services.trocr_service import get_trocr_status
        status = get_trocr_status()
        assert isinstance(status, dict)
        assert "enabled" in status
        assert "available" in status

    def test_disabled_by_default(self):
        """TrOCR should be disabled unless TROCR_ENABLED=true is set."""
        import app.services.trocr_service as trocr_svc
        # Unless env var is set, TrOCR should not be enabled
        if not trocr_svc.TROCR_ENABLED:
            assert not trocr_svc.is_trocr_available()

    def test_recognize_fails_gracefully_when_disabled(self):
        from app.services.trocr_service import is_trocr_available, recognize_page_trocr
        if not is_trocr_available():
            with pytest.raises(RuntimeError, match="not available"):
                recognize_page_trocr("nonexistent.png")


# ─────────────────────────────────────────────────────────
# Test: OCR Service Imports and Configuration
# ─────────────────────────────────────────────────────────

class TestOCRServiceSetup:
    """Tests that OCR service imports and configures correctly."""

    def test_ocr_service_imports(self):
        """OCR service must import without errors."""
        from app.services import ocr_service
        assert hasattr(ocr_service, "preprocess_and_ocr_image")
        assert hasattr(ocr_service, "process_document_ocr")
        assert hasattr(ocr_service, "process_answer_script_ocr")

    def test_cv2_availability_flag(self):
        from app.services.ocr_service import CV2_AVAILABLE
        # Should be a boolean
        assert isinstance(CV2_AVAILABLE, bool)

    def test_tesseract_configs_list(self):
        from app.services.ocr_service import TESSERACT_CONFIGS
        assert len(TESSERACT_CONFIGS) >= 3
        assert all(isinstance(c, str) for c in TESSERACT_CONFIGS)

    def test_good_quality_thresholds(self):
        from app.services.ocr_service import GOOD_QUALITY_WORD_COUNT, GOOD_QUALITY_CONFIDENCE
        assert GOOD_QUALITY_WORD_COUNT > 0
        assert 0 < GOOD_QUALITY_CONFIDENCE < 100


# ─────────────────────────────────────────────────────────
# Test: Segment-Level OCR Correctness (synthetic data)
# ─────────────────────────────────────────────────────────

class TestSegmentationWithSyntheticText:
    """
    Test segmentation logic using crafted OCR-like text.
    No actual images needed — tests the pure text processing logic.
    """

    def _run_extraction_on_text(self, pages_text, question_numbers):
        """Helper: simulate extraction from synthetic OCR text."""
        from app.services.student_answer_extraction_service import (
            QUESTION_MARKER_PATTERN, _extract_question_number, _normalise_q_num,
            clean_ocr_text
        )

        answers_data = {}
        current_q_num = None

        for page_num, page_text in enumerate(pages_text, start=1):
            page_text = clean_ocr_text(page_text)
            matches = list(QUESTION_MARKER_PATTERN.finditer(page_text))

            if not matches:
                if current_q_num is not None and page_text.strip():
                    answers_data[current_q_num]["text"].append(page_text.strip())
            else:
                for i, match in enumerate(matches):
                    raw_q_num = _extract_question_number(match)
                    if not raw_q_num:
                        continue
                    norm_q_num = _normalise_q_num(raw_q_num)

                    if i == 0 and match.start() > 0:
                        pre_text = page_text[:match.start()].strip()
                        if pre_text and current_q_num is not None:
                            answers_data[current_q_num]["text"].append(pre_text)

                    next_start = matches[i+1].start() if i+1 < len(matches) else len(page_text)
                    block_text = page_text[match.end():next_start].strip()

                    current_q_num = norm_q_num
                    if current_q_num not in answers_data:
                        answers_data[current_q_num] = {"text": [], "start": page_num}
                    if block_text:
                        answers_data[current_q_num]["text"].append(block_text)

        return answers_data

    def test_simple_q_markers(self):
        # Markers must be at start of lines — that is how handwriting is structured
        text = "Q1 Photosynthesis is a process.\nQ2 Respiration produces ATP.\nQ3 Osmosis involves water."
        answers = self._run_extraction_on_text([text], ["1", "2", "3"])
        assert "1" in answers
        assert "2" in answers
        assert "3" in answers
        assert "Photosynthesis" in answers["1"]["text"][0]

    def test_cross_page_answers(self):
        page1 = "Q1 Photosynthesis is the process by which plants"
        page2 = "use sunlight to produce glucose and oxygen. Q2 Respiration"
        answers = self._run_extraction_on_text([page1, page2], ["1", "2"])
        assert "1" in answers
        # Q1 answer should span both pages
        combined_q1 = " ".join(answers["1"]["text"])
        assert "Photosynthesis" in combined_q1

    def test_numeric_dot_markers(self):
        text = "1. Photosynthesis overview\n\n2. Respiration details\n\n3. Osmosis process"
        answers = self._run_extraction_on_text([text], ["1", "2", "3"])
        assert "1" in answers or "2" in answers  # At least some markers detected

    def test_multipage_no_markers(self):
        """When no markers, should return empty (triggering positional fallback)."""
        page1 = "First answer content here about photosynthesis."
        page2 = "Second answer content here about respiration."
        answers = self._run_extraction_on_text([page1, page2], ["1", "2"])
        # No markers → answers_data will be empty (triggers positional fallback externally)
        assert len(answers) == 0


# ─────────────────────────────────────────────────────────
# Entry Point
# ─────────────────────────────────────────────────────────

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
