"""Step 3a: Task system — base class for all bot tasks."""

import time
from abc import ABC, abstractmethod
from enum import Enum, auto
from typing import Optional

from ..utils.logger import log


class TaskStatus(Enum):
    PENDING = auto()
    RUNNING = auto()
    COMPLETED = auto()
    FAILED = auto()
    PAUSED = auto()


class Task(ABC):
    """Base class for all autonomous tasks.

    Subclasses must implement:
        - preconditions()  — can the task start?
        - execute()        — main action loop (called repeatedly)
        - is_complete()    — has the goal been reached?

    Optionally override:
        - handle_failure() — recovery logic
        - on_start()       — one-time setup when task begins
        - on_complete()    — cleanup when task finishes
    """

    def __init__(self, name: str, description: str = ""):
        self.name = name
        self.description = description
        self.status = TaskStatus.PENDING
        self.start_time: Optional[float] = None
        self.end_time: Optional[float] = None
        self.iterations = 0
        self.errors = 0
        self.xp_gained = 0
        self._log = log

    # --- Abstract methods (must implement) ---

    @abstractmethod
    def preconditions(self) -> bool:
        """Check if all preconditions are met to start/continue this task.

        Examples: correct location, required items in inventory, minimum levels.
        """
        ...

    @abstractmethod
    def execute(self) -> bool:
        """Perform one iteration of the task's main action.

        Returns True if the action succeeded, False otherwise.
        Called repeatedly by the state machine until is_complete() or failure.
        """
        ...

    @abstractmethod
    def is_complete(self) -> bool:
        """Check if the task's goal has been reached."""
        ...

    # --- Optional hooks ---

    def handle_failure(self, error: Exception) -> bool:
        """Handle a failure during execution.

        Returns True if recovery succeeded and task should continue,
        False if task should be aborted.
        """
        self._log.error(f"[{self.name}] Failure: {error}")
        self.errors += 1
        if self.errors >= 5:
            self._log.error(f"[{self.name}] Too many errors ({self.errors}), aborting.")
            return False
        return True

    def on_start(self):
        """Called once when the task transitions to RUNNING."""
        self._log.info(f"[{self.name}] Starting: {self.description}")

    def on_complete(self):
        """Called once when the task is marked COMPLETED."""
        elapsed = (self.end_time or time.time()) - (self.start_time or time.time())
        self._log.info(
            f"[{self.name}] Completed in {elapsed:.0f}s — "
            f"{self.iterations} iterations, {self.xp_gained} XP gained"
        )

    # --- Runner ---

    def run(self) -> TaskStatus:
        """Execute the full task lifecycle. Returns final status."""
        # Check preconditions
        if not self.preconditions():
            self._log.warning(f"[{self.name}] Preconditions not met.")
            self.status = TaskStatus.FAILED
            return self.status

        self.status = TaskStatus.RUNNING
        self.start_time = time.time()
        self.on_start()

        while self.status == TaskStatus.RUNNING:
            # Check completion
            if self.is_complete():
                self.status = TaskStatus.COMPLETED
                self.end_time = time.time()
                self.on_complete()
                break

            # Execute one iteration
            try:
                success = self.execute()
                if success:
                    self.iterations += 1
                else:
                    self._log.warning(f"[{self.name}] Execute returned False.")
                    self.errors += 1
            except Exception as e:
                if not self.handle_failure(e):
                    self.status = TaskStatus.FAILED
                    self.end_time = time.time()
                    break

            # Safety check: too many errors
            if self.errors >= 10:
                self._log.error(f"[{self.name}] Exceeded error limit, aborting.")
                self.status = TaskStatus.FAILED
                self.end_time = time.time()
                break

        return self.status

    # --- Utility ---

    @property
    def elapsed(self) -> float:
        """Seconds since task started."""
        if self.start_time is None:
            return 0.0
        end = self.end_time or time.time()
        return end - self.start_time

    def __repr__(self):
        return f"<Task '{self.name}' status={self.status.name} iter={self.iterations}>"
