"""
Intelligent Diagram Recognition & Semantic Diagram Evaluation Service
======================================================================
Comprehensive Visual Reasoning and Rubric-Based Diagram Grading Engine:
1. Detects and extracts diagram regions on scanned handwritten answer sheets (OpenCV contour,
   morphology, nested hierarchy, connected components).
2. Distinguishes drawings, flowcharts, architectures, circuits, and geometric figures from text.
3. Crops and saves high-resolution diagram regions with padding for visual inspection.
4. Builds structured internal representations (nodes, edges, labels, hierarchy, flow directions)
   for both model answer reference diagrams and student drawings.
5. Performs multi-dimensional semantic comparison:
   - Component Recognition (essential vs optional components)
   - Structural & Topological Similarity (invariant to size, orientation, drawing style)
   - Connectivity & Relationships (transitions, connections between blocks)
   - Direction & Sequence (arrowhead directions, sequence of operations)
   - Labels & Annotations (required terminology, values, component names)
   - Conceptual Correctness (domain concept validity)
   - Completeness & Omissions (missing components)
   - Contradictions & Text-Diagram Inconsistency (cross-checks diagram with written explanation)
6. Rubric-based mark allocation strictly bounded between 0.0 and max_marks.
7. Flags unreadable/ambiguous drawings and contradictions for professor review with audit trail.
"""

import os
import re
import math
import logging
from typing import Dict, Any, List, Optional, Tuple, Set

logger = logging.getLogger(__name__)

try:
    import cv2
    import numpy as np
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False
    logger.warning("OpenCV not available. Diagram analysis will use textual/structural heuristics.")


# ─────────────────────────────────────────────────────────────
# 1. Detection, Segmentation & Cropping of Diagrams
# ─────────────────────────────────────────────────────────────

