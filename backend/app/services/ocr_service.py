"""
OCR Service — Handwriting-Optimized Pipeline
=============================================
Supports two OCR backends:
  1. Tesseract (default, always available)
  2. TrOCR — microsoft/trocr-base-handwritten (optional, requires GPU/good CPU)

Design decisions:
- Smart early-exit: stops trying more Tesseract configs once a good result is found
- Reduced passes: max 2-3 image variants instead of 4-5
- Per-stage timing for benchmarking and debugging
- Thread-safe: max 2 workers to avoid Tesseract race conditions
- OpenCV pipeline with graceful PIL fallback
"""

import os
import time
import logging
import pytesseract
import numpy as np
from PIL import Image, ImageEnhance, ImageFilter
from sqlalchemy.orm import Session
from fastapi import HTTPException
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor
from app.models.exam_document import ExamDocument
from app.models.ocr_result import OCRResult
from app.models.answer_script import AnswerScript
from app.models.answer_script_page import AnswerScriptPage
from app.services.document_processing_service import PROCESSED_ANSWERS_DIR
from app.config import settings

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────
# OpenCV availability check
# ─────────────────────────────────────────────────────────
try:
    import cv2
    CV2_AVAILABLE = True
    logger.info("OpenCV available — advanced handwriting preprocessing enabled")
except ImportError:
    CV2_AVAILABLE = False
    logger.warning("opencv-python not installed. Falling back to PIL-only preprocessing.")

# ─────────────────────────────────────────────────────────
# Quality thresholds for early-exit logic
# ─────────────────────────────────────────────────────────
GOOD_QUALITY_WORD_COUNT = 20   # Stop trying more configs once we have this many words
GOOD_QUALITY_CONFIDENCE = 55.0  # AND confidence is above this %

# Tesseract configs in priority order — best for handwriting first
TESSERACT_CONFIGS = [
    "--oem 1 --psm 6 -c preserve_interword_spaces=1",  # Uniform block — best default
    "--oem 1 --psm 4 -c preserve_interword_spaces=1",  # Single column
    "--oem 1 --psm 3 -c preserve_interword_spaces=1",  # Auto segmentation
    "--oem 1 --psm 11",                                 # Sparse text (scattered answers)
    "--oem 0 --psm 6",                                  # Legacy engine last resort
]


def _configure_tesseract():
    """Configure Tesseract executable path from settings or environment."""
    tesseract_cmd = getattr(settings, "tesseract_cmd", None) or os.environ.get("TESSERACT_CMD")
    if not tesseract_cmd:
        default_path = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
        if os.path.exists(default_path):
            tesseract_cmd = default_path
    if tesseract_cmd and os.path.exists(tesseract_cmd):
        pytesseract.pytesseract.tesseract_cmd = tesseract_cmd


# ─────────────────────────────────────────────────────────
# Image Preprocessing — OpenCV Pipeline
# ─────────────────────────────────────────────────────────

