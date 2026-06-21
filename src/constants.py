"""
constants.py
~~~~~~~~~~~~~~~~
Defines key values and unchanging states.
"""

from enum import Enum, auto
import sys
import os
from pathlib import Path


def get_resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller"""
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return Path(base_path) / relative_path


# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GRAY = (150, 150, 150)
GREEN = (0, 255, 0)
RED = (255, 0, 0)
GOLD = (255, 215, 0)

# Shared Data
SQUARE_COLORS = [
    (255, 100, 100),
    (100, 255, 150),
    (100, 150, 255),
    (255, 255, 100),
    (255, 150, 255),
    (100, 255, 255),
    (255, 180, 100),
    (200, 100, 255),
    (100, 255, 200),
    (255, 100, 200),
]
STORE_SYMBOLS = ["Q", "A", "B", "C", "D", "E", "F", "G", "H", "I"]
ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"

DIFFICULTY_MAP = {
    "Imbecillus": ("Easy", 7),
    "Mediocris": ("Medium", 5),
    "Altus": ("Hard", 3),
}


class GameState(Enum):
    MENU = auto()
    TRANSITION_TO_PLAY = auto()
    PLAYING = auto()
    PAUSE = auto()
    STORE = auto()
    INVENTORY = auto()
    ROUND_OVER = auto()