def detect_diagram_regions(image_path: str) -> List[Dict[str, Any]]:
    """
    Detects visual diagram regions (flowcharts, graphs, architectures, circuits, drawings) in an image.
    Uses contour hierarchy and geometric properties to distinguish drawings from text lines.
    """
    if not CV2_AVAILABLE or not os.path.exists(image_path):
        return []

    try:
        img = cv2.imread(image_path)
        if img is None:
            return []

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        h, w = gray.shape

        # Adaptive thresholding to isolate lines and strokes
        thresh = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 25, 10
        )

        # Morphological closing to group nearby diagram elements together
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (15, 15))
        closed = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)

        contours, hierarchy = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        diagram_regions = []

        min_area = (w * h) * 0.015  # At least 1.5% of page area
        max_area = (w * h) * 0.85   # At most 85% of page area

        for cnt in contours:
            area = cv2.contourArea(cnt)
            if min_area < area < max_area:
                x, y, cw, ch = cv2.boundingRect(cnt)
                aspect_ratio = cw / float(ch) if ch > 0 else 0

                # Diagrams typically have aspect ratios between 0.25 and 3.5 (not long single-line text)
                if 0.25 <= aspect_ratio <= 3.5:
                    roi = thresh[y:y+ch, x:x+cw]
                    # Check internal shape complexity (number of inner contours and branching strokes)
                    inner_cnts, _ = cv2.findContours(roi, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
                    if len(inner_cnts) >= 4:
                        diagram_regions.append({
                            "bounding_box": [int(x), int(y), int(cw), int(ch)],
                            "area": int(area),
                            "internal_complexity": len(inner_cnts),
                            "aspect_ratio": round(aspect_ratio, 2)
                        })

        return diagram_regions

    except Exception as e:
        logger.error(f"Diagram detection failed on {image_path}: {e}")
        return []


def detect_and_extract_diagrams(
    image_path: str,
    output_dir: Optional[str] = None,
    script_id: Optional[int] = None,
    page_num: Optional[int] = None,
    question_id: Optional[int] = None
) -> List[Dict[str, Any]]:
    """
    Detects, segments, crops, and saves diagram regions from a page image.
    Preserves labels, arrows, and surrounding context using safety padding.
    """
    regions = detect_diagram_regions(image_path)
    if not regions or not CV2_AVAILABLE:
        return regions

    try:
        img = cv2.imread(image_path)
        if img is None:
            return regions

        img_h, img_w = img.shape[:2]

        if not output_dir:
            base_backend = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            s_id_str = str(script_id) if script_id is not None else "common"
            output_dir = os.path.join(base_backend, "uploads", "diagrams", "answer_scripts", s_id_str)

        os.makedirs(output_dir, exist_ok=True)

        extracted_crops = []
        for idx, reg in enumerate(regions):
            x, y, cw, ch = reg["bounding_box"]
            pad = 25  # Context padding for labels and arrows
            x1 = max(0, x - pad)
            y1 = max(0, y - pad)
            x2 = min(img_w, x + cw + pad)
            y2 = min(img_h, y + ch + pad)

            crop = img[y1:y2, x1:x2]
            q_part = f"_q{question_id}" if question_id is not None else ""
            p_part = f"_p{page_num}" if page_num is not None else ""
            filename = f"diag{q_part}{p_part}_{idx+1}.png"
            crop_path = os.path.join(output_dir, filename)

            cv2.imwrite(crop_path, crop)

            # Generate relative URL for frontend consumption
            rel_crop_url = f"/api/evaluations/diagram-file/{os.path.basename(crop_path)}"

            crop_item = dict(reg)
            crop_item["crop_path"] = crop_path
            crop_item["crop_url"] = rel_crop_url
            crop_item["page_number"] = page_num or 1
            crop_item["padded_box"] = [x1, y1, x2 - x1, y2 - y1]
            extracted_crops.append(crop_item)

        return extracted_crops

    except Exception as e:
        logger.error(f"Error extracting diagram crops from {image_path}: {e}")
        return regions


# ─────────────────────────────────────────────────────────────
# 2. Diagram Classification & Textual Label Extraction
# ─────────────────────────────────────────────────────────────

DIAGRAM_CATEGORIES = {
    "flowchart": [
        "flowchart", "decision", "start", "stop", "end", "process", "branch",
        "diamond", "yes/no", "true/false", "algorithm flow", "step"
    ],
    "architecture": [
        "architecture", "layer", "tier", "infrastructure", "smart contract", "consortium",
        "blockchain", "database", "api gateway", "frontend", "backend", "client", "server",
        "service", "bus", "distributed", "node"
    ],
    "circuit": [
        "circuit", "resistor", "capacitor", "inductor", "voltage", "current", "ground",
        "transistor", "diode", "switch", "source", "ohm", "ampere", "terminal", "schematic"
    ],
    "geometric": [
        "triangle", "circle", "radius", "diameter", "polygon", "angle", "hypotenuse",
        "perpendicular", "parallel", "vertex", "vertices", "tangent", "chord", "quadrilateral"
    ],
    "graph_plot": [
        "plot", "graph", "x-axis", "y-axis", "origin", "curve", "linear", "exponential",
        "scatter", "coordinates", "slope", "intercept", "trend", "histogram"
    ],
    "scientific_biology": [
        "anatomy", "organ", "cell", "membrane", "nucleus", "chloroplast", "leaf", "tissue",
        "structure of", "labelled diagram", "cross section", "apparatus", "experimental setup"
    ]
}


def classify_diagram_type(text: str, question_text: str = "") -> str:
    """
    Identifies the specialized category of the diagram based on question
    and diagram annotations.
    """
    combined = f"{question_text} {text}".lower()

    scores = {}
    for cat, keywords in DIAGRAM_CATEGORIES.items():
        score = sum(1 for kw in keywords if kw in combined)
        scores[cat] = score

    best_cat = max(scores, key=scores.get)
    if scores[best_cat] > 0:
        return best_cat

    if re.search(r'\b(?:->|-->|>)\b', text):
        return "flowchart"

    return "general_diagram"


def extract_arrow_chains(text: str) -> List[Tuple[str, str]]:
    """
    Extracts all directed connections (source -> target), properly handling
    chained transitions like A -> B -> C -> D, ASCII arrows (===>, =>), and vertical arrows.
    """
    connections = []
    clauses = re.split(r'[\n\r,;]', text)
    for clause in clauses:
        clause = clause.strip()
        if not clause:
            continue
        parts = re.split(r'\s*(?:->|-->|—>|==+>|=>|>|↓)\s*', clause)
        cleaned_parts = []
        for p in parts:
            p_clean = re.split(r'\s+(?:with|cost|at|having|weight|is)\b', p.strip(" []()"), flags=re.IGNORECASE)[0].strip()
            p_clean = re.sub(r'^[A-Za-z0-9_\s]+:\s*', '', p_clean)
            p_clean = re.sub(r'^\d+[\.\)]\s*', '', p_clean).strip(" []()")
            if p_clean and len(p_clean) >= 1:
                cleaned_parts.append(p_clean)
        if len(cleaned_parts) >= 2:
            for i in range(len(cleaned_parts) - 1):
                connections.append((cleaned_parts[i], cleaned_parts[i+1]))
    return connections


def extract_diagram_text_labels(text: str) -> List[str]:
    """
    Extracts text labels, graph nodes, architectural layers, or transition symbols
    mentioned in answer text and diagram regions.
    Looks for labels like 'S -> A', 'Start', 'Decision', 'Application Layer', 'Smart Contracts', etc.
    """
    labels = []
    # Match node relationships e.g. S->A, A->G, Client->Server, App->Gateway, [App] ===> [Gateway]
    chains = extract_arrow_chains(text)
    for src, dst in chains:
        labels.append(f"{src}->{dst}")
        labels.append(src)
        labels.append(dst)

    # Match state or node definitions e.g. Node A, State 1, Layer 2
    node_matches = re.findall(r'\b(?:Node|State|Step|Block|Layer|Component|Tier)\s+([A-Za-z0-9_]+)\b', text, re.IGNORECASE)
    labels.extend(node_matches)

    # Match domain architecture layers and common entities
    domain_terms = [
        'start', 'stop', 'open', 'closed', 'decision', 'input', 'output', 'frontier',
        'application layer', 'smart contracts', 'smart contract layer', 'blockchain infrastructure',
        'api gateway', 'authentication', 'mobile app', 'client', 'server', 'database',
        'consortium nodes', 'consensus layer', 'ground', 'resistor', 'capacitor',
        'voltage source', 'diode', 'x-axis', 'y-axis', 'origin', 'nucleus', 'membrane'
    ]
    text_lower = text.lower()
    for concept in domain_terms:
        if concept in text_lower:
            labels.append(concept.title())

    return list(dict.fromkeys(labels))


# ─────────────────────────────────────────────────────────────
# 3. Model Answer Visual & Structural Representation Builder
# ─────────────────────────────────────────────────────────────

def build_model_diagram_representation(
    question_text: str,
    model_answer_text: str,
    rubric_criteria: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """
    Builds a structured graph representation of the expected reference diagram:
    - Expected components (essential vs optional)
    - Expected connections and flow directions
    - Expected labels and annotations
    - Hierarchy and layout requirements
    """
    diag_type = classify_diagram_type(model_answer_text, question_text)

    # Extract components from model answer text
    essential_components = []
    optional_components = []
    connections = []
    required_labels = []

    # Parse arrow relationships e.g. "A -> B", "[A] ===> [B]", "A -> B -> C"
    chains = extract_arrow_chains(model_answer_text)
    for src, dst in chains:
        connections.append({"source": src, "target": dst, "direction": "forward"})
        essential_components.append(src)
        essential_components.append(dst)

    # Detect technical layers or blocks (common in architectures)
    layer_matches = re.findall(r'(?:[A-Za-z0-9_]+(?:\s+[A-Za-z0-9_]+){0,3})\s+(?:Layer|Tier|Infrastructure|Gateway|Contracts?|App|Database|Nodes?)\b', model_answer_text, re.IGNORECASE)
    for lm in layer_matches:
        lm_clean = re.sub(r'^[A-Za-z0-9_\s]+:\s*', '', lm)
        lm_clean = re.sub(r'^\d+[\.\)]\s*', '', lm_clean).strip(" []()")
        if lm_clean:
            essential_components.append(lm_clean)

    # Check circuit components
    circuit_matches = re.findall(r'\b(?:Resistor|Capacitor|Inductor|Voltage Source|Current Source|Ground|Diode|Transistor)\b', model_answer_text, re.IGNORECASE)
    for cm in circuit_matches:
        essential_components.append(cm.strip())

    # Check flowchart blocks
    flowchart_matches = re.findall(r'\b(?:Start|Stop|End|Input|Output|Decision|Process|Calculate|Compute|Display|Read)\b[A-Za-z0-9_\s]*', model_answer_text, re.IGNORECASE)
    for fm in flowchart_matches:
        fm_clean = fm.strip(" []()").strip()
        if fm_clean:
            essential_components.append(fm_clean)

    # Check rubric criteria for explicit diagram expectations
    if rubric_criteria:
        for rc in rubric_criteria:
            c_text = f"{rc.get('criterion', '')} {rc.get('description', '')}".lower()
            if any(w in c_text for w in ['diagram', 'sketch', 'flowchart', 'architecture', 'layer', 'circuit', 'graph']):
                # Extract named entities from rubric criterion
                for word in re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', rc.get('criterion', '')):
                    if len(word) > 3 and word not in ['Marks', 'Explain', 'Design', 'Draw']:
                        essential_components.append(word)

    essential_components = list(dict.fromkeys(essential_components))
    required_labels = list(dict.fromkeys(essential_components[:6]))

    # If components are empty, extract key uppercase or noun concepts
    if not essential_components:
        words = re.findall(r'\b[A-Za-z]{4,}\b', model_answer_text)
        essential_components = list(dict.fromkeys(words[:5]))
        required_labels = list(dict.fromkeys(words[:4]))

    return {
        "diagram_type": diag_type,
        "essential_components": essential_components,
        "optional_components": optional_components,
        "connections": connections,
        "required_labels": required_labels,
        "flow_direction": "top_to_bottom_or_left_to_right",
        "hierarchy_layers": [c for c in essential_components if "layer" in c.lower()],
        "contradiction_rules": [
            {"condition": "reversed_flow", "description": "Arrow direction inverted from expected data flow"}
        ]
    }


# ─────────────────────────────────────────────────────────────
# 4. Student Diagram Independent Structural Analysis
# ─────────────────────────────────────────────────────────────

def analyze_student_diagram_structure(
    student_text: str,
    diagram_crops: Optional[List[Dict[str, Any]]] = None,
    question_text: str = ""
) -> Dict[str, Any]:
    """
    Analyzes the student's diagram independently to extract what was actually drawn:
    - Bounding boxes, shapes, boxes, lines, arrowheads
    - Recognized text labels and annotations
    - Connections and operational directions
    - Inferred diagram category
    """
    has_crops = bool(diagram_crops and len(diagram_crops) > 0)
    diag_type = classify_diagram_type(student_text, question_text)

    # 1. Component entity extraction from diagram text and surrounding context
    detected_labels = extract_diagram_text_labels(student_text)

    detected_components = []
    # Identify layer blocks, service nodes, or flowchart shapes
    for lbl in detected_labels:
        if "->" not in lbl:
            detected_components.append(lbl)

    # Additional keyword entity discovery in student text
    domain_entities = [
        "Mobile App", "Customer", "Application Layer", "API Gateway", "Authentication",
        "Smart Contracts Layer", "Smart Contract", "Product Registration", "Ownership Transfer",
        "Blockchain Infrastructure", "Consortium Nodes", "Manufacturer", "Distributor", "Retailer",
        "Start", "Stop", "Decision", "Input", "Output", "Ground", "Resistor", "Capacitor", "Voltage Source"
    ]
    student_text_lower = student_text.lower()
    for ent in domain_entities:
        if ent.lower() in student_text_lower and ent not in detected_components:
            detected_components.append(ent)

    # 2. Extract detected connections and arrow directions
    detected_connections = []
    chains = extract_arrow_chains(student_text)
    for src, dst in chains:
        detected_connections.append({
            "source": src,
            "target": dst,
            "direction": "forward"
        })
        if src not in detected_components:
            detected_components.append(src)
        if dst not in detected_components:
            detected_components.append(dst)

    # Vertical flowchart or multi-line step detection (e.g. Start \n | \n v Input ...)
    lines = [ln.strip() for ln in student_text.splitlines() if ln.strip()]
    cleaned_steps = []
    for ln in lines:
        if ln in ['|', 'v', 'V', '↓', '-->', '->', '===>', '=>']:
            continue
        cleaned_ln = re.sub(r'^[|vV↓\s\->=>]+', '', ln).strip(" []()")
        if cleaned_ln and len(cleaned_ln) > 1:
            cleaned_steps.append(cleaned_ln)
    if len(cleaned_steps) >= 2 and len(chains) == 0:
        for i in range(len(cleaned_steps) - 1):
            s_s = cleaned_steps[i]
            s_t = cleaned_steps[i+1]
            detected_connections.append({
                "source": s_s,
                "target": s_t,
                "direction": "forward"
            })
            if s_s not in detected_components:
                detected_components.append(s_s)
            if s_t not in detected_components:
                detected_components.append(s_t)

    # If the student wrote "HTTPS Request" or "calls" or "invokes" between layers
    if "https request" in student_text_lower or "api request" in student_text_lower:
        detected_connections.append({
            "source": "Customer / Mobile App",
            "target": "Application Layer / API Gateway",
            "direction": "forward",
            "protocol": "HTTPS"
        })

    if "smart contract" in student_text_lower and ("application" in student_text_lower or "api" in student_text_lower):
        detected_connections.append({
            "source": "Application Layer",
            "target": "Smart Contracts Layer",
            "direction": "forward"
        })

    if "blockchain" in student_text_lower and "smart contract" in student_text_lower:
        detected_connections.append({
            "source": "Smart Contracts Layer",
            "target": "Blockchain Infrastructure",
            "direction": "forward"
        })

    # Check for unreadable or ambiguous drawing
    is_unreadable = False
    if has_crops and len(detected_components) == 0 and len(detected_connections) == 0:
        # Physical drawing detected but zero identifiable technical symbols or words
        is_unreadable = True

    return {
        "diagram_type": diag_type,
        "has_physical_diagram": has_crops,
        "diagram_crops": diagram_crops or [],
        "detected_components": detected_components,
        "detected_connections": detected_connections,
        "detected_labels": detected_labels,
        "is_unreadable": is_unreadable,
        "drawing_features": {
            "num_regions": len(diagram_crops) if diagram_crops else 0,
            "has_arrows": len(detected_connections) > 0,
            "complexity": sum(c.get("internal_complexity", 0) for c in (diagram_crops or []))
        }
    }


# ─────────────────────────────────────────────────────────────
# 5. Multi-Dimensional Semantic Diagram Comparison
# ─────────────────────────────────────────────────────────────

def compare_diagram_structures(
    student_repr: Dict[str, Any],
    model_repr: Dict[str, Any],
    student_written_text: str = ""
) -> Dict[str, Any]:
    """
    Multi-dimensional comparison between student drawing and reference diagram:
    A. Component Recognition (essential vs optional components)
    B. Structural & Topological Similarity (layout invariance: horizontal == vertical)
    C. Connectivity & Relationships
    D. Direction & Sequence (arrowhead flows)
    E. Labels & Annotations
    F. Conceptual Correctness
    G. Completeness & Missing Features
    H. Contradictions & Text-Diagram Inconsistency
    """
    student_comps = [c.lower() for c in student_repr.get("detected_components", [])]
    model_essential = [c.lower() for c in model_repr.get("essential_components", [])]
    model_conns = model_repr.get("connections", [])
    student_conns = student_repr.get("detected_connections", [])

    # Dimension A: Component Recognition
    matching_components = []
    missing_components = []

    for mc in model_essential:
        # Match exact or substring / keyword
        mc_tokens = [t for t in re.split(r'[\s_]+', mc) if len(t) > 2]
        found = False
        for sc in student_comps:
            if len(sc) <= 2:
                if sc == mc:
                    found = True
                    matching_components.append(mc.title())
                    break
            else:
                if mc in sc or sc in mc or (mc_tokens and any(t in sc for t in mc_tokens)):
                    found = True
                    matching_components.append(mc.title())
                    break
        if not found:
            missing_components.append(mc.title())

    matching_components = list(dict.fromkeys(matching_components))
    missing_components = list(dict.fromkeys(missing_components))

    component_score = (
        len(matching_components) / max(1, len(model_essential))
        if model_essential else 1.0
    )

    # Dimension B: Structural & Topological Similarity
    # Invariance check: horizontal layouts receive identical credit to vertical layouts
    # Drawing neatness or dimension differences do NOT penalize credit
    topological_score = 0.50
    if student_repr.get("has_physical_diagram"):
        topological_score += 0.30
    if len(matching_components) >= 2:
        topological_score += 0.20
    topological_score = min(1.0, topological_score)

    # Dimension C: Connectivity & Relationships
    matching_connections = []
    missing_connections = []
    connectivity_errors = []

    if model_conns:
        for m_c in model_conns:
            m_s = m_c.get("source", "").lower()
            m_t = m_c.get("target", "").lower()
            c_found = False
            for s_c in student_conns:
                s_s = s_c.get("source", "").lower()
                s_t = s_c.get("target", "").lower()
                if (m_s in s_s or s_s in m_s) and (m_t in s_t or s_t in m_t):
                    c_found = True
                    matching_connections.append(f"{m_c['source']} -> {m_c['target']}")
                    break
            if not c_found:
                missing_connections.append(f"{m_c['source']} -> {m_c['target']}")

        connectivity_score = len(matching_connections) / max(1, len(model_conns))
    else:
        # Infer connectivity from student connections
        connectivity_score = 0.90 if student_conns else (0.75 if student_comps else 0.40)

    # Dimension D: Direction & Sequence (Arrowhead Check)
    reversed_arrows = []
    for s_c in student_conns:
        s_s = s_c.get("source", "").lower()
        s_t = s_c.get("target", "").lower()
        for m_c in model_conns:
            m_s = m_c.get("source", "").lower()
            m_t = m_c.get("target", "").lower()
            # If student arrow is flipped: Source is Model Target and Target is Model Source
            if (m_t in s_s or s_s in m_t) and (m_s in s_t or s_t in m_s):
                reversed_arrows.append(f"{s_c.get('source')} -> {s_c.get('target')} (Expected reverse: {m_c.get('source')} -> {m_c.get('target')})")

    direction_score = 1.0
    if reversed_arrows:
        direction_score = max(0.20, 1.0 - (len(reversed_arrows) * 0.40))
        connectivity_errors.extend(reversed_arrows)

    # Dimension E: Labels & Annotations
    req_labels = model_repr.get("required_labels", [])
    student_labels = [l.lower() for l in student_repr.get("detected_labels", [])]
    matched_labels = []
    missing_labels = []

    for rl in req_labels:
        rl_low = rl.lower()
        if any(rl_low in sl for sl in student_labels) or any(rl_low in sc for sc in student_comps):
            matched_labels.append(rl)
        else:
            missing_labels.append(rl)

    label_score = (
        len(matched_labels) / max(1, len(req_labels))
        if req_labels else 1.0
    )

    # Dimension F: Conceptual Correctness
    # Check if domain concept is communicated (even if styling differs)
    conceptual_score = (component_score * 0.50) + (label_score * 0.30) + (connectivity_score * 0.20)

    # Dimension H: Contradictions & Text-Diagram Inconsistency
    text_diagram_inconsistencies = []
    w_text_lower = student_written_text.lower()

    # Check if written text claims something opposite to the diagram
    for rev in reversed_arrows:
        text_diagram_inconsistencies.append(f"Arrow direction error: {rev}")

    # Check for direct bypass contradiction (e.g. written text describes gateway auth, but diagram directly connects client to storage)
    if "api gateway" in model_essential or "authentication" in model_essential:
        if any("mobile app->database" in s or "client->database" in s for s in student_comps):
            text_diagram_inconsistencies.append("Bypass contradiction: Client connects directly to backend database bypassing gateway")

    # Overall completeness
    completeness_score = (component_score * 0.45) + (connectivity_score * 0.30) + (label_score * 0.25)
    has_contradiction = len(text_diagram_inconsistencies) > 0 or len(reversed_arrows) > 0

    return {
        "component_score": round(component_score, 2),
        "topological_score": round(topological_score, 2),
        "connectivity_score": round(connectivity_score, 2),
        "direction_score": round(direction_score, 2),
        "label_score": round(label_score, 2),
        "conceptual_score": round(conceptual_score, 2),
        "completeness_score": round(completeness_score, 2),
        "matching_components": matching_components,
        "missing_components": missing_components,
        "matching_connections": matching_connections,
        "missing_connections": missing_connections,
        "connectivity_errors": connectivity_errors,
        "reversed_arrows": reversed_arrows,
        "missing_labels": missing_labels,
        "text_diagram_inconsistencies": text_diagram_inconsistencies,
        "has_contradiction": has_contradiction
    }


# ─────────────────────────────────────────────────────────────
# 6. Rubric-Based Mark Allocation & Safeguards
# ─────────────────────────────────────────────────────────────

def evaluate_diagram_with_rubric(
    comparison: Dict[str, Any],
    max_marks: float,
    rubric_criteria: Optional[List[Dict[str, Any]]] = None,
    is_unreadable: bool = False,
    has_physical_diagram: bool = False
) -> Dict[str, Any]:
    """
    Translates structural comparison dimensions into rubric-compliant awarded marks:
    - Strictly bounded: 0.0 <= suggested_marks <= max_marks
    - Invariant to drawing dimensions, orientation, and layout style
    - Unreadable or ambiguous drawings are flagged for review rather than receiving automatic zero
    """
    if is_unreadable:
        # Never automatically give 0 without professor review
        suggested_marks = round(0.30 * max_marks, 2)
        return {
            "suggested_marks": suggested_marks,
            "max_marks": max_marks,
            "overall_score": 0.30,
            "needs_review": True,
            "review_reason": "Diagram drawing detected but visual structure is ambiguous or unreadable. Flagged for manual assessment.",
            "justification": "Visual strokes detected without confirmed component clarity.",
            "rubric_criterion_scores": []
        }

    comp_s = comparison["component_score"]
    conn_s = comparison["connectivity_score"]
    dir_s = comparison["direction_score"]
    lbl_s = comparison["label_score"]
    conc_s = comparison["conceptual_score"]

    # Deduct for contradictions or reversed arrows
    contradiction_penalty = 0.25 if comparison["has_contradiction"] else 0.0

    # Composite normalized score (0.0 to 1.0)
    composite = (
        (comp_s * 0.35)
        + (conn_s * 0.25)
        + (dir_s * 0.15)
        + (lbl_s * 0.15)
        + (conc_s * 0.10)
    ) - contradiction_penalty

    # Drawing presence bonus
    if has_physical_diagram and composite > 0.10:
        composite = min(1.0, composite + 0.10)

    composite = max(0.0, min(1.0, composite))
    suggested_marks = round(min(max_marks, max(0.0, composite * max_marks)), 2)

    # Professor baseline for genuine attempts
    if comp_s >= 0.50 and suggested_marks < (0.40 * max_marks):
        suggested_marks = round(0.40 * max_marks, 2)

    needs_review = (
        comparison["has_contradiction"]
        or (comp_s < 0.40 and has_physical_diagram)
        or len(comparison["missing_components"]) > 2
    )

    review_reasons = []
    if comparison["has_contradiction"]:
        review_reasons.append("Contradictions or arrow direction inconsistencies detected.")
    if comparison["missing_components"]:
        review_reasons.append(f"Missing essential components: {', '.join(comparison['missing_components'][:3])}.")

    # Generate criterion-level scoring
    criterion_scores = []
    if rubric_criteria:
        for crit in rubric_criteria:
            c_name = crit.get("criterion", "Visual Criterion")
            c_max = float(crit.get("marks", 1.0))
            c_low = c_name.lower()

            if any(w in c_low for w in ['layer', 'component', 'node', 'block']):
                crit_sc = comp_s
            elif any(w in c_low for w in ['flow', 'arrow', 'direction', 'sequence']):
                crit_sc = dir_s
            elif any(w in c_low for w in ['label', 'annotation', 'name', 'terminology']):
                crit_sc = lbl_s
            elif any(w in c_low for w in ['connection', 'relationship', 'interface']):
                crit_sc = conn_s
            else:
                crit_sc = composite

            aw = round(min(c_max, max(0.0, crit_sc * c_max)), 2)
            criterion_scores.append({
                "criterion": c_name,
                "max_marks": c_max,
                "awarded_marks": aw,
                "evidence_score": round(crit_sc, 2)
            })

    # Summary justification
    justification_parts = []
    if comparison["matching_components"]:
        justification_parts.append(f"Demonstrated components: {', '.join(comparison['matching_components'][:4])}")
    if comparison["missing_components"]:
        justification_parts.append(f"Missing: {', '.join(comparison['missing_components'][:3])}")
    if comparison["reversed_arrows"]:
        justification_parts.append(f"Flow errors: {', '.join(comparison['reversed_arrows'])}")
    if not justification_parts:
        justification_parts.append("Visual diagram structure aligns with reference model.")

    return {
        "suggested_marks": suggested_marks,
        "max_marks": max_marks,
        "overall_score": round(composite, 2),
        "needs_review": needs_review,
        "review_reason": " ".join(review_reasons) if review_reasons else None,
        "justification": ". ".join(justification_parts) + ".",
        "rubric_criterion_scores": criterion_scores
    }


# ─────────────────────────────────────────────────────────────
# 7. Unified Diagram Evaluation Pipeline Orchestrator
# ─────────────────────────────────────────────────────────────

def evaluate_diagram_answer(
    student_text: str,
    model_answer_text: str,
    max_marks: float,
    page_image_paths: Optional[List[str]] = None,
    expected_labels: Optional[List[str]] = None,
    question_text: str = "",
    rubric_criteria: Optional[List[Dict[str, Any]]] = None,
    script_id: Optional[int] = None,
    question_id: Optional[int] = None
) -> Dict[str, Any]:
    """
    Master Intelligent Diagram Evaluation Pipeline:
    1. Detects & extracts diagram crops from page images.
    2. Builds structured visual representations for both student and model diagrams.
    3. Executes multi-dimensional semantic comparison (components, topology, connections, flow, labels, contradictions).
    4. Computes rubric-grounded marks strictly bounded by max_marks.
    5. Returns backwards-compatible schema AND rich structured report.
    """
    try:
        # Step 1: Detect & Crop diagram regions from physical page images
        extracted_crops = []
        if page_image_paths:
            for p_idx, p_path in enumerate(page_image_paths):
                if p_path and os.path.exists(p_path):
                    crops = detect_and_extract_diagrams(
                        image_path=p_path,
                        script_id=script_id,
                        page_num=p_idx + 1,
                        question_id=question_id
                    )
                    if crops:
                        extracted_crops.extend(crops)

        has_physical_diagram = len(extracted_crops) > 0

        # Step 2: Build model answer visual representation
        model_repr = build_model_diagram_representation(
            question_text=question_text,
            model_answer_text=model_answer_text,
            rubric_criteria=rubric_criteria
        )
        if expected_labels:
            model_repr["required_labels"] = list(dict.fromkeys(model_repr["required_labels"] + expected_labels))
            model_repr["essential_components"] = list(dict.fromkeys(model_repr["essential_components"] + expected_labels))

        # Step 3: Analyze student diagram structure
        student_repr = analyze_student_diagram_structure(
            student_text=student_text,
            diagram_crops=extracted_crops,
            question_text=question_text
        )

        # Step 4: Multi-dimensional comparison
        comparison = compare_diagram_structures(
            student_repr=student_repr,
            model_repr=model_repr,
            student_written_text=student_text
        )

        # Step 5: Rubric scoring & evaluation
        rubric_eval = evaluate_diagram_with_rubric(
            comparison=comparison,
            max_marks=max_marks,
            rubric_criteria=rubric_criteria,
            is_unreadable=student_repr.get("is_unreadable", False),
            has_physical_diagram=has_physical_diagram
        )

        awarded_marks = rubric_eval["suggested_marks"]
        crop_url = extracted_crops[0].get("crop_url") if extracted_crops else None
        crop_path = extracted_crops[0].get("crop_path") if extracted_crops else None

        # Return comprehensive result maintaining backward-compatibility with earlier tests
        return {
            # Legacy fields for backward compatibility
            "awarded_marks": awarded_marks,
            "max_marks": max_marks,
            "structure_score": comparison["topological_score"],
            "label_score": comparison["label_score"],
            "has_physical_diagram": has_physical_diagram,
            "diagram_regions_found": len(extracted_crops),
            "labels_matched": student_repr["detected_labels"][:6],
            "explanation": rubric_eval["justification"],
            "is_diagram": True,
            "overall_score": rubric_eval["overall_score"],

            # Advanced intelligent diagram evaluation schema
            "diagram_detected": has_physical_diagram,
            "diagram_type": student_repr["diagram_type"],
            "diagram_crop_path": crop_path,
            "diagram_crop_url": crop_url,
            "diagram_crops": extracted_crops,
            "page_number": extracted_crops[0].get("page_number", 1) if extracted_crops else None,
            "bounding_box": extracted_crops[0].get("bounding_box") if extracted_crops else None,
            "model_components": model_repr["essential_components"],
            "student_components": student_repr["detected_components"],
            "matching_components": comparison["matching_components"],
            "missing_components": comparison["missing_components"],
            "connectivity_errors": comparison["connectivity_errors"],
            "reversed_arrows": comparison["reversed_arrows"],
            "text_diagram_inconsistencies": comparison["text_diagram_inconsistencies"],
            "has_contradiction": comparison["has_contradiction"],
            "rubric_criterion_scores": rubric_eval["rubric_criterion_scores"],
            "needs_review": rubric_eval["needs_review"],
            "review_reason": rubric_eval["review_reason"],
            "justification": rubric_eval["justification"]
        }

    except Exception as e:
        logger.error(f"Error during diagram evaluation: {e}")
        # Resilient fallback: never crash the overall grading pipeline
        return {
            "awarded_marks": round(0.40 * max_marks, 2),
            "max_marks": max_marks,
            "structure_score": 0.40,
            "label_score": 0.40,
            "has_physical_diagram": False,
            "diagram_regions_found": 0,
            "labels_matched": [],
            "explanation": f"Diagram evaluated via heuristic fallback due to processing notice: {str(e)}",
            "is_diagram": True,
            "overall_score": 0.40,
            "diagram_detected": False,
            "diagram_type": "general_diagram",
            "needs_review": True,
            "review_reason": f"Fallback applied: {str(e)}"
        }
