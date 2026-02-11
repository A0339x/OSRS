"""Step 2c: Camera control — rotation, zoom, and compass reset."""

import random
import time
from typing import Optional

import pyautogui

from ..utils.config import COMPASS, GAME_AREA
from ..utils.logger import log
from .mouse import drag, human_click, human_move
from .timing import wait


def rotate_camera(degrees: float, duration: Optional[float] = None):
    """Rotate the camera by dragging with the middle mouse button.

    Positive degrees = clockwise, negative = counter-clockwise.
    The drag is performed in the center of the game viewport.

    Args:
        degrees: How many degrees to rotate (approximate).
        duration: Drag duration in seconds (auto-calculated if None).
    """
    ga = GAME_AREA
    center_x = ga["x"] + ga["w"] // 2
    center_y = ga["y"] + ga["h"] // 2

    # Approximate pixels per degree of camera rotation.
    # This is empirical — OSRS uses ~3-4 px per degree with middle-drag.
    px_per_degree = 3.5
    dx = int(degrees * px_per_degree)

    start = (center_x - dx // 2, center_y + random.randint(-10, 10))
    end = (center_x + dx // 2, center_y + random.randint(-10, 10))

    if duration is None:
        duration = 0.2 + abs(degrees) / 360 * 0.5

    log.debug(f"Rotating camera {degrees:.0f}° ({dx}px drag)")
    drag(start, end, button="middle", duration=duration)
    wait(100, 250)


def zoom(clicks: int):
    """Zoom the camera in or out.

    Args:
        clicks: Positive = zoom in, negative = zoom out.
    """
    ga = GAME_AREA
    center_x = ga["x"] + ga["w"] // 2 + random.randint(-20, 20)
    center_y = ga["y"] + ga["h"] // 2 + random.randint(-20, 20)

    human_move(center_x, center_y)
    wait(50, 150)

    for _ in range(abs(clicks)):
        pyautogui.scroll(1 if clicks > 0 else -1)
        time.sleep(random.uniform(0.05, 0.12))

    log.debug(f"Zoomed {'in' if clicks > 0 else 'out'} {abs(clicks)} clicks")


def set_compass_north():
    """Click the compass icon to reset camera to face north."""
    cx = COMPASS["x"] + COMPASS["w"] // 2
    cy = COMPASS["y"] + COMPASS["h"] // 2
    log.info("Resetting compass to north.")
    human_click(cx, cy)
    wait(300, 600)


def pitch_up(degrees: float = 45):
    """Tilt camera up by middle-dragging vertically upward."""
    ga = GAME_AREA
    center_x = ga["x"] + ga["w"] // 2 + random.randint(-10, 10)
    center_y = ga["y"] + ga["h"] // 2

    px_per_degree = 3.0
    dy = int(degrees * px_per_degree)

    start = (center_x, center_y + dy // 2)
    end = (center_x, center_y - dy // 2)

    drag(start, end, button="middle", duration=0.3)
    wait(100, 250)


def pitch_down(degrees: float = 45):
    """Tilt camera down by middle-dragging vertically downward."""
    pitch_up(-degrees)
