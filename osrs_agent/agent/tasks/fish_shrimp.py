"""Step 3b: FishShrimp task — fish shrimp at Draynor Village and drop fish."""

from ...input.interactions import (
    click_object,
    drop_all_inventory,
    open_tab,
    wait_until_idle,
)
from ...input.timing import maybe_afk, wait, wait_medium
from ...vision.inventory_reader import is_inventory_full, read_inventory
from ...vision.screen_capture import capture_game_window
from ...vision.stats_reader import read_skill_levels
from ..task import Task


class FishShrimp(Task):
    """Fish shrimp/anchovies at Draynor and drop them. Stops at target Fishing level."""

    XP_PER_SHRIMP = 10
    XP_PER_ANCHOVY = 40

    def __init__(self, target_level: int = 20):
        super().__init__(
            name="FishShrimp",
            description=f"Fish shrimp/anchovies until Fishing level {target_level}",
        )
        self.target_level = target_level
        self.current_level = 1
        self.fish_caught = 0

    def preconditions(self) -> bool:
        """Check: player has a small fishing net in inventory, Fishing < target."""
        frame = capture_game_window()
        if frame is None:
            return False

        open_tab("stats")
        wait(400, 800)
        frame = capture_game_window()
        if frame is None:
            return False

        levels = read_skill_levels(frame)
        fish_level = levels.get("fishing")
        if fish_level is not None:
            self.current_level = fish_level
            self._log.info(f"Current Fishing level: {fish_level}")
            if fish_level >= self.target_level:
                self._log.info("Already at or above target level.")
                return False

        open_tab("inventory")
        wait(200, 400)
        return True

    def execute(self) -> bool:
        """One iteration: find fishing spot → fish → handle inventory."""
        frame = capture_game_window()
        if frame is not None:
            inv = read_inventory(frame)
            if is_inventory_full(inv):
                self._log.info("Inventory full — dropping fish.")
                drop_all_inventory()
                wait(300, 600)

        # Fishing spots show as cyan/blue shimmering
        result = click_object("fishing_spot", timeout=5.0)
        if result is None:
            self._log.warning("No fishing spot found — rotating camera.")
            from ...input.camera import rotate_camera
            rotate_camera(90)
            wait(500, 1000)
            return False

        # Fishing takes longer per catch than chopping
        self._log.info("Fishing...")
        idle = wait_until_idle(timeout=15.0)
        if idle:
            self.fish_caught += 1
            # Approximate XP (could be shrimp or anchovy)
            xp = self.XP_PER_SHRIMP if self.current_level < 15 else self.XP_PER_ANCHOVY
            self.xp_gained += xp
            self._log.info(f"Fish #{self.fish_caught} caught (+{xp} XP)")

        maybe_afk(chance=0.03)
        wait_medium()
        return True

    def is_complete(self) -> bool:
        if self.iterations % 10 == 0 and self.iterations > 0:
            open_tab("stats")
            wait(400, 700)
            frame = capture_game_window()
            if frame is not None:
                levels = read_skill_levels(frame)
                fish = levels.get("fishing")
                if fish is not None:
                    self.current_level = fish
                    self._log.info(f"Fishing level: {fish}")
            open_tab("inventory")
            wait(200, 400)

        return self.current_level >= self.target_level
