"""Step 1b: Read skill levels from the Stats tab using OCR."""

import re
from typing import Dict, Optional

import cv2
import numpy as np

try:
    import pytesseract
except ImportError:
    pytesseract = None

try:
    import easyocr
    _easyocr_reader = None
except ImportError:
    easyocr = None

from ..utils.config import SKILL_NAMES, STATS_TAB_ICON
from ..utils.logger import log


def _get_easyocr_reader():
    global _easyocr_reader
    if _easyocr_reader is None:
        _easyocr_reader = easyocr.Reader(["en"], gpu=False)
    return _easyocr_reader


# Stats tab grid layout (3 columns, 8 rows — last row has 2 skills)
# Each cell is approx 62 x 32 pixels.
# The level number sits in the lower-right of each cell.
STATS_GRID = {
    "origin_x": 548,  # relative to game window
    "origin_y": 193,
    "cell_w": 62,
    "cell_h": 32,
    "cols": 3,
    "rows": 8,  # last row only has 2 skills
    # Within each cell, the level text is roughly in this sub-region:
    "level_roi_x": 32,  # offset from cell left
    "level_roi_y": 16,  # offset from cell top
    "level_roi_w": 28,
    "level_roi_h": 14,
}


def _preprocess_for_ocr(roi: np.ndarray) -> np.ndarray:
    """Upscale, convert to grayscale, threshold — optimised for small OSRS digits."""
    # Upscale 4x for better OCR on tiny text
    h, w = roi.shape[:2]
    roi = cv2.resize(roi, (w * 4, h * 4), interpolation=cv2.INTER_CUBIC)

    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)

    # OSRS skill levels are yellow/white text on dark background.
    # Threshold to isolate bright text.
    _, thresh = cv2.threshold(gray, 160, 255, cv2.THRESH_BINARY)

    return thresh


def _ocr_digit(image: np.ndarray) -> Optional[int]:
    """Run OCR on a preprocessed image and try to extract an integer."""
    text = ""

    if pytesseract is not None:
        # Tesseract with digit whitelist
        config = "--psm 7 -c tessedit_char_whitelist=0123456789"
        text = pytesseract.image_to_string(image, config=config).strip()
    elif easyocr is not None:
        reader = _get_easyocr_reader()
        results = reader.readtext(image, detail=0, allowlist="0123456789")
        text = "".join(results).strip()
    else:
        log.error("No OCR backend available (need pytesseract or easyocr).")
        return None

    # Extract first number found
    match = re.search(r"\d+", text)
    if match:
        val = int(match.group())
        if 1 <= val <= 99:
            return val
    return None


def read_skill_levels(game_frame: np.ndarray) -> Dict[str, Optional[int]]:
    """Read all skill levels from the Stats tab in the given game frame.

    The Stats tab must be open when the screenshot is taken.
    Returns a dict mapping skill name -> level (or None if unreadable).
    """
    g = STATS_GRID
    levels: Dict[str, Optional[int]] = {}
    skill_idx = 0

    for row in range(g["rows"]):
        cols_in_row = 2 if row == g["rows"] - 1 else g["cols"]
        for col in range(cols_in_row):
            if skill_idx >= len(SKILL_NAMES):
                break

            skill = SKILL_NAMES[skill_idx]
            skill_idx += 1

            # Cell top-left
            cx = g["origin_x"] + col * g["cell_w"]
            cy = g["origin_y"] + row * g["cell_h"]

            # Level sub-region within cell
            lx = cx + g["level_roi_x"]
            ly = cy + g["level_roi_y"]
            lw = g["level_roi_w"]
            lh = g["level_roi_h"]

            # Bounds check
            if ly + lh > game_frame.shape[0] or lx + lw > game_frame.shape[1]:
                log.warning(f"Skill '{skill}' ROI out of frame bounds, skipping.")
                levels[skill] = None
                continue

            roi = game_frame[ly:ly + lh, lx:lx + lw]
            processed = _preprocess_for_ocr(roi)
            level = _ocr_digit(processed)
            levels[skill] = level
            log.debug(f"  {skill}: {level}")

    return levels


# ---------------------------------------------------------------------------
# Quick self-test
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    from .screen_capture import capture_game_window, save_screenshot

    print("=== OSRS Stats Reader Test ===")
    print("Make sure the Stats tab is open in-game!")

    frame = capture_game_window()
    if frame is None:
        print("ERROR: Could not capture game window.")
        raise SystemExit(1)

    save_screenshot(frame, "stats_test.png")
    levels = read_skill_levels(frame)
    print("\nSkill Levels:")
    for skill, level in levels.items():
        status = str(level) if level is not None else "???"
        print(f"  {skill:15s} : {status}")