def _preprocess_handwriting_cv2(image_path: str) -> list:
    """
    Optimized OpenCV preprocessing for handwriting.
    Returns 2-3 variants (not 4-5) to avoid redundant OCR calls.

    Variants returned:
    1. CLAHE + deskew + adaptive threshold (best for most handwriting)
    2. Otsu binarisation of deskewed image (best for dark ink)
    3. Raw denoised grayscale (fallback — minimal processing)
    """
    img_bgr = cv2.imread(image_path)
    if img_bgr is None:
        raise ValueError(f"Cannot read image: {image_path}")

    # 1. Upscale 2x for better character recognition
    h, w = img_bgr.shape[:2]
    # Only upscale if the image is small; avoid blowing up already large images
    if max(h, w) < 2000:
        img_bgr = cv2.resize(img_bgr, (w * 2, h * 2), interpolation=cv2.INTER_CUBIC)

    # 2. Grayscale
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)

    # 3. CLAHE — contrast limited adaptive histogram equalisation
    clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))
    gray_clahe = clahe.apply(gray)

    # 4. Denoise — remove scan speckles while preserving pen strokes
    denoised = cv2.fastNlMeansDenoising(
        gray_clahe, h=10, templateWindowSize=7, searchWindowSize=21
    )

    # 5. Deskew
    deskewed = _deskew(denoised)

    # 6. Adaptive threshold — best for uneven lighting / shadows in handwriting
    adaptive = cv2.adaptiveThreshold(
        deskewed, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        blockSize=31,
        C=10
    )

    # 7. Morphological closing — join broken letter strokes
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
    closed_adaptive = cv2.morphologyEx(adaptive, cv2.MORPH_CLOSE, kernel)

    # 8. Otsu variant — good for dense, dark ink
    _, otsu = cv2.threshold(deskewed, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    def to_pil(arr):
        return Image.fromarray(arr)

    # Return 3 variants — sufficient without overdoing it
    return [
        to_pil(closed_adaptive),   # Best for most handwriting
        to_pil(otsu),              # Best for dark ink
        to_pil(deskewed),          # Raw denoised — conservative fallback
    ]


def _deskew(image: np.ndarray) -> np.ndarray:
    """Correct page tilt using minimum area rectangle on dark pixels."""
    coords = np.column_stack(np.where(image < 200))  # dark pixels
    if len(coords) < 10:
        return image
    angle = cv2.minAreaRect(coords.astype(np.float32))[-1]
    if angle < -45:
        angle = 90 + angle
    elif angle > 45:
        angle = angle - 90
    if abs(angle) < 0.5:  # Less than 0.5° — not worth rotating
        return image
    (h, w) = image.shape[:2]
    center = (w // 2, h // 2)
    M = cv2.getRotationMatrix2D(center, angle, 1.0)
    return cv2.warpAffine(
        image, M, (w, h),
        flags=cv2.INTER_CUBIC,
        borderMode=cv2.BORDER_REPLICATE
    )


def _preprocess_handwriting_pil(image_path: str) -> list:
    """
    PIL-only fallback preprocessing (3 variants instead of 4).
    """
    img = Image.open(image_path)
    w, h = img.size
    # Only upscale small images
    if max(h, w) < 2000:
        img = img.resize((w * 2, h * 2), Image.LANCZOS)
    gray = img.convert("L")

    # Variant 1: Strong contrast + sharpen (best for faint pencil)
    v1 = ImageEnhance.Contrast(gray).enhance(2.5)
    v1 = ImageEnhance.Sharpness(v1).enhance(2.0)
    v1 = v1.filter(ImageFilter.SHARPEN)

    # Variant 2: Moderate contrast + unsharp mask
    v2 = ImageEnhance.Contrast(gray).enhance(1.8)
    v2 = v2.filter(ImageFilter.UnsharpMask(radius=2, percent=150, threshold=3))

    # Variant 3: Original grayscale — minimal processing
    v3 = gray

    return [v1, v2, v3]


# ─────────────────────────────────────────────────────────
# Multi-Config Tesseract with Smart Early-Exit
# ─────────────────────────────────────────────────────────

def _run_tesseract_smart(preprocessed_images: list) -> tuple:
    """
    Smart Tesseract runner with early-exit optimization.

    For each image variant:
      - Try first Tesseract config
      - If result quality is GOOD (≥20 words AND ≥55% confidence) → stop immediately
      - Otherwise try the next config
      - Track the best result seen so far
    
    This reduces redundant OCR calls significantly:
    - Best case: 1 call per page (good handwriting, first config works)
    - Worst case: 15 calls (3 images × 5 configs) — still fewer than the old 20

    Returns: (best_text, avg_confidence, word_count, ocr_duration_seconds)
    """
    best_text = ""
    best_score = -1.0
    best_conf = 0.0
    t0 = time.time()

    for img_idx, img in enumerate(preprocessed_images):
        for cfg_idx, config in enumerate(TESSERACT_CONFIGS):
            try:
                data = pytesseract.image_to_data(
                    img, config=config, output_type=pytesseract.Output.DICT
                )
                text = pytesseract.image_to_string(img, config=config).strip()

                if not text:
                    continue

                confs = [
                    float(c) for c in data.get("conf", [])
                    if str(c).replace("-", "").isdigit() and float(c) >= 0
                ]
                avg_conf = float(np.mean(confs)) if confs else 0.0
                word_count = len(text.split())
                # Scoring: reward word count and confidence together
                score = word_count * (avg_conf / 100.0 + 0.1)

                if score > best_score:
                    best_score = score
                    best_text = text
                    best_conf = avg_conf

                logger.debug(
                    f"  OCR img={img_idx} cfg={cfg_idx}: {word_count} words, "
                    f"conf={avg_conf:.1f}%, score={score:.1f}"
                )

                # Early-exit: result is good enough — don't waste time on more configs
                if word_count >= GOOD_QUALITY_WORD_COUNT and avg_conf >= GOOD_QUALITY_CONFIDENCE:
                    logger.debug(
                        f"  Early-exit at img={img_idx} cfg={cfg_idx} "
                        f"({word_count} words, {avg_conf:.1f}%)"
                    )
                    duration = time.time() - t0
                    return best_text, round(best_conf, 2), word_count, round(duration, 3)

            except Exception as e:
                logger.debug(f"  Tesseract config '{config}' failed: {e}")
                continue

        # If we already have a good result after the first image, skip remaining images
        best_word_count = len(best_text.split()) if best_text else 0
        if best_word_count >= GOOD_QUALITY_WORD_COUNT and best_conf >= GOOD_QUALITY_CONFIDENCE:
            logger.debug(f"  Good result after img={img_idx}, skipping remaining image variants")
            break

    duration = time.time() - t0
    final_word_count = len(best_text.split()) if best_text else 0
    return best_text, round(best_conf, 2), final_word_count, round(duration, 3)


# ─────────────────────────────────────────────────────────
# OCR Error Correction
# ─────────────────────────────────────────────────────────

def _fix_common_ocr_errors(text: str) -> str:
    """
    Correct systematic Tesseract misreads in handwritten text.
    Focused on question number markers (critical for extraction).
    """
    import re
    if not text:
        return text

    # Question number normalisation
    text = re.sub(r'\bQ[lI|]\b', 'Q1', text)                          # Ql/QI/Q| → Q1
    text = re.sub(r'\bQi\b', 'Q1', text, flags=re.IGNORECASE)
    text = re.sub(r'\bQO\b', 'Q0', text, flags=re.IGNORECASE)
    text = re.sub(r'\bQ\s*-\s*(\d+)', r'Q\1', text)                   # Q - 1 → Q1
    text = re.sub(r'\bQ\s+(\d+)\b', r'Q\1', text)                     # Q 1 → Q1

    # Common single-character substitutions at line start
    text = re.sub(r'^l\.', '1.', text, flags=re.MULTILINE)            # l. → 1.
    text = re.sub(r'^I\.', '1.', text, flags=re.MULTILINE)            # I. → 1.

    # Zero/O confusion between digits
    text = re.sub(r'(\d)O(\d)', r'\g<1>0\2', text)

    # Remove stray vertical bars (scan artifacts)
    text = re.sub(r'(?<!\w)\|(?!\w)', '', text)

    # Normalize whitespace
    text = re.sub(r'[ \t]{2,}', ' ', text)

    return text.strip()


# ─────────────────────────────────────────────────────────
# Main OCR Entry Point
# ─────────────────────────────────────────────────────────

def preprocess_and_ocr_image(image_path: str) -> tuple:
    """
    OCR a single page image.

    Pipeline:
    1. Preprocess with OpenCV (or PIL fallback)
    2. Smart Tesseract multi-config with early-exit
    3. OCR error correction
    4. Last-resort raw fallback if result is empty

    Returns: (text, confidence, word_count, processing_time_s)
    """
    _configure_tesseract()
    t_start = time.time()

    # Preprocessing
    try:
        if CV2_AVAILABLE:
            preprocessed = _preprocess_handwriting_cv2(image_path)
        else:
            preprocessed = _preprocess_handwriting_pil(image_path)
    except Exception as e:
        logger.warning(f"Preprocessing failed for {image_path}: {e} — using raw image")
        try:
            preprocessed = [Image.open(image_path).convert("L")]
        except Exception as e2:
            logger.error(f"Cannot open image {image_path}: {e2}")
            return "", 0.0, 0, round(time.time() - t_start, 3)

    # Smart Tesseract
    text, conf, word_count, ocr_time = _run_tesseract_smart(preprocessed)

    # Post-OCR cleanup
    text = _fix_common_ocr_errors(text)

    # Last resort: if still empty, try raw PIL image directly
    if not text:
        try:
            raw_img = Image.open(image_path).convert("L")
            text = pytesseract.image_to_string(
                raw_img, config="--oem 1 --psm 6"
            ).strip()
            text = _fix_common_ocr_errors(text)
            conf = 40.0 if text else 0.0
            word_count = len(text.split()) if text else 0
            logger.debug(f"  Raw fallback produced {word_count} words")
        except Exception as e:
            logger.debug(f"  Raw fallback also failed: {e}")

    total_time = round(time.time() - t_start, 3)
    return text, conf, word_count, total_time


# ─────────────────────────────────────────────────────────
# Document OCR (Question Papers, Model Answers, Rubrics)
# ─────────────────────────────────────────────────────────

def process_document_ocr(document_id: int, db: Session):
    """Run OCR on all pages of an exam document (question paper / model answer / rubric)."""
    document = db.query(ExamDocument).filter(ExamDocument.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    if document.processing_status != "processed":
        raise HTTPException(
            status_code=400,
            detail="Document must be processed (PDF→images) before OCR. Run 'Process' first."
        )

    exam_id = document.exam_id
    output_dir = os.path.join("uploads", "processed", "exams", str(exam_id), str(document_id))

    if not os.path.exists(output_dir):
        raise HTTPException(
            status_code=400,
            detail=f"Processed pages directory not found at {output_dir}. Re-run 'Process'."
        )

    page_files = sorted([
        f for f in os.listdir(output_dir)
        if f.endswith(".png") and f.startswith("page_")
    ])
    if not page_files:
        raise HTTPException(
            status_code=400,
            detail="No page images found for this document. Re-run 'Process'."
        )

    # Cache: skip pages that already have good OCR results
    existing_pages = {
        p.page_number: p
        for p in db.query(OCRResult).filter(OCRResult.document_id == document_id).all()
    }

    pages_to_process = []
    for file_name in page_files:
        try:
            page_num = int(file_name.split("_")[1].split(".")[0])
        except Exception:
            continue
        image_path = os.path.join(output_dir, file_name)
        existing = existing_pages.get(page_num)
        if existing and existing.ocr_status == "processed" and existing.extracted_text:
            logger.debug(f"Skipping page {page_num} — already OCR'd")
            continue
        pages_to_process.append((page_num, image_path))

    logger.info(
        f"Document {document_id}: {len(pages_to_process)}/{len(page_files)} pages need OCR"
    )

    def _worker(item):
        p_num, img_path = item
        t0 = time.time()
        try:
            txt, conf, words, ocr_t = preprocess_and_ocr_image(img_path)
            total_t = round(time.time() - t0, 3)
            logger.info(
                f"  Page {p_num}: {words} words, conf={conf:.1f}%, "
                f"ocr={ocr_t}s, total={total_t}s"
            )
            return p_num, img_path, txt, conf, "processed", None
        except Exception as e:
            logger.error(f"  Page {p_num}: OCR FAILED — {e}")
            return p_num, img_path, "", 0.0, "failed", str(e)

    # Max 2 workers — Tesseract has issues with > 2 concurrent processes on Windows
    max_workers = min(2, len(pages_to_process)) if pages_to_process else 1
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        results_list = list(executor.map(_worker, pages_to_process))

    for p_num, img_path, txt, conf, status, err in results_list:
        rec = existing_pages.get(p_num)
        if not rec:
            rec = OCRResult(document_id=document_id, page_number=p_num, image_path=img_path)
            db.add(rec)
        rec.extracted_text = txt
        rec.ocr_confidence = conf
        rec.ocr_status = status
        rec.error_message = err
        rec.processed_at = datetime.now(timezone.utc)

    db.commit()

    results = db.query(OCRResult).filter(
        OCRResult.document_id == document_id
    ).order_by(OCRResult.page_number).all()

    overall_status = "processed"
    failed_pages = [r.page_number for r in results if r.ocr_status == "failed"]
    if failed_pages:
        overall_status = "partial_failure"
        logger.warning(f"Document {document_id}: OCR failed on pages {failed_pages}")

    total_words = sum(
        len((r.extracted_text or "").split()) for r in results if r.ocr_status == "processed"
    )
    logger.info(f"Document {document_id}: OCR complete. Total words: {total_words}")

    return {
        "document_id": document_id,
        "status": overall_status,
        "total_words_extracted": total_words,
        "pages": [
            {
                "page_number": r.page_number,
                "text": r.extracted_text,
                "ocr_status": r.ocr_status,
                "ocr_confidence": r.ocr_confidence,
                "word_count": len((r.extracted_text or "").split())
            }
            for r in results
        ]
    }


# ─────────────────────────────────────────────────────────
# Answer Script OCR (Student Handwritten Answer Sheets)
# ─────────────────────────────────────────────────────────

def process_answer_script_ocr(answer_script_id: int, db: Session):
    """
    OCR pipeline for student handwritten answer scripts.

    Status tracking:
    - processing → processed (all pages done)
    - processing → failed (unrecoverable error)
    - per-page: processed | failed | blank

    Actionable error messages replace generic failures.
    """
    document = db.query(AnswerScript).filter(AnswerScript.id == answer_script_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Answer script not found")

    if document.processing_status != "processed":
        raise HTTPException(
            status_code=400,
            detail="Answer script pages not rendered yet. Run 'Process' first to convert PDF to images."
        )

    image_dir = os.path.join(PROCESSED_ANSWERS_DIR, str(answer_script_id))
    if not os.path.exists(image_dir):
        raise HTTPException(
            status_code=400,
            detail=f"Image directory not found: {image_dir}. Re-run 'Process'."
        )

    document.ocr_status = "processing"
    db.commit()

    try:
        existing_pages = {
            p.page_number: p
            for p in db.query(AnswerScriptPage).filter(
                AnswerScriptPage.answer_script_id == answer_script_id
            ).all()
        }

        pages_to_process = []
        skipped_pages = []
        for i in range(document.page_count):
            page_num = i + 1
            filename = f"page_{page_num:03d}.png"
            filepath = os.path.join(image_dir, filename)

            if not os.path.exists(filepath):
                logger.warning(f"  Page {page_num}: image file missing ({filepath})")
                continue

            existing = existing_pages.get(page_num)
            if existing and existing.ocr_status == "processed" and existing.extracted_text:
                skipped_pages.append(page_num)
                continue

            pages_to_process.append((page_num, filepath))

        logger.info(
            f"Answer script {answer_script_id}: "
            f"{len(pages_to_process)} pages to OCR, {len(skipped_pages)} cached, "
            f"backend={'OpenCV+Tesseract' if CV2_AVAILABLE else 'PIL+Tesseract'}"
        )

        def _worker(item):
            p_num, f_path = item
            t0 = time.time()
            try:
                txt, conf, words, ocr_t = preprocess_and_ocr_image(f_path)
                total_t = round(time.time() - t0, 3)

                # Classify page quality for reporting
                if words == 0:
                    page_status = "blank"
                    err = "No text extracted from this page"
                    logger.warning(f"  Page {p_num}: BLANK — no text detected ({total_t}s)")
                elif words < 5:
                    page_status = "processed"
                    err = f"Very few words detected ({words}) — handwriting may be unclear"
                    logger.warning(f"  Page {p_num}: {words} words (low), conf={conf:.1f}% ({total_t}s)")
                else:
                    page_status = "processed"
                    err = None
                    logger.info(f"  Page {p_num}: {words} words, conf={conf:.1f}% ({total_t}s)")

                return p_num, f_path, txt, conf, page_status, err
            except Exception as e:
                logger.error(f"  Page {p_num}: OCR FAILED — {e}")
                return p_num, f_path, "", 0.0, "failed", str(e)

        # Max 2 workers — safe for Tesseract on Windows
        max_workers = min(2, len(pages_to_process)) if pages_to_process else 1
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            results_list = list(executor.map(_worker, pages_to_process))

        for p_num, f_path, txt, conf, status, err in results_list:
            rec = existing_pages.get(p_num)
            if not rec:
                rec = AnswerScriptPage(
                    answer_script_id=answer_script_id,
                    page_number=p_num,
                    image_path=f_path
                )
                db.add(rec)
            rec.extracted_text = txt
            rec.ocr_confidence = conf
            rec.ocr_status = status
            rec.error_message = err
            rec.processed_at = datetime.now(timezone.utc)

        document.ocr_status = "processed"
        db.commit()

        # Summary
        total_words = sum(
            len((txt or "").split())
            for _, _, txt, _, st, _ in results_list
            if st in ("processed", "blank")
        )
        blank_pages = [p for p, _, _, _, st, _ in results_list if st == "blank"]
        failed_pages = [p for p, _, _, _, st, _ in results_list if st == "failed"]

        logger.info(
            f"Answer script {answer_script_id}: OCR complete. "
            f"Total words: {total_words}, blank: {blank_pages}, failed: {failed_pages}"
        )

        if total_words == 0 and not skipped_pages:
            logger.warning(
                f"Answer script {answer_script_id}: ZERO words extracted across all pages. "
                "Check if the PDF contains actual image pages (not just a blank/white scan)."
            )

    except Exception as e:
        document.ocr_status = "failed"
        db.commit()
        raise HTTPException(
            status_code=500,
            detail=f"OCR pipeline failed: {str(e)}"
        )


def get_answer_script_ocr_results(answer_script_id: int, db: Session):
    document = db.query(AnswerScript).filter(AnswerScript.id == answer_script_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Answer script not found")

    results = db.query(AnswerScriptPage).filter(
        AnswerScriptPage.answer_script_id == answer_script_id
    ).order_by(AnswerScriptPage.page_number).all()

    return {
        "answer_script_id": answer_script_id,
        "student_id": document.student_id,
        "exam_id": document.exam_id,
        "status": document.ocr_status,
        "pages": [
            {
                "page_number": r.page_number,
                "text": r.extracted_text,
                "ocr_status": r.ocr_status,
                "ocr_confidence": r.ocr_confidence,
                "word_count": len((r.extracted_text or "").split()),
                "error_message": r.error_message
            }
            for r in results
        ]
    }
