"""
TrOCR Service — Optional Handwriting Recognition Backend
=========================================================
Uses microsoft/trocr-base-handwritten from HuggingFace Transformers.

This is an optional supplement to Tesseract. It is NOT used by default.
To enable: set TROCR_ENABLED=true in .env

Architecture:
- Single model instance (initialized once, reused)
- CPU inference by default; GPU if available
- Line-level recognition (TrOCR is trained on single text lines)
- Paragraph reconstruction from ordered lines
- Safe initialization with informative error messages

TrOCR vs Tesseract trade-off:
- TrOCR: higher accuracy on cursive/joined handwriting, slower (~3-10s/page CPU)
- Tesseract: faster, better for printed-style handwriting, lower accuracy for cursive
- Recommendation: use Tesseract by default; enable TrOCR for difficult pages

Benchmark endpoint: POST /answer-scripts/{id}/ocr/benchmark
"""

import os
import time
import logging
from typing import Optional, List, Tuple

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────────

TROCR_ENABLED = os.environ.get("TROCR_ENABLED", "false").lower() == "true"
TROCR_MODEL_ID = "microsoft/trocr-base-handwritten"

# ─────────────────────────────────────────────────────────
# Model State
# ─────────────────────────────────────────────────────────

_trocr_processor = None
_trocr_model = None
_trocr_device = None
_trocr_init_error: Optional[str] = None
_trocr_initialized = False


def _initialize_trocr() -> bool:
    """
    Initialize TrOCR model and processor.
    Called once — result is cached in module-level variables.

    Returns True if initialization succeeded, False otherwise.
    """
    global _trocr_processor, _trocr_model, _trocr_device
    global _trocr_init_error, _trocr_initialized

    if _trocr_initialized:
        return _trocr_init_error is None

    _trocr_initialized = True

    if not TROCR_ENABLED:
        _trocr_init_error = "TrOCR is disabled (set TROCR_ENABLED=true in .env to enable)"
        logger.info(_trocr_init_error)
        return False

    logger.info(f"Initializing TrOCR model: {TROCR_MODEL_ID}")
    t0 = time.time()

    try:
        import torch
        from transformers import TrOCRProcessor, VisionEncoderDecoderModel

        # Select device
        if torch.cuda.is_available():
            _trocr_device = "cuda"
            logger.info("TrOCR: GPU available — using CUDA")
        else:
            _trocr_device = "cpu"
            logger.info("TrOCR: No GPU — using CPU (expect ~3-10s per page)")

        _trocr_processor = TrOCRProcessor.from_pretrained(TROCR_MODEL_ID)
        _trocr_model = VisionEncoderDecoderModel.from_pretrained(TROCR_MODEL_ID)
        _trocr_model = _trocr_model.to(_trocr_device)
        _trocr_model.eval()

        elapsed = round(time.time() - t0, 2)
        logger.info(f"TrOCR initialized successfully in {elapsed}s on {_trocr_device}")
        return True

    except ImportError as e:
        _trocr_init_error = f"TrOCR requires 'transformers' and 'torch': {e}"
        logger.error(_trocr_init_error)
        return False
    except OSError as e:
        _trocr_init_error = (
            f"TrOCR model not found locally: {e}. "
            f"Run: from transformers import TrOCRProcessor; "
            f"TrOCRProcessor.from_pretrained('{TROCR_MODEL_ID}')"
        )
        logger.error(_trocr_init_error)
        return False
    except Exception as e:
        _trocr_init_error = f"TrOCR initialization failed: {type(e).__name__}: {e}"
        logger.error(_trocr_init_error)
        return False


def is_trocr_available() -> bool:
    """Check if TrOCR is enabled and successfully initialized."""
    return _initialize_trocr()


def get_trocr_status() -> dict:
    """Return TrOCR initialization status for API reporting."""
    available = _initialize_trocr()
    return {
        "enabled": TROCR_ENABLED,
        "available": available,
        "model": TROCR_MODEL_ID if available else None,
        "device": _trocr_device if available else None,
        "error": _trocr_init_error if not available else None
    }


# ─────────────────────────────────────────────────────────
# Text Line Segmentation
# ─────────────────────────────────────────────────────────

