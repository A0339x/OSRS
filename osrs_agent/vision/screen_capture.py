"""Step 1a: Screen capture — find the OSRS game window and capture it."""

import os
import time
from typing import Optional

import cv2
import numpy as np

try:
    import pygetwindow as gw
except ImportError:
    gw = None

try:
    import mss
except ImportError:
    mss = None

try:
    import pyautogui
except ImportError:
    pyautogui = None

from ..utils.config import GAME_WINDOW_TITLE, SCREENSHOTS_DIR
from ..utils.logger import log


def find_game_window(title: str = GAME_WINDOW_TITLE) -> Optional[dict]:
    """Find the OSRS (or RuneLite) game window by title.

    Returns a dict with keys: left, top, width, height — or None if not found.
    Searches for windows whose title contains the search string (case-insensitive).
    """
    if gw is None:
        log.warning("pygetwindow not available — falling back to full screen capture.")
        return None

    # Try common OSRS window titles
    search_titles = [title, "RuneLite", "OSRS", "Old School RuneScape"]
    for search in search_titles:
        try:
            windows = gw.getWindowsWithTitle(search)
            if windows:
                win = windows[0]
                log.info(f"Found game window: '{win.title}' at ({win.left}, {win.top}) "
                         f"size {win.width}x{win.height}")
                return {
                    "left": win.left,
                    "top": win.top,
                    "width": win.width,
                    "height": win.height,
                    "title": win.title,
                }
        except Exception as e:
            log.debug(f"Error searching for '{search}': {e}")
            continue

    log.warning("Game window not found by title. Listing all visible windows:")
    try:
        for w in gw.getAllWindows():
            if w.title.strip():
                log.info(f"  Window: '{w.title}' ({w.width}x{w.height})")
    except Exception:
        pass

    return None


def capture_game_window(window: Optional[dict] = None) -> Optional[np.ndarray]:
    """Capture the game window region and return it as a BGR numpy array.

    If *window* is None, attempts to find it automatically.
    Falls back to full-screen capture if the window can't be located.
    """
    if window is None:
        window = find_game_window()

    if mss is not None:
        return _capture_mss(window)
    elif pyautogui is not None:
        return _capture_pyautogui(window)
    else:
        log.error("No screen capture backend available (need mss or pyautogui).")
        return None


def _capture_mss(window: Optional[dict]) -> Optional[np.ndarray]:
    """Capture using the mss library (fastest)."""
    with mss.mss() as sct:
        if window:
            monitor = {
                "left": window["left"],
                "top": window["top"],
                "width": window["width"],
                "height": window["height"],
            }
        else:
            monitor = sct.monitors[1]  # primary monitor

        img = sct.grab(monitor)
        # mss returns BGRA — convert to BGR for OpenCV
        frame = np.array(img)
        frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
        return frame


def _capture_pyautogui(window: Optional[dict]) -> Optional[np.ndarray]:
    """Capture using pyautogui (slower but always available)."""
    if window:
        screenshot = pyautogui.screenshot(
            region=(window["left"], window["top"], window["width"], window["height"])
        )
    else:
        screenshot = pyautogui.screenshot()

    frame = np.array(screenshot)
    frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
    return frame


def save_screenshot(frame: np.ndarray, filename: Optional[str] = None) -> str:
    """Save a captured frame to the screenshots directory. Returns the file path."""
    os.makedirs(SCREENSHOTS_DIR, exist_ok=True)
    if filename is None:
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        filename = f"capture_{timestamp}.png"
    path = os.path.join(SCREENSHOTS_DIR, filename)
    cv2.imwrite(path, frame)
    log.info(f"Screenshot saved: {path}")
    return path


# ---------------------------------------------------------------------------
# Quick self-test
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print("=== OSRS Screen Capture Test ===")
    win = find_game_window()
    if win:
        print(f"Window found: {win['title']} — {win['width']}x{win['height']}")
    else:
        print("Game window not found, will capture full screen.")

    frame = capture_game_window(win)
    if frame is not None:
        print(f"Captured frame shape: {frame.shape}")
        path = save_screenshot(frame, "test_capture.png")
        print(f"Saved to: {path}")
    else:
        print("ERROR: Failed to capture screen.")
