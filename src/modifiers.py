"""
modifiers.py
~~~~~~~~~~~~
Defines the shop modifier system and inventory logic for altering
gameplay parameters (e.g., multipliers, guess limits, letter unmasking).
"""

import random
from typing import Callable, Any


class Modifier:
    """
    Represents a purchasable store item that alters gameplay.
    Contains its own logic.
    """

    def __init__(
        self,
        id: str,
        name: str,
        cost: int,
        description: str,
        effect_func: Callable[[Any], list] = None,
    ):
        self.id = id
        self.name = name
        self.cost = cost
        self.description = description
        self._effect_func = effect_func

    def apply(self, game_round) -> list:
        """Applies the modifier's effect and returns characters to be guessed."""
        if self.id in game_round.active_modifiers:
            return []

        game_round.active_modifiers.add(self.id)

        chars_to_guess = []
        if self._effect_func:
            res = self._effect_func(game_round)
            if res:
                chars_to_guess = res

        return chars_to_guess


# --- Effect Logic Functions ---


def _apply_vowels(r):
    return ["A", "E", "I", "O", "U"]


def _apply_double_points(r):
    r.score_multiplier *= 2
    return []


def _apply_first_last(r):
    alnum_chars = [c.upper() for c in r.clue.answer if c.isalnum()]
    if alnum_chars:
        return [alnum_chars[0], alnum_chars[-1]]
    return []


def _apply_random(r, count: int):
    unrevealed = list(
        set(
            [
                c.upper()
                for c in r.clue.answer
                if c.isalnum() and c.upper() not in r.guessed_letters
            ]
        )
    )
    if unrevealed:
        return random.sample(unrevealed, min(count, len(unrevealed)))
    return []


def _apply_all_or_nothing(r):
    r.guesses_remaining = 1
    return []


def _apply_extra_guesses(r):
    r.guesses_remaining += 2
    return []


def _apply_rstln(r):
    return ["R", "S", "T", "L", "N"]


# --- Pygame-Ready Catalog ---
STORE_CATALOG = {
    "VOWELS": Modifier(
        "VOWELS", "Vowel Movement", 50, "Unmasks A, E, I, O, U.", _apply_vowels
    ),
    "DOUBLE_POINTS": Modifier(
        "DOUBLE_POINTS",
        "Inflation",
        100,
        "Earn 2x points if you win.",
        _apply_double_points,
    ),
    "FIRST_LAST": Modifier(
        "FIRST_LAST",
        "Bookends",
        75,
        "Reveals the first and last letters.",
        _apply_first_last,
    ),
    "RANDOM_1": Modifier(
        "RANDOM_1",
        "Lucky Dip",
        25,
        "Reveals 1 random letter.",
        lambda r: _apply_random(r, 1),
    ),
    "RANDOM_2": Modifier(
        "RANDOM_2",
        "Double Dip",
        45,
        "Reveals 2 random letters.",
        lambda r: _apply_random(r, 2),
    ),
    "RANDOM_3": Modifier(
        "RANDOM_3",
        "Hat Trick",
        60,
        "Reveals 3 random letters.",
        lambda r: _apply_random(r, 3),
    ),
    "REROLL": Modifier("REROLL", "Garbage Clue", 50, "Skips the current clue.", None),
    "ALL_OR_NOTHING": Modifier(
        "ALL_OR_NOTHING", "YOLO", 0, "Bet your entire score.", _apply_all_or_nothing
    ),
    "EXTRA_GUESSES": Modifier(
        "EXTRA_GUESSES",
        "Second Wind",
        40,
        "Gives you +2 extra guesses.",
        _apply_extra_guesses,
    ),
    "RSTLN": Modifier("RSTLN", "The Sajak", 85, "Reveals R, S, T, L, N.", _apply_rstln),
}
