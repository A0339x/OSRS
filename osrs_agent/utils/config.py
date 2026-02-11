"""Configuration and constants for the OSRS agent."""

import os

# Paths
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SCREENSHOTS_DIR = os.path.join(PROJECT_ROOT, "screenshots")
TEMPLATES_DIR = os.path.join(PROJECT_ROOT, "templates")
LOGS_DIR = os.path.join(PROJECT_ROOT, "logs")

# Game window
GAME_WINDOW_TITLE = "Old School RuneScape"  # may also be "RuneLite" if using that client

# UI region offsets (relative to game window top-left)
# These are for the default fixed-mode layout (765x503 game area).
# RuneLite may differ — we auto-detect where possible.
GAME_AREA = {"x": 0, "y": 0, "w": 765, "h": 503}

# Minimap (top-right)
MINIMAP = {"x": 548, "y": 8, "w": 152, "h": 152}

# Inventory grid: 4 columns x 7 rows, each slot ~42x36 px
INVENTORY_ORIGIN = {"x": 563, "y": 213}
INVENTORY_SLOT_W = 42
INVENTORY_SLOT_H = 36
INVENTORY_COLS = 4
INVENTORY_ROWS = 7

# Stats tab positions (skill level text regions relative to stats tab)
# We'll refine these during Step 1b testing.
STATS_TAB_ICON = {"x": 718, "y": 178}  # approximate click target for Stats tab

# Orbs (HP, prayer, run energy) — left side of minimap
HP_ORB = {"x": 522, "y": 56, "w": 24, "h": 24}
PRAYER_ORB = {"x": 522, "y": 90, "w": 24, "h": 24}
RUN_ORB = {"x": 522, "y": 124, "w": 24, "h": 24}
SPEC_ORB = {"x": 522, "y": 158, "w": 24, "h": 24}

# Compass
COMPASS = {"x": 624, "y": 8, "w": 24, "h": 24}

# Tab icons along the bottom of the side panel (approximate x positions)
TABS = {
    "combat":    {"x": 545, "y": 178},
    "stats":     {"x": 571, "y": 178},
    "quests":    {"x": 597, "y": 178},
    "inventory": {"x": 623, "y": 178},
    "equipment": {"x": 649, "y": 178},
    "prayer":    {"x": 675, "y": 178},
    "magic":     {"x": 701, "y": 178},
    "clan":      {"x": 545, "y": 466},
    "friends":   {"x": 571, "y": 466},
    "account":   {"x": 597, "y": 466},
    "logout":    {"x": 623, "y": 466},
    "settings":  {"x": 649, "y": 466},
    "emotes":    {"x": 675, "y": 466},
    "music":     {"x": 701, "y": 466},
}

# Skill names in the order they appear on the stats tab (left to right, top to bottom)
SKILL_NAMES = [
    "attack", "hitpoints", "mining",
    "strength", "agility", "smithing",
    "defence", "herblore", "fishing",
    "ranged", "thieving", "cooking",
    "prayer", "crafting", "firemaking",
    "magic", "fletching", "woodcutting",
    "runecraft", "slayer", "farming",
    "construction", "hunter",
]

# Colors (BGR for OpenCV)
INVENTORY_EMPTY_COLOR_RANGE = {
    "lower": (55, 45, 35),   # dark brown background of empty slot
    "upper": (75, 65, 55),
}

# Object highlight colors in OSRS (when right-click menu isn't open)
# These are approximate HSV ranges.
OBJECT_COLORS_HSV = {
    "tree":         {"lower": (30, 40, 40), "upper": (85, 255, 255)},   # green/brown
    "rock":         {"lower": (0, 0, 80), "upper": (30, 60, 200)},      # grey/brown
    "fishing_spot": {"lower": (90, 80, 80), "upper": (130, 255, 255)},  # cyan/blue shimmer
    "npc_yellow":   {"lower": (20, 150, 150), "upper": (35, 255, 255)}, # yellow NPC text
}

# HP bar colors (above character in combat)
HP_BAR_GREEN_HSV = {"lower": (35, 150, 100), "upper": (85, 255, 255)}
HP_BAR_RED_HSV = {"lower": (0, 150, 100), "upper": (10, 255, 255)}
