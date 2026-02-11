"""Step 2a: Human-like mouse movement using Bezier curves."""

import math
import random
import time
from typing import Optional, Tuple

import pyautogui

from ..utils.logger import log

# Disable pyautogui's built-in pause and fail-safe for our own control
pyautogui.PAUSE = 0
pyautogui.FAILSAFE = True  # move to top-left corner to abort


def _bezier_point(t: float, points: list) -> Tuple[float, float]:
    """Evaluate a Bezier curve at parameter t (0-1) given control points."""
    n = len(points) - 1
    x, y = 0.0, 0.0
    for i, (px, py) in enumerate(points):
        # Bernstein basis polynomial
        coeff = math.comb(n, i) * (t ** i) * ((1 - t) ** (n - i))
        x += coeff * px
        y += coeff * py
    return x, y


def _generate_control_points(
    start: Tuple[int, int],
    end: Tuple[int, int],
    num_control: int = 2,
) -> list:
    """Generate random control points for a Bezier curve between start and end."""
    sx, sy = start
    ex, ey = end
    dx = ex - sx
    dy = ey - sy
    dist = math.hypot(dx, dy)

    points = [start]
    for i in range(num_control):
        # Fraction along the line
        frac = (i + 1) / (num_control + 1)
        # Base point along the straight line
        bx = sx + dx * frac
        by = sy + dy * frac
        # Random perpendicular offset proportional to distance
        offset_scale = dist * random.uniform(0.1, 0.35)
        angle = math.atan2(dy, dx) + math.pi / 2
        offset = random.uniform(-offset_scale, offset_scale)
        cx = bx + math.cos(angle) * offset
        cy = by + math.sin(angle) * offset
        points.append((cx, cy))
    points.append(end)
    return points


def _ease_in_out(t: float) -> float:
    """Smooth acceleration/deceleration easing function."""
    if t < 0.5:
        return 2 * t * t
    return 1 - (-2 * t + 2) ** 2 / 2


def human_move(
    x: int,
    y: int,
    duration: Optional[float] = None,
    offset_range: int = 3,
) -> Tuple[int, int]:
    """Move the mouse to (x, y) with human-like Bezier curve motion.

    Args:
        x, y: Target coordinates.
        duration: Movement time in seconds. Auto-calculated if None.
        offset_range: Random pixel offset added to target (+/-).

    Returns:
        The actual (x, y) the mouse ended up at (after offset).
    """
    # Apply small random offset
    actual_x = x + random.randint(-offset_range, offset_range)
    actual_y = y + random.randint(-offset_range, offset_range)

    start = pyautogui.position()
    dist = math.hypot(actual_x - start[0], actual_y - start[1])

    if duration is None:
        # Duration scales with distance: ~0.15s for short moves, ~0.6s for long
        duration = 0.15 + (dist / 2000) * 0.5
        duration *= random.uniform(0.85, 1.15)

    # Number of control points: more for longer distances
    num_control = 2 if dist < 400 else 3
    control_points = _generate_control_points(
        (start[0], start[1]), (actual_x, actual_y), num_control
    )

    # Number of interpolation steps
    steps = max(int(dist / 3), 15)
    step_delay = duration / steps

    for i in range(steps + 1):
        t = i / steps
        eased_t = _ease_in_out(t)
        bx, by = _bezier_point(eased_t, control_points)
        pyautogui.moveTo(int(bx), int(by), _pause=False)
        time.sleep(step_delay)

    # Occasional micro-overshoot and correction (~15% of the time)
    if random.random() < 0.15 and dist > 50:
        overshoot_x = actual_x + random.randint(-5, 5)
        overshoot_y = actual_y + random.randint(-5, 5)
        pyautogui.moveTo(overshoot_x, overshoot_y, _pause=False)
        time.sleep(random.uniform(0.02, 0.06))
        pyautogui.moveTo(actual_x, actual_y, _pause=False)
        time.sleep(random.uniform(0.01, 0.03))

    return actual_x, actual_y


def human_click(
    x: int,
    y: int,
    button: str = "left",
    offset_range: int = 3,
    pre_delay: Optional[Tuple[float, float]] = None,
    post_delay: Optional[Tuple[float, float]] = None,
) -> Tuple[int, int]:
    """Move to (x, y) with human motion and click.

    Args:
        x, y: Target coordinates.
        button: 'left' or 'right'.
        offset_range: Random pixel offset on target.
        pre_delay: (min, max) seconds to wait before clicking after arriving.
        post_delay: (min, max) seconds to wait after clicking.

    Returns:
        The actual (x, y) clicked.
    """
    actual_x, actual_y = human_move(x, y, offset_range=offset_range)

    # Short pause before click (simulates human reaction)
    if pre_delay:
        time.sleep(random.uniform(*pre_delay))
    else:
        time.sleep(random.uniform(0.04, 0.12))

    # Click with slight hold (humans don't do instant press-release)
    hold_time = random.uniform(0.04, 0.10)
    pyautogui.mouseDown(button=button, _pause=False)
    time.sleep(hold_time)
    pyautogui.mouseUp(button=button, _pause=False)

    # Post-click delay
    if post_delay:
        time.sleep(random.uniform(*post_delay))
    else:
        time.sleep(random.uniform(0.08, 0.20))

    log.debug(f"Clicked ({actual_x}, {actual_y}) [{button}]")
    return actual_x, actual_y


def human_right_click(x: int, y: int, **kwargs) -> Tuple[int, int]:
    """Convenience wrapper for right-click."""
    return human_click(x, y, button="right", **kwargs)


def human_double_click(x: int, y: int, **kwargs) -> Tuple[int, int]:
    """Double-click with human-like timing between clicks."""
    actual_x, actual_y = human_click(x, y, **kwargs)
    time.sleep(random.uniform(0.05, 0.15))
    # Second click at same position with tiny offset
    pyautogui.mouseDown(button="left", _pause=False)
    time.sleep(random.uniform(0.04, 0.08))
    pyautogui.mouseUp(button="left", _pause=False)
    return actual_x, actual_y


def drag(
    start: Tuple[int, int],
    end: Tuple[int, int],
    button: str = "middle",
    duration: Optional[float] = None,
):
    """Human-like click-and-drag from start to end."""
    human_move(start[0], start[1])
    time.sleep(random.uniform(0.05, 0.12))
    pyautogui.mouseDown(button=button, _pause=False)
    time.sleep(random.uniform(0.05, 0.10))
    human_move(end[0], end[1], duration=duration)
    time.sleep(random.uniform(0.03, 0.08))
    pyautogui.mouseUp(button=button, _pause=False)
