#!/usr/bin/env python3
"""OSRS Autonomous Agent — main entry point.

Usage:
    python -m osrs_agent.main              # run default task queue
    python -m osrs_agent.main --test-vision  # test vision layer only
    python -m osrs_agent.main --chop 15    # chop trees to level 15
    python -m osrs_agent.main --fish 20    # fish shrimp to level 20
    python -m osrs_agent.main --mine 15    # mine tin to level 15
"""

import argparse
import signal
import sys

from .agent import StateMachine, ChopTrees, FishShrimp, MineTin
from .utils.logger import log
from .vision.screen_capture import capture_game_window, find_game_window, save_screenshot


def test_vision():
    """Run a quick test of the vision layer."""
    print("=" * 50)
    print("OSRS Vision Layer Test")
    print("=" * 50)

    # Step 1a: Screen capture
    print("\n[1a] Screen capture...")
    win = find_game_window()
    if win:
        print(f"  Window: '{win['title']}' at ({win['left']}, {win['top']}) "
              f"size {win['width']}x{win['height']}")
    else:
        print("  Game window not found — capturing full screen.")

    frame = capture_game_window(win)
    if frame is None:
        print("  ERROR: Failed to capture screen.")
        return
    print(f"  Frame shape: {frame.shape}")
    path = save_screenshot(frame, "vision_test.png")
    print(f"  Saved: {path}")

    # Step 1b: Stats
    print("\n[1b] Reading skill levels (Stats tab must be open)...")
    from .vision.stats_reader import read_skill_levels
    levels = read_skill_levels(frame)
    for skill, level in levels.items():
        print(f"  {skill:15s}: {level if level else '???'}")

    # Step 1c: Inventory
    print("\n[1c] Reading inventory...")
    from .vision.inventory_reader import read_inventory
    inv = read_inventory(frame)
    filled = sum(1 for s in inv if not s["empty"])
    print(f"  {filled}/28 slots filled")

    # Step 1d: Object detection
    print("\n[1d] Detecting objects...")
    from .vision.object_detector import detect_objects, annotate_detections
    from .utils.config import OBJECT_COLORS_HSV
    for obj_type in OBJECT_COLORS_HSV:
        dets = detect_objects(frame, obj_type)
        print(f"  {obj_type}: {len(dets)} found")
        if dets:
            annotated = annotate_detections(frame, dets, label=obj_type)
            save_screenshot(annotated, f"detect_{obj_type}.png")

    # Step 1e: Player state
    print("\n[1e] Reading player state...")
    from .vision.player_state import read_player_state
    state = read_player_state(frame)
    for k, v in state.items():
        print(f"  {k:15s}: {v}")

    print("\n" + "=" * 50)
    print("Vision test complete! Check the screenshots/ folder.")
    print("=" * 50)


def main():
    parser = argparse.ArgumentParser(description="OSRS Autonomous Agent")
    parser.add_argument("--test-vision", action="store_true",
                        help="Test the vision layer and exit")
    parser.add_argument("--chop", type=int, metavar="LEVEL",
                        help="Chop trees to target Woodcutting level")
    parser.add_argument("--fish", type=int, metavar="LEVEL",
                        help="Fish shrimp to target Fishing level")
    parser.add_argument("--mine", type=int, metavar="LEVEL",
                        help="Mine tin to target Mining level")
    args = parser.parse_args()

    if args.test_vision:
        test_vision()
        return

    # Build task queue
    sm = StateMachine()

    if args.chop:
        sm.add_task(ChopTrees(target_level=args.chop))
    if args.fish:
        sm.add_task(FishShrimp(target_level=args.fish))
    if args.mine:
        sm.add_task(MineTin(target_level=args.mine))

    # Default: chop to 15, fish to 20, mine to 15
    if not sm.task_queue:
        sm.add_task(ChopTrees(target_level=15))
        sm.add_task(FishShrimp(target_level=20))
        sm.add_task(MineTin(target_level=15))

    # Graceful shutdown on Ctrl+C
    def signal_handler(sig, frame):
        print("\nCtrl+C received — stopping agent...")
        sm.stop()

    signal.signal(signal.SIGINT, signal_handler)

    sm.run()


if __name__ == "__main__":
    main()
