"""Step 3c: State machine — main loop that orchestrates tasks and handles interruptions."""

import time
from enum import Enum, auto
from typing import Dict, List, Optional

from ..input.timing import wait, wait_long
from ..utils.logger import log
from ..vision.player_state import read_player_state
from ..vision.screen_capture import capture_game_window
from ..vision.stats_reader import read_skill_levels
from ..vision.inventory_reader import read_inventory
from .task import Task, TaskStatus


class AgentPhase(Enum):
    IDLE = auto()
    RUNNING_TASK = auto()
    HANDLING_INTERRUPT = auto()
    STOPPED = auto()


class StateMachine:
    """Main agent loop that reads game state, selects tasks, and handles interruptions.

    Usage:
        sm = StateMachine()
        sm.add_task(ChopTrees(target_level=15))
        sm.add_task(FishShrimp(target_level=20))
        sm.run()
    """

    def __init__(self):
        self.phase = AgentPhase.IDLE
        self.task_queue: List[Task] = []
        self.current_task: Optional[Task] = None
        self.completed_tasks: List[Task] = []
        self.game_state: Dict = {}
        self.prev_frame = None
        self.total_runtime = 0.0
        self._running = False

    def add_task(self, task: Task):
        """Add a task to the queue."""
        self.task_queue.append(task)
        log.info(f"Queued task: {task.name} — {task.description}")

    def _read_game_state(self) -> Dict:
        """Capture screen and read all relevant game state."""
        frame = capture_game_window()
        if frame is None:
            return self.game_state

        state = {}

        # Player state (HP, prayer, combat, idle)
        player = read_player_state(frame, prev_frame=self.prev_frame)
        state["player"] = player

        # Inventory
        state["inventory"] = read_inventory(frame)

        # Store frame for next idle comparison
        self.prev_frame = frame
        self.game_state = state
        return state

    def _check_interruptions(self, state: Dict) -> Optional[str]:
        """Check for situations that need immediate handling.

        Returns a string describing the interruption, or None.
        """
        player = state.get("player", {})

        # Low HP — eat food or teleport
        hp = player.get("hp")
        if hp is not None and hp < 10:
            return "low_hp"

        # Death detection — if HP hits 0
        if hp is not None and hp <= 0:
            return "death"

        # Unexpected combat
        if player.get("in_combat") and self.current_task:
            # Only interrupt if the current task isn't combat-related
            if "combat" not in self.current_task.name.lower():
                return "unexpected_combat"

        return None

    def _handle_interruption(self, interruption: str):
        """Handle an interruption event."""
        log.warning(f"INTERRUPTION: {interruption}")
        self.phase = AgentPhase.HANDLING_INTERRUPT

        if interruption == "low_hp":
            log.info("Low HP — pausing task. Eat food or teleport.")
            # For now, just wait and hope auto-regen or player intervenes.
            # A more advanced version would eat food from inventory.
            wait_long()

        elif interruption == "death":
            log.error("Player died! Stopping agent.")
            self._running = False

        elif interruption == "unexpected_combat":
            log.info("Unexpected combat — waiting for it to resolve.")
            # Wait for combat to end
            for _ in range(20):
                wait(1000, 2000)
                frame = capture_game_window()
                if frame is not None:
                    ps = read_player_state(frame)
                    if not ps.get("in_combat"):
                        log.info("Combat resolved.")
                        break

        self.phase = AgentPhase.RUNNING_TASK if self._running else AgentPhase.STOPPED

    def run(self):
        """Main loop — process task queue until all tasks complete or agent stops."""
        self._running = True
        start_time = time.time()
        log.info("=" * 50)
        log.info("OSRS Agent starting")
        log.info(f"Tasks queued: {len(self.task_queue)}")
        for i, t in enumerate(self.task_queue):
            log.info(f"  {i + 1}. {t.name}: {t.description}")
        log.info("=" * 50)

        while self._running and self.task_queue:
            # Pick next task
            self.current_task = self.task_queue[0]
            self.phase = AgentPhase.RUNNING_TASK
            log.info(f"\n--- Starting task: {self.current_task.name} ---")

            # Run the task
            status = self.current_task.run()

            if status == TaskStatus.COMPLETED:
                log.info(f"Task '{self.current_task.name}' completed successfully!")
                self.completed_tasks.append(self.current_task)
                self.task_queue.pop(0)
            elif status == TaskStatus.FAILED:
                log.error(f"Task '{self.current_task.name}' failed.")
                self.task_queue.pop(0)
            else:
                log.warning(f"Task '{self.current_task.name}' ended with status: {status}")
                self.task_queue.pop(0)

            # Brief pause between tasks
            wait(1000, 2000)

        # Wrap up
        self._running = False
        self.phase = AgentPhase.STOPPED
        self.total_runtime = time.time() - start_time

        log.info("=" * 50)
        log.info("OSRS Agent stopped")
        log.info(f"Total runtime: {self.total_runtime:.0f}s")
        log.info(f"Tasks completed: {len(self.completed_tasks)}/{len(self.completed_tasks) + len(self.task_queue)}")
        for t in self.completed_tasks:
            log.info(f"  ✓ {t.name}: {t.iterations} iterations, {t.xp_gained} XP in {t.elapsed:.0f}s")
        log.info("=" * 50)

    def stop(self):
        """Signal the agent to stop after the current iteration."""
        log.info("Stop requested — agent will halt after current action.")
        self._running = False
        if self.current_task:
            self.current_task.status = TaskStatus.PAUSED
