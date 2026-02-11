"""Step 2b: Human-like delays and timing utilities."""

import random
import time

from ..utils.logger import log


def wait(min_ms: int = 100, max_ms: int = 300) -> float:
    """Sleep for a random duration using a gaussian distribution.

    The gaussian is centered between min and max, with stddev = (max-min)/6
    so that ~99.7% of values fall within [min, max]. Values are clamped.

    Returns the actual sleep time in seconds.
    """
    center = (min_ms + max_ms) / 2
    stddev = (max_ms - min_ms) / 6
    delay_ms = random.gauss(center, stddev)
    delay_ms = max(min_ms, min(max_ms, delay_ms))
    delay_s = delay_ms / 1000.0
    time.sleep(delay_s)
    return delay_s


def wait_short() -> float:
    """Short delay between rapid actions (e.g., successive inventory clicks)."""
    return wait(80, 200)


def wait_medium() -> float:
    """Medium delay between distinct actions (e.g., after clicking a tree)."""
    return wait(300, 700)


def wait_long() -> float:
    """Longer delay simulating brief thought or reaction."""
    return wait(800, 1500)


def wait_action_complete(min_ms: int = 1500, max_ms: int = 3000) -> float:
    """Wait for a game action to complete (e.g., walking, animation)."""
    return wait(min_ms, max_ms)


def maybe_afk(chance: float = 0.02, min_s: float = 5.0, max_s: float = 30.0) -> bool:
    """Occasionally insert a long AFK pause to simulate real player behavior.

    Args:
        chance: Probability of triggering an AFK pause (0-1).
        min_s: Minimum AFK duration in seconds.
        max_s: Maximum AFK duration in seconds.

    Returns:
        True if an AFK pause was taken.
    """
    if random.random() > chance:
        return False

    afk_time = random.uniform(min_s, max_s)
    log.info(f"AFK pause: {afk_time:.1f}s")
    time.sleep(afk_time)
    return True


def sleep_until(condition_fn, timeout_s: float = 10.0, poll_interval_ms: int = 200) -> bool:
    """Sleep until condition_fn() returns True, or timeout.

    Args:
        condition_fn: Callable that returns True when the condition is met.
        timeout_s: Maximum time to wait.
        poll_interval_ms: How often to check the condition.

    Returns:
        True if condition was met, False if timed out.
    """
    start = time.time()
    while time.time() - start < timeout_s:
        if condition_fn():
            return True
        wait(poll_interval_ms - 50, poll_interval_ms + 50)
    return False
