"""
state.py
~~~~~~~~
Manages the core state machine for game sessions. Handles individual round
tracking, win/loss evaluation, scoring multipliers, difficulty scaling,
and user inventory/shop operations.
"""

import random
from src.loader import TriviaDatabase, TriviaClue
from src.modifiers import STORE_CATALOG


class Round:
    def __init__(self, clue: TriviaClue, guesses_allowed: int):
        self.clue = clue
        self.guesses_remaining = guesses_allowed
        self.guessed_letters = set()

        for char in str(self.clue.answer):
            if char.isdigit():
                self.guessed_letters.add(char)

        self.is_won = False
        self.active_modifiers = set()
        self.score_multiplier = 1.0

        self._check_win_condition()

        self.consecutive_corrects = 0
        self.consecutive_wrongs = 0
        self.alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"

        # --- FIX: Bounty letter must come from the answer ---
        answer_letters = [c for c in str(self.clue.answer).upper() if c.isalpha()]
        if answer_letters:
            self.bounty_letter = random.choice(answer_letters)
        else:
            self.bounty_letter = random.choice(self.alphabet)

        self.letter_freq_mult = {
            "E": 0.5,
            "T": 0.5,
            "A": 0.5,
            "O": 0.5,
            "I": 0.5,
            "N": 0.5,
            "S": 0.5,
            "H": 0.5,
            "R": 0.5,
            "D": 1.0,
            "L": 1.0,
            "C": 1.0,
            "U": 1.0,
            "M": 1.0,
            "W": 1.0,
            "F": 1.0,
            "G": 1.0,
            "Y": 1.0,
            "P": 1.0,
            "B": 1.0,
            "V": 1.5,
            "K": 1.5,
            "J": 1.5,
            "X": 1.5,
            "Q": 1.5,
            "Z": 1.5,
        }

    def process_guess(
        self, guess: str, diff_mult: float, is_freebie: bool = False
    ) -> dict:
        char = guess.upper()
        if char in self.guessed_letters:
            return {"status": "ignored", "char": char}

        self.guessed_letters.add(char)
        answer_upper = self.clue.answer.upper()

        result = {
            "status": "",
            "char": char,
            "points": 0.0,
            "is_bounty": False,
            "heat": 0,
        }

        if char in answer_upper:
            self.consecutive_corrects += 1
            self.consecutive_wrongs = 0

            base_val = 15.0
            freq_mult = self.letter_freq_mult.get(char, 1.0)
            heat_mult = 1.0 + (self.consecutive_corrects * 0.2)
            letter_score = base_val * freq_mult * diff_mult * heat_mult

            if char == self.bounty_letter:
                letter_score *= 2.0
                result["is_bounty"] = True

            result["status"] = "correct"
            result["points"] = letter_score
            result["heat"] = self.consecutive_corrects

            self._check_win_condition()
        else:
            self.consecutive_wrongs += 1
            self.consecutive_corrects = 0

            if not is_freebie:
                self.guesses_remaining -= 1

            base_penalty = 5.0
            penalty_amount = base_penalty * (1.5 ** (self.consecutive_wrongs - 1))

            result["status"] = "incorrect"
            result["points"] = -penalty_amount

        return result

    def _check_win_condition(self):
        self.is_won = all(
            c in self.guessed_letters or not c.isalnum()
            for c in self.clue.answer.upper()
        )

    def get_base_score(self) -> int:
        base = self.clue.base_value if self.is_won else 0
        return int(base * self.score_multiplier)

    def is_completed(self) -> bool:
        return self.is_won or self.guesses_remaining <= 0


