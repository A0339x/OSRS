"""Input layer — human-like mouse, keyboard, and camera control."""
from .mouse import human_click, human_move, human_right_click, drag
from .timing import wait, wait_short, wait_medium, wait_long, maybe_afk
from .camera import rotate_camera, zoom, set_compass_north
from .interactions import (
    click_object,
    click_inventory_slot,
    drop_inventory_slot,
    drop_all_inventory,
    open_tab,
    type_text,
    walk_to,
    wait_until_idle,
)
