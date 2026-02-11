"""Step 1e: Read player state — HP, prayer, run energy, idle detection, combat status."""

import time
from typing import Dict, Optional, Tuple

import cv2
import numpy as np

try:
    import pytesseract
except ImportError:
    pytesseract = None

from ..utils.config import (
    GAME_AREA,
    HP_BAR_GREEN_HSV,
    HP_BAR_RED_HSV,
    HP_ORB,
    PRAYER_ORB,
    RUN_ORB,
    SPEC_ORB,
)
from ..utils.logger import log


def _read_orb_value(game_frame: np.ndarray, orb: Dict) -> Optional[int]:
    """Read the numeric value displayed on an orb (HP/prayer/run/spec).

    Orbs show a number overlaid on a circular icon. We crop, preprocess, and OCR.
    """
    x, y, w, h = orb["x"], orb["y"], orb["w"], orb["h"]

    if y + h > game_frame.shape[0] or x + w > game_frame.shape[1]:
        return None

    roi = game_frame[y:y + h, x:x + w]

    # Upscale 4x
    roi = cv2.resize(roi, (w * 4, h * 4), interpolation=cv2.INTER_CUBIC)
    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    _, thresh = cv2.threshold(gray, 180, 255, cv2.THRESH_BINARY)

    if pytesseract is None:
        return None

    config = "--psm 7 -c tessedit_char_whitelist=0123456789"
    text = pytesseract.image_to_string(thresh, config=config).strip()

    import re
    match = re.search(r"\d+", text)
    if match:
        return int(match.group())
    return None


def _read_orb_percentage(game_frame: np.ndarray, orb: Dict) -> float:
    """Estimate orb fill percentage by counting green vs dark pixels.

    Returns a float 0.0 to 1.0.
    """
    x, y, w, h = orb["x"], orb["y"], orb["w"], orb["h"]
    if y + h > game_frame.shape[0] or x + w > game_frame.shape[1]:
        return 0.0

    roi = game_frame[y:y + h, x:x + w]
    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)

    # Green fill of the orb
    green_mask = cv2.inRange(hsv, np.array([30, 50, 50]), np.array([90, 255, 255]))
    green_pixels = cv2.countNonZero(green_mask)
    total_pixels = w * h

    return green_pixels / total_pixels if total_pixels > 0 else 0.0


def detect_combat(game_frame: np.ndarray) -> bool:
    """Detect if the player is in combat by looking for HP bars above character.

    HP bars are thin green/red horizontal bars near the center of the viewport.
    """
    ga = GAME_AREA
    # Check the area above the player character (roughly center of viewport)
    center_x = ga["x"] + ga["w"] // 2
    center_y = ga["y"] + ga["h"] // 2

    # Search region above player
    search_y = max(0, center_y - 80)
    search_h = 60
    search_x = max(0, center_x - 40)
    search_w = 80

    roi = game_frame[search_y:search_y + search_h, search_x:search_x + search_w]
    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)

    # Look for the green HP bar
    green_lower = np.array(HP_BAR_GREEN_HSV["lower"], dtype=np.uint8)
    green_upper = np.array(HP_BAR_GREEN_HSV["upper"], dtype=np.uint8)
    green_mask = cv2.inRange(hsv, green_lower, green_upper)

    # Look for the red HP bar
    red_lower = np.array(HP_BAR_RED_HSV["lower"], dtype=np.uint8)
    red_upper = np.array(HP_BAR_RED_HSV["upper"], dtype=np.uint8)
    red_mask = cv2.inRange(hsv, red_lower, red_upper)

    # HP bars are thin horizontal lines — look for horizontal runs of green/red
    combined = cv2.bitwise_or(green_mask, red_mask)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (15, 2))
    hp_bar_mask = cv2.morphologyEx(combined, cv2.MORPH_OPEN, kernel)

    bar_pixels = cv2.countNonZero(hp_bar_mask)
    in_combat = bar_pixels > 30

    if in_combat:
        log.debug(f"Combat detected ({bar_pixels} HP bar pixels).")

    return in_combat


