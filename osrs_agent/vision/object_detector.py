"""Step 1d: Detect game objects using color-based detection and template matching."""

from typing import Dict, List, Optional, Tuple

import cv2
import numpy as np

from ..utils.config import GAME_AREA, OBJECT_COLORS_HSV
from ..utils.logger import log


def detect_objects(
    game_frame: np.ndarray,
    object_type: str,
    min_area: int = 200,
    max_results: int = 10,
) -> List[Dict]:
    """Detect objects of the given type in the game viewport.

    Args:
        game_frame: BGR screenshot of the game window.
        object_type: Key into OBJECT_COLORS_HSV (e.g. "tree", "rock", "fishing_spot").
        min_area: Minimum contour area in pixels to be considered a valid detection.
        max_results: Maximum number of detections to return.

    Returns:
        List of dicts sorted by area (largest first):
            {"center": (x, y), "bbox": (x, y, w, h), "area": int}
    """
    if object_type not in OBJECT_COLORS_HSV:
        log.error(f"Unknown object type: '{object_type}'. "
                  f"Known types: {list(OBJECT_COLORS_HSV.keys())}")
        return []

    color_range = OBJECT_COLORS_HSV[object_type]

    # Crop to just the main game viewport (exclude UI panels)
    ga = GAME_AREA
    viewport = game_frame[ga["y"]:ga["y"] + ga["h"], ga["x"]:ga["x"] + ga["w"]]

    # Convert to HSV
    hsv = cv2.cvtColor(viewport, cv2.COLOR_BGR2HSV)

    lower = np.array(color_range["lower"], dtype=np.uint8)
    upper = np.array(color_range["upper"], dtype=np.uint8)
    mask = cv2.inRange(hsv, lower, upper)

    # Morphological cleanup
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=2)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=1)

    # Find contours
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    detections = []
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area < min_area:
            continue

        x, y, w, h = cv2.boundingRect(cnt)
        cx = ga["x"] + x + w // 2
        cy = ga["y"] + y + h // 2

        detections.append({
            "center": (cx, cy),
            "bbox": (ga["x"] + x, ga["y"] + y, w, h),
            "area": int(area),
        })

    # Sort largest first (usually the closest / most prominent object)
    detections.sort(key=lambda d: d["area"], reverse=True)
    detections = detections[:max_results]

    log.info(f"Detected {len(detections)} '{object_type}' object(s).")
    return detections


def detect_by_template(
    game_frame: np.ndarray,
    template: np.ndarray,
    threshold: float = 0.75,
    max_results: int = 10,
) -> List[Dict]:
    """Find objects matching a template image in the game viewport.

    Args:
        game_frame: BGR screenshot.
        template: BGR template image.
        threshold: Match confidence threshold (0-1).
        max_results: Max detections.

    Returns:
        List of {"center": (x, y), "bbox": (x, y, w, h), "confidence": float}.
    """
    ga = GAME_AREA
    viewport = game_frame[ga["y"]:ga["y"] + ga["h"], ga["x"]:ga["x"] + ga["w"]]

    result = cv2.matchTemplate(viewport, template, cv2.TM_CCOEFF_NORMED)
    locations = np.where(result >= threshold)

    th, tw = template.shape[:2]
    detections = []

    for pt in zip(*locations[::-1]):  # (x, y) pairs
        x, y = int(pt[0]), int(pt[1])
        cx = ga["x"] + x + tw // 2
        cy = ga["y"] + y + th // 2
        conf = float(result[y, x])
        detections.append({
            "center": (cx, cy),
            "bbox": (ga["x"] + x, ga["y"] + y, tw, th),
            "confidence": conf,
        })

    # Non-maximum suppression (simple distance-based)
    detections = _nms(detections, distance=tw // 2)
    detections.sort(key=lambda d: d["confidence"], reverse=True)
    return detections[:max_results]


def _nms(detections: List[Dict], distance: int = 20) -> List[Dict]:
    """Simple non-maximum suppression based on center distance."""
    if not detections:
        return []

    kept = []
    for det in sorted(detections, key=lambda d: d.get("confidence", d.get("area", 0)),
                      reverse=True):
        cx, cy = det["center"]
        too_close = False
        for k in kept:
            kx, ky = k["center"]
            if abs(cx - kx) < distance and abs(cy - ky) < distance:
                too_close = True
                break
        if not too_close:
            kept.append(det)
    return kept


def find_nearest(detections: List[Dict], reference: Tuple[int, int] = None) -> Optional[Dict]:
    """Return the detection nearest to a reference point (defaults to screen center)."""
    if not detections:
        return None

    if reference is None:
        ga = GAME_AREA
        reference = (ga["x"] + ga["w"] // 2, ga["y"] + ga["h"] // 2)

    def dist(d):
        dx = d["center"][0] - reference[0]
        dy = d["center"][1] - reference[1]
        return dx * dx + dy * dy

    return min(detections, key=dist)


def annotate_detections(
    frame: np.ndarray,
    detections: List[Dict],
    label: str = "",
    color: Tuple[int, int, int] = (0, 255, 0),
) -> np.ndarray:
    """Draw bounding boxes and labels on a frame copy (for debugging)."""
    annotated = frame.copy()
    for i, det in enumerate(detections):
        x, y, w, h = det["bbox"]
        cv2.rectangle(annotated, (x, y), (x + w, y + h), color, 2)
        text = f"{label} #{i}" if label else f"#{i}"
        cv2.putText(annotated, text, (x, y - 5), cv2.FONT_HERSHEY_SIMPLEX,
                     0.5, color, 1)
        cx, cy = det["center"]
        cv2.circle(annotated, (cx, cy), 4, (0, 0, 255), -1)
    return annotated


# ---------------------------------------------------------------------------
# Quick self-test
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    from .screen_capture import capture_game_window, save_screenshot

    print("=== OSRS Object Detector Test ===")
    frame = capture_game_window()
    if frame is None:
        print("ERROR: Could not capture game window.")
        raise SystemExit(1)

    save_screenshot(frame, "objects_test_raw.png")

    for obj_type in OBJECT_COLORS_HSV:
        dets = detect_objects(frame, obj_type)
        if dets:
            annotated = annotate_detections(frame, dets, label=obj_type)
            save_screenshot(annotated, f"objects_test_{obj_type}.png")
            print(f"\n{obj_type}: {len(dets)} found")
            for d in dets:
                print(f"  center={d['center']}  area={d['area']}")
        else:
            print(f"\n{obj_type}: none found")
