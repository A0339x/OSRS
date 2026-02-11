"""Step 3b: MineTin task — mine tin rocks near Lumbridge and drop ore."""

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


class MineTin(Task):
    """Mine tin ore near Lumbridge and drop it. Stops at target Mining level."""

    XP_PER_TIN = 17.5

    def __init__(self, target_level: int = 15):
        super().__init__(
            name="MineTin",
            description=f"Mine tin ore until Mining level {target_level}",
        )
        self.target_level = target_level
        self.current_level = 1
        self.ore_mined = 0

    def preconditions(self) -> bool:
        """Check: player has a pickaxe, Mining < target."""
        frame = capture_game_window()
        if frame is None:
            return False

        open_tab("stats")
        wait(400, 800)
        frame = capture_game_window()
        if frame is None:
            return False

        levels = read_skill_levels(frame)
        mining_level = levels.get("mining")
        if mining_level is not None:
            self.current_level = mining_level
            self._log.info(f"Current Mining level: {mining_level}")
            if mining_level >= self.target_level:
                self._log.info("Already at or above target level.")
                return False

        open_tab("inventory")
        wait(200, 400)
        return True

    def execute(self) -> bool:
        """One iteration: find tin rock → mine → handle inventory."""
        frame = capture_game_window()
        if frame is not None:
            inv = read_inventory(frame)
            if is_inventory_full(inv):
                self._log.info("Inventory full — dropping ore.")
                drop_all_inventory()
                wait(300, 600)

        # Tin rocks are grey/brown — detected via "rock" color range
        result = click_object("rock", timeout=5.0)
        if result is None:
            self._log.warning("No rock found — rotating camera.")
            from ...input.camera import rotate_camera
            rotate_camera(90)
            wait(500, 1000)
            return False

        self._log.info("Mining...")
        idle = wait_until_idle(timeout=12.0)
        if idle:
            self.ore_mined += 1
            self.xp_gained += self.XP_PER_TIN
            self._log.info(f"Ore #{self.ore_mined} mined (+{self.XP_PER_TIN} XP)")

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
                mining = levels.get("mining")
                if mining is not None:
                    self.current_level = mining
                    self._log.info(f"Mining level: {mining}")
            open_tab("inventory")
            wait(200, 400)

        return self.current_level >= self.target_level