def detect_idle(
    frame_a: np.ndarray,
    frame_b: np.ndarray,
    threshold: float = 0.5,
) -> bool:
    """Detect if the player is idle by comparing two frames taken ~1s apart.

    Compares the player character area. If pixel change is below threshold,
    the player is likely idle (not animating).

    Args:
        frame_a: First capture.
        frame_b: Second capture (taken ~0.5-1s later).
        threshold: Percentage of pixels that must change to be "not idle".

    Returns:
        True if the player appears idle.
    """
    ga = GAME_AREA
    # Player character region (center of viewport)
    cx = ga["x"] + ga["w"] // 2
    cy = ga["y"] + ga["h"] // 2
    half_w, half_h = 30, 40

    roi_a = frame_a[cy - half_h:cy + half_h, cx - half_w:cx + half_w]
    roi_b = frame_b[cy - half_h:cy + half_h, cx - half_w:cx + half_w]

    if roi_a.shape != roi_b.shape:
        return True  # assume idle if shapes don't match

    gray_a = cv2.cvtColor(roi_a, cv2.COLOR_BGR2GRAY)
    gray_b = cv2.cvtColor(roi_b, cv2.COLOR_BGR2GRAY)

    diff = cv2.absdiff(gray_a, gray_b)
    _, diff_thresh = cv2.threshold(diff, 25, 255, cv2.THRESH_BINARY)

    changed_pct = cv2.countNonZero(diff_thresh) / diff_thresh.size * 100

    is_idle = changed_pct < threshold
    log.debug(f"Idle check: {changed_pct:.1f}% pixels changed → {'IDLE' if is_idle else 'ACTIVE'}")
    return is_idle


def read_player_state(game_frame: np.ndarray, prev_frame: Optional[np.ndarray] = None) -> Dict:
    """Read the full player state from the current game frame.

    Returns:
        {
            "hp": int or None,
            "hp_pct": float (0-1),
            "prayer": int or None,
            "prayer_pct": float (0-1),
            "run_energy": int or None,
            "run_pct": float (0-1),
            "spec_pct": float (0-1),
            "in_combat": bool,
            "is_idle": bool or None (None if no prev_frame),
        }
    """
    state = {
        "hp": _read_orb_value(game_frame, HP_ORB),
        "hp_pct": _read_orb_percentage(game_frame, HP_ORB),
        "prayer": _read_orb_value(game_frame, PRAYER_ORB),
        "prayer_pct": _read_orb_percentage(game_frame, PRAYER_ORB),
        "run_energy": _read_orb_value(game_frame, RUN_ORB),
        "run_pct": _read_orb_percentage(game_frame, RUN_ORB),
        "spec_pct": _read_orb_percentage(game_frame, SPEC_ORB),
        "in_combat": detect_combat(game_frame),
        "is_idle": None,
    }

    if prev_frame is not None:
        state["is_idle"] = detect_idle(prev_frame, game_frame)

    log.info(f"Player state: HP={state['hp']} Prayer={state['prayer']} "
             f"Run={state['run_energy']} Combat={state['in_combat']} "
             f"Idle={state['is_idle']}")
    return state


# ---------------------------------------------------------------------------
# Quick self-test
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    from .screen_capture import capture_game_window, save_screenshot

    print("=== OSRS Player State Test ===")
    frame1 = capture_game_window()
    if frame1 is None:
        print("ERROR: Could not capture game window.")
        raise SystemExit(1)

    save_screenshot(frame1, "player_state_test.png")

    print("\nWaiting 1 second for idle detection...")
    time.sleep(1.0)
    frame2 = capture_game_window()

    state = read_player_state(frame2, prev_frame=frame1)
    print("\nPlayer State:")
    for k, v in state.items():
        print(f"  {k:15s}: {v}")
