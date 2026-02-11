"""Step 2d: Core interaction helpers — click objects, inventory, tabs, walk, type."""

import random
import time
from typing import Optional, Tuple

import pyautogui

from ..utils.config import (
    INVENTORY_COLS,
    INVENTORY_ORIGIN,
    INVENTORY_SLOT_H,
    INVENTORY_SLOT_W,
    MINIMAP,
    TABS,
)
from ..utils.logger import log
from ..vision.object_detector import detect_objects, find_nearest
from ..vision.screen_capture import capture_game_window
from .mouse import human_click, human_move, human_right_click
from .timing import sleep_until, wait, wait_medium, wait_short


def click_object(
    object_type: str,
    timeout: float = 5.0,
    right_click: bool = False,
    min_area: int = 200,
) -> Optional[Tuple[int, int]]:
    """Use vision to find a game object and click on it.

    Args:
        object_type: Type key (e.g. "tree", "rock", "fishing_spot").
        timeout: Max time to search before giving up.
        right_click: If True, right-click instead of left-click.
        min_area: Minimum detection area.

    Returns:
        (x, y) clicked, or None if object not found.
    """
    start = time.time()
    while time.time() - start < timeout:
        frame = capture_game_window()
        if frame is None:
            wait(200, 400)
            continue

        detections = detect_objects(frame, object_type, min_area=min_area)
        target = find_nearest(detections)

        if target:
            cx, cy = target["center"]
            log.info(f"Clicking {object_type} at ({cx}, {cy})")
            if right_click:
                return human_right_click(cx, cy)
            else:
                return human_click(cx, cy)

        wait(300, 600)

    log.warning(f"Could not find '{object_type}' within {timeout}s.")
    return None


def click_inventory_slot(slot: int) -> Tuple[int, int]:
    """Click on a specific inventory slot (0-27).

    Slot layout: 4 columns x 7 rows, numbered left-to-right, top-to-bottom.
    """
    if not 0 <= slot <= 27:
        raise ValueError(f"Invalid inventory slot: {slot} (must be 0-27)")

    col = slot % INVENTORY_COLS
    row = slot // INVENTORY_COLS

    x = INVENTORY_ORIGIN["x"] + col * INVENTORY_SLOT_W + INVENTORY_SLOT_W // 2
    y = INVENTORY_ORIGIN["y"] + row * INVENTORY_SLOT_H + INVENTORY_SLOT_H // 2

    log.debug(f"Clicking inventory slot {slot} (row={row}, col={col})")
    return human_click(x, y)


def drop_inventory_slot(slot: int):
    """Right-click an inventory slot and select "Drop"."""
    col = slot % INVENTORY_COLS
    row = slot // INVENTORY_COLS
    x = INVENTORY_ORIGIN["x"] + col * INVENTORY_SLOT_W + INVENTORY_SLOT_W // 2
    y = INVENTORY_ORIGIN["y"] + row * INVENTORY_SLOT_H + INVENTORY_SLOT_H // 2

    human_right_click(x, y)
    wait(200, 400)
    # "Drop" is usually the last/bottom option in the right-click menu.
    # It's typically ~65 pixels below the right-click point.
    human_click(x, y + 65)
    wait_short()


def drop_all_inventory():
    """Drop all items in inventory, column by column (shift-drop pattern)."""
    log.info("Dropping all inventory items.")
    # Enable shift-click drop: hold shift
    pyautogui.keyDown("shift")
    time.sleep(random.uniform(0.05, 0.1))

    # Drop column by column (more efficient path)
    for col in range(INVENTORY_COLS):
        for row in range(7):  # 7 rows
            slot = row * INVENTORY_COLS + col
            x = INVENTORY_ORIGIN["x"] + col * INVENTORY_SLOT_W + INVENTORY_SLOT_W // 2
            y = INVENTORY_ORIGIN["y"] + row * INVENTORY_SLOT_H + INVENTORY_SLOT_H // 2
            human_click(x, y, offset_range=2)
            wait(60, 140)

    pyautogui.keyUp("shift")
    wait_short()


def open_tab(tab_name: str):
    """Click a UI tab by name (e.g. 'inventory', 'stats', 'prayer')."""
    tab_name = tab_name.lower()
    if tab_name not in TABS:
        log.error(f"Unknown tab: '{tab_name}'. Known: {list(TABS.keys())}")
        return

    pos = TABS[tab_name]
    log.debug(f"Opening tab: {tab_name}")
    human_click(pos["x"], pos["y"])
    wait(200, 400)


def type_text(text: str, interval_range: Tuple[float, float] = (0.05, 0.15)):
    """Type text with human-like key delays.

    Args:
        text: The string to type.
        interval_range: (min, max) seconds between keystrokes.
    """
    log.debug(f"Typing: '{text}'")
    for char in text:
        pyautogui.press(char) if len(char) == 1 else pyautogui.press(char)
        time.sleep(random.uniform(*interval_range))


def press_key(key: str, hold_time: Optional[float] = None):
    """Press a single key with optional hold time."""
    if hold_time:
        pyautogui.keyDown(key)
        time.sleep(hold_time)
        pyautogui.keyUp(key)
    else:
        pyautogui.press(key)
    wait(50, 120)


def walk_to(minimap_x: int, minimap_y: int):
    """Click on the minimap to walk to a position.

    Args:
        minimap_x, minimap_y: Coordinates relative to minimap top-left.
    """
    abs_x = MINIMAP["x"] + minimap_x
    abs_y = MINIMAP["y"] + minimap_y

    # Clamp to minimap bounds
    abs_x = max(MINIMAP["x"], min(MINIMAP["x"] + MINIMAP["w"], abs_x))
    abs_y = max(MINIMAP["y"], min(MINIMAP["y"] + MINIMAP["h"], abs_y))

    log.info(f"Walking via minimap click ({abs_x}, {abs_y})")
    human_click(abs_x, abs_y)
    # Walking takes time — wait based on distance from minimap center
    cx = MINIMAP["x"] + MINIMAP["w"] // 2
    cy = MINIMAP["y"] + MINIMAP["h"] // 2
    dist = ((abs_x - cx) ** 2 + (abs_y - cy) ** 2) ** 0.5
    # Rough estimate: ~50ms per pixel of minimap distance
    walk_time_ms = int(dist * 50)
    wait(walk_time_ms, walk_time_ms + 500)


def wait_until_idle(timeout: float = 15.0) -> bool:
    """Wait until the player stops animating (idle detection).

    Returns True if idle detected, False if timed out.
    """
    from ..vision.player_state import detect_idle

    prev_frame = capture_game_window()
    if prev_frame is None:
        return False

    def check_idle():
        nonlocal prev_frame
        time.sleep(0.5)
        curr_frame = capture_game_window()
        if curr_frame is None:
            return False
        idle = detect_idle(prev_frame, curr_frame)
        prev_frame = curr_frame
        return idle

    return sleep_until(check_idle, timeout_s=timeout, poll_interval_ms=600)