def _segment_image_into_lines(image) -> List:
    """
    Segment a PIL image into individual text line images for TrOCR.

    TrOCR is trained on single-line images; feeding full pages gives poor results.
    
    Approach:
    1. Try OpenCV horizontal projection profile (best for clean scans)
    2. Fallback: split image into fixed-height strips
    
    Returns: list of PIL Image objects, one per text line
    """
    try:
        import cv2
        import numpy as np

        img_array = np.array(image.convert("L"))
        _, binary = cv2.threshold(img_array, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

        # Horizontal projection — sum of dark pixels per row
        row_sums = binary.sum(axis=1)

        # Find line boundaries (transitions from text to whitespace)
        threshold = row_sums.max() * 0.05  # 5% of max row density
        in_text = row_sums > threshold

        lines = []
        in_line = False
        line_start = 0
        min_line_height = 10  # Ignore tiny fragments

        for row_idx, has_text in enumerate(in_text):
            if has_text and not in_line:
                in_line = True
                line_start = row_idx
            elif not has_text and in_line:
                in_line = False
                height = row_idx - line_start
                if height >= min_line_height:
                    # Add small padding
                    y1 = max(0, line_start - 3)
                    y2 = min(img_array.shape[0], row_idx + 3)
                    line_img = image.crop((0, y1, image.width, y2))
                    lines.append(line_img)

        if in_line:  # Handle last line
            height = len(in_text) - line_start
            if height >= min_line_height:
                y1 = max(0, line_start - 3)
                line_img = image.crop((0, y1, image.width, image.height))
                lines.append(line_img)

        if lines:
            logger.debug(f"TrOCR: Segmented into {len(lines)} text lines")
            return lines

    except Exception as e:
        logger.debug(f"TrOCR line segmentation failed: {e}")

    # Fallback: fixed-height strips
    strip_height = max(40, image.height // 20)
    strips = []
    for y in range(0, image.height, strip_height):
        strip = image.crop((0, y, image.width, min(y + strip_height, image.height)))
        strips.append(strip)
    logger.debug(f"TrOCR: Using {len(strips)} fixed-height strips as fallback")
    return strips


# ─────────────────────────────────────────────────────────
# TrOCR Page Recognition
# ─────────────────────────────────────────────────────────

def recognize_page_trocr(image_path: str) -> Tuple[str, float]:
    """
    Recognize handwriting on a page using TrOCR.

    Pipeline:
    1. Open and preprocess image
    2. Segment into text lines
    3. Run TrOCR on each line
    4. Reconstruct paragraph-ordered text
    
    Returns: (recognized_text, confidence_estimate)
    """
    if not is_trocr_available():
        raise RuntimeError(
            f"TrOCR not available: {_trocr_init_error}. "
            "Falling back to Tesseract."
        )

    from PIL import Image
    import torch

    t0 = time.time()

    try:
        image = Image.open(image_path).convert("RGB")
    except Exception as e:
        raise ValueError(f"Cannot open image {image_path}: {e}")

    # Segment page into lines
    lines = _segment_image_into_lines(image)
    if not lines:
        logger.warning(f"TrOCR: No lines segmented from {image_path}")
        return "", 0.0

    recognized_lines = []
    total_tokens = 0

    with torch.no_grad():
        for line_idx, line_img in enumerate(lines):
            try:
                # Resize line to appropriate height for TrOCR (384px height is standard)
                target_height = 384
                aspect = line_img.width / line_img.height
                new_width = min(int(target_height * aspect), 3840)
                line_img_resized = line_img.resize((new_width, target_height))

                pixel_values = _trocr_processor(
                    images=line_img_resized, return_tensors="pt"
                ).pixel_values.to(_trocr_device)

                generated_ids = _trocr_model.generate(pixel_values)
                line_text = _trocr_processor.batch_decode(
                    generated_ids, skip_special_tokens=True
                )[0].strip()

                if line_text:
                    recognized_lines.append(line_text)
                    total_tokens += len(line_text.split())

            except Exception as e:
                logger.debug(f"TrOCR: Line {line_idx} recognition failed: {e}")
                continue

    full_text = "\n".join(recognized_lines)
    elapsed = round(time.time() - t0, 3)

    # TrOCR doesn't provide confidence scores — estimate based on token density
    conf_estimate = min(85.0, 50.0 + total_tokens * 0.5)

    logger.info(
        f"TrOCR: {len(recognized_lines)}/{len(lines)} lines recognized, "
        f"{total_tokens} words, {elapsed}s"
    )

    return full_text, conf_estimate


# ─────────────────────────────────────────────────────────
# Benchmark: Compare Tesseract vs TrOCR on Same Pages
# ─────────────────────────────────────────────────────────

def benchmark_ocr_backends(image_paths: List[str]) -> dict:
    """
    Run both Tesseract and TrOCR on the same images and compare results.
    
    Metrics:
    - Word count (higher = more content extracted)
    - Processing time per page
    - TrOCR availability

    Does NOT auto-switch backends — provides data for informed decision.
    """
    from app.services.ocr_service import preprocess_and_ocr_image

    results = []
    trocr_available = is_trocr_available()

    for img_path in image_paths:
        page_result = {"image": os.path.basename(img_path)}

        # Tesseract
        try:
            t0 = time.time()
            tess_text, tess_conf, tess_words, _ = preprocess_and_ocr_image(img_path)
            tess_time = round(time.time() - t0, 3)
            page_result["tesseract"] = {
                "word_count": tess_words,
                "confidence": tess_conf,
                "time_s": tess_time,
                "text_preview": tess_text[:200] if tess_text else ""
            }
        except Exception as e:
            page_result["tesseract"] = {"error": str(e)}

        # TrOCR
        if trocr_available:
            try:
                t0 = time.time()
                trocr_text, trocr_conf = recognize_page_trocr(img_path)
                trocr_time = round(time.time() - t0, 3)
                page_result["trocr"] = {
                    "word_count": len(trocr_text.split()),
                    "confidence_estimate": trocr_conf,
                    "time_s": trocr_time,
                    "text_preview": trocr_text[:200] if trocr_text else ""
                }
            except Exception as e:
                page_result["trocr"] = {"error": str(e)}
        else:
            page_result["trocr"] = {
                "available": False,
                "reason": _trocr_init_error
            }

        results.append(page_result)

    return {
        "trocr_available": trocr_available,
        "trocr_status": get_trocr_status(),
        "pages": results,
        "recommendation": (
            "TrOCR showed higher word counts — consider enabling for difficult pages"
            if trocr_available and all(
                r.get("trocr", {}).get("word_count", 0) >
                r.get("tesseract", {}).get("word_count", 0)
                for r in results
                if "word_count" in r.get("trocr", {}) and "word_count" in r.get("tesseract", {})
            )
            else "Tesseract performing comparably or better — no switch needed"
        )
    }
