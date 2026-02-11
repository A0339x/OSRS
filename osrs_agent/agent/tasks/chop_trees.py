"""Step 3b: ChopTrees task — chop normal trees near Lumbridge and drop logs."""

from ...input.interactions import (
    click_object,
    drop_all_inventory,
    open_tab,
    wait_until_idle,
)
from ...input.timing import maybe_afk, wait, wait_medium
from ...vision.inventory_reader import is_inventory_full, read_inventory
from ...vision.player_state import read_player_state
from ...vision.screen_capture import capture_game_window
from ...vision.stats_reader import read_skill_levels
from ..task import Task


class ChopTrees(Task):
    """Chop normal trees and drop logs. Stops at a target Woodcutting level."""

    # XP per normal log
    XP_PER_LOG = 25

    def __init__(self, target_level: int = 15):
        super().__init__(
            name="ChopTrees",
            description=f"Chop normal trees until Woodcutting level {target_level}",
        )
        self.target_level = target_level
        self.current_level = 1
        self.logs_chopped = 0

    def preconditions(self) -> bool:
        """Check: player has an axe equipped or in inventory, WC < target."""
        frame = capture_game_window()
        if frame is None:
            self._log.warning("Cannot capture screen for precondition check.")
            return False

        # Read current woodcutting level
        open_tab("stats")
        wait(400, 800)
        frame = capture_game_window()
        if frame is None:
            return False

        levels = read_skill_levels(frame)
        wc_level = levels.get("woodcutting")

        if wc_level is not None:
            self.current_level = wc_level
            self._log.info(f"Current Woodcutting level: {wc_level}")
            if wc_level >= self.target_level:
                self._log.info("Already at or above target level.")
                return False

        # Switch to inventory tab for the main loop
        open_tab("inventory")
        wait(200, 400)
        return True

    def execute(self) -> bool:
        """One iteration: find tree → chop → handle inventory."""
        # Check for full inventory first
        frame = capture_game_window()
        if frame is not None:
            inv = read_inventory(frame)
            if is_inventory_full(inv):
                self._log.info("Inventory full — dropping logs.")
                drop_all_inventory()
                wait(300, 600)

        # Find and click a tree
        result = click_object("tree", timeout=5.0)
        if result is None:
            self._log.warning("No tree found — rotating camera and retrying.")
            from ...input.camera import rotate_camera
            rotate_camera(90)
            wait(500, 1000)
            return False

        # Wait for chopping animation to finish (player goes idle)
        self._log.info("Chopping...")
        idle = wait_until_idle(timeout=12.0)
        if idle:
            self.logs_chopped += 1
            self.xp_gained += self.XP_PER_LOG
            self._log.info(f"Log #{self.logs_chopped} chopped (+{self.XP_PER_LOG} XP)")

        # Random AFK pause for human-like behavior
        maybe_afk(chance=0.03)
        wait_medium()
        return True

    def is_complete(self) -> bool:
        """Check if we've reached the target level."""
        # Periodically re-read level from stats
        if self.iterations % 10 == 0 and self.iterations > 0:
            open_tab("stats")
            wait(400, 700)
            frame = capture_game_window()
            if frame is not None:
                levels = read_skill_levels(frame)
                wc = levels.get("woodcutting")
                if wc is not None:
                    self.current_level = wc
                    self._log.info(f"Woodcutting level: {wc}")
            open_tab("inventory")
            wait(200, 400)

        return self.current_level >= self.target_level