class GameManager:
    def __init__(self):
        self.total_score = 0.0
        self.rounds_played = 0
        self.inventory = {mod_id: 0 for mod_id in STORE_CATALOG.keys()}

        self.difficulty = "Medium"
        self.guesses_allowed = 5
        self.min_year = 1970
        self.max_year = 2026

        self.db = None
        self.current_category = None
        self.current_round = None

    def load_databases(self, file_mapping: dict):
        assert file_mapping, "File mapping cannot be empty."
        self.db = TriviaDatabase(file_mapping)
        return len(self.db.categories) > 0

    def start_round(self, carry_over_modifiers: set = None) -> bool:
        assert self.db is not None, "Cannot start round: Database not loaded."

        clue = self.db.get_random_clue(
            category=None, min_year=self.min_year, max_year=self.max_year
        )
        if not clue:
            return False

        self.current_category = clue.category
        self.current_round = Round(clue, guesses_allowed=self.guesses_allowed)
        self.rounds_played += 1

        if carry_over_modifiers:
            for mod_id in carry_over_modifiers:
                mod = STORE_CATALOG.get(mod_id)
                if mod:
                    mod.apply(self.current_round)

        return True

    def submit_guess(self, guess: str, is_freebie: bool = False) -> dict:
        assert self.current_round is not None, "Cannot submit guess: No active round."
        assert len(guess) == 1, "Guess must be a single character."

        if not guess.isalpha():
            return {
                "status": "ignored",
                "char": guess,
                "points": 0.0,
                "is_bounty": False,
                "heat": 0,
            }

        if self.current_round.is_completed():
            return {"status": "completed"}

        diff_mult = {"Hard": 0.5, "Medium": 1.0, "Easy": 1.5}.get(self.difficulty, 1.0)
        result = self.current_round.process_guess(guess, diff_mult, is_freebie)

        if result["status"] == "correct":
            self.total_score += result["points"]
        elif result["status"] == "incorrect":
            self.total_score = max(0.0, self.total_score + result["points"])

        return result

    def buy_item(self, mod_id: str) -> bool:
        mod = STORE_CATALOG.get(mod_id)
        if mod and self.total_score >= mod.cost:
            self.total_score -= mod.cost
            self.inventory[mod_id] += 1
            return True
        return False

    def activate_item(self, mod_id: str) -> dict:
        if self.inventory.get(mod_id, 0) <= 0:
            return {"success": False, "message": "Not enough items in inventory."}
        if not self.current_round:
            return {"success": False, "message": "No active round."}

        if mod_id == "REROLL":
            self.inventory[mod_id] -= 1
            active_mods = self.current_round.active_modifiers.copy()
            active_mods.discard("REROLL")
            success = self.start_round(carry_over_modifiers=active_mods)
            if not success:
                self.inventory[mod_id] += 1
                return {"success": False, "message": "No more clues in this era!"}
            return {"success": True, "message": "Rerolled clue!"}

        mod = STORE_CATALOG.get(mod_id)
        if mod:
            if mod_id in self.current_round.active_modifiers:
                return {
                    "success": False,
                    "message": "Already activated.",
                    "results": [],
                }

            self.inventory[mod_id] -= 1
            chars_to_guess = mod.apply(self.current_round)

            results = []
            for char in chars_to_guess:
                res = self.submit_guess(char, is_freebie=True)
                results.append(res)

            return {
                "success": True,
                "message": f"Activated {mod.name}!",
                "results": results,
            }

        # --- FIX: Removed dead unreachable code block here ---
        return {"success": False, "message": "Invalid item."}

    def process_round_end(self) -> dict:
        assert self.current_round is not None, "Cannot process end: No active round."

        is_all_in = "ALL_OR_NOTHING" in self.current_round.active_modifiers
        result = {
            "won": self.current_round.is_won,
            "answer": self.current_round.clue.answer,
            "points_earned": 0,
            "is_all_in": is_all_in,
        }

        if self.current_round.is_won:
            points = (
                self.total_score if is_all_in else self.current_round.get_base_score()
            )
            result["points_earned"] = points
            self.total_score += points
        else:
            if is_all_in:
                self.total_score = 0

        return result
