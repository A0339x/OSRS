"""Step 1c: Read inventory — detect filled/empty slots and identify items."""

import os
from typing import Dict, List, Optional, Tuple

import cv2
import numpy as np

from ..utils.config import (
    INVENTORY_COLS,
    INVENTORY_ORIGIN,
    INVENTORY_ROWS,
    INVENTORY_SLOT_H,
    INVENTORY_SLOT_W,
    TEMPLATES_DIR,
)
from ..utils.logger import log


def _slot_region(slot: int) -> Tuple[int, int, int, int]:
    """Return (x, y, w, h) for inventory slot 0-27 relative to game window."""
    col = slot % INVENTORY_COLS
    row = slot // INVENTORY_COLS
    x = INVENTORY_ORIGIN["x"] + col * INVENTORY_SLOT_W
    y = INVENTORY_ORIGIN["y"] + row * INVENTORY_SLOT_H
    return x, y, INVENTORY_SLOT_W, INVENTORY_SLOT_H


def _is_slot_empty(roi: np.ndarray, threshold: float = 0.92) -> bool:
    """Determine if an inventory slot ROI is empty.

    Empty slots have a very uniform dark-brown color. We measure the standard
    deviation of pixel intensity — low stddev → empty.
    """
    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    mean, stddev = cv2.meanStdDev(gray)
    # Empty slots have stddev < ~8 and mean in the brown range (~50-70).
    return float(stddev) < 12.0 and 30 < float(mean) < 90


def read_inventory(game_frame: np.ndarray) -> List[Dict]:
    """Read inventory state from the game frame.

    Returns a list of 28 dicts, one per slot:
        {"slot": 0, "empty": True/False, "item": "unknown" or matched name,
         "center": (x, y)}
    """
    inventory = []
    for slot in range(INVENTORY_COLS * INVENTORY_ROWS):
        x, y, w, h = _slot_region(slot)

        # Bounds check
        if y + h > game_frame.shape[0] or x + w > game_frame.shape[1]:
            inventory.append({"slot": slot, "empty": True, "item": None,
                              "center": (x + w // 2, y + h // 2)})
            continue

        roi = game_frame[y:y + h, x:x + w]
        empty = _is_slot_empty(roi)

        item_name = None
        if not empty:
            item_name = _identify_item(roi)

        inventory.append({
            "slot": slot,
            "empty": empty,
            "item": item_name,
            "center": (x + w // 2, y + h // 2),
        })

    filled = sum(1 for s in inventory if not s["empty"])
    log.info(f"Inventory: {filled}/28 slots filled.")
    return inventory


# ---------------------------------------------------------------------------
# Template matching for item identification
# ---------------------------------------------------------------------------

_template_cache: Dict[str, np.ndarray] = {}


def _load_templates() -> Dict[str, np.ndarray]:
    """Load all item templates from the templates directory.

    Template filenames should be: <item_name>.png  (e.g. oak_logs.png)
    """
    if _template_cache:
        return _template_cache

    if not os.path.isdir(TEMPLATES_DIR):
        log.debug("Templates directory not found — item identification disabled.")
        return {}

    for fname in os.listdir(TEMPLATES_DIR):
        if not fname.lower().endswith(".png"):
            continue
        name = os.path.splitext(fname)[0]
        path = os.path.join(TEMPLATES_DIR, fname)
        tmpl = cv2.imread(path)
        if tmpl is not None:
            _template_cache[name] = tmpl
            log.debug(f"Loaded template: {name}")

    log.info(f"Loaded {len(_template_cache)} item templates.")
    return _template_cache


def _identify_item(slot_roi: np.ndarray, threshold: float = 0.80) -> Optional[str]:
    """Try to match the slot ROI against known item templates.

    Returns the best-matching item name, or 'unknown' if no match.
    """
    templates = _load_templates()
    if not templates:
        return "unknown"

    best_name = "unknown"
    best_score = threshold

    for name, tmpl in templates.items():
        # Resize template to slot size if needed
        th, tw = tmpl.shape[:2]
        sh, sw = slot_roi.shape[:2]
        if th != sh or tw != sw:
            tmpl_resized = cv2.resize(tmpl, (sw, sh))
        else:
            tmpl_resized = tmpl

        result = cv2.matchTemplate(slot_roi, tmpl_resized, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, _ = cv2.minMaxLoc(result)

        if max_val > best_score:
            best_score = max_val
            best_name = name

    return best_name


def count_item(inventory: List[Dict], item_name: str) -> int:
    """Count how many of a specific item are in the inventory."""
    return sum(1 for s in inventory if s.get("item") == item_name)


def is_inventory_full(inventory: List[Dict]) -> bool:
    """Check if all 28 slots are filled."""
    return all(not s["empty"] for s in inventory)


def first_empty_slot(inventory: List[Dict]) -> Optional[int]:
    """Return the slot number of the first empty slot, or None."""
    for s in inventory:
        if s["empty"]:
            return s["slot"]
    return None


# ---------------------------------------------------------------------------
# Quick self-test
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    from .screen_capture import capture_game_window, save_screenshot

    print("=== OSRS Inventory Reader Test ===")
    print("Make sure the Inventory tab is open in-game!")

    frame = capture_game_window()
    if frame is None:
        print("ERROR: Could not capture game window.")
        raise SystemExit(1)

    save_screenshot(frame, "inventory_test.png")
    inv = read_inventory(frame)

    print(f"\nInventory ({sum(1 for s in inv if not s['empty'])}/28 filled):")
    for s in inv:
        status = "EMPTY" if s["empty"] else (s["item"] or "???")
        print(f"  Slot {s['slot']:2d}: {status}")
