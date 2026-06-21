"""
loader.py
~~~~~~~~~
Parses and loads CSV trivia datasets into structures, managing categories
and filtering logic for gameplay.
"""

import csv
import random
import re
from pathlib import Path
from src.constants import get_resource_path

_DATA_DIR = get_resource_path("assets/datasets")

# Dynamic cross-platform dataset pathing
DATA_CATEGORIES = {
    "1": ("Movies", _DATA_DIR / "movies.csv"),
    "2": ("TV", _DATA_DIR / "TV.csv"),
    "3": ("Music", _DATA_DIR / "music.csv"),
    "4": ("Games", _DATA_DIR / "games.csv"),
}


class TriviaClue:
    """
    Represents a single trivia clue, including its answer, hint, category,
    and methods for display and validation.
    """

    def __init__(self, data_row: dict, category: str):
        self.answer = data_row.get("Answer", "").strip().upper()
        self.hint_text = data_row.get("Hint", "").strip()
        self.release_date = data_row.get("Date", "").strip()
        self.category = category.upper()

        # Safely extract a 4-digit year for filtering
        year_match = re.search(r"\d{4}", self.release_date)
        self.year = int(year_match.group()) if year_match else None

        # Base value: 10 points per letter (ignoring spaces)
        self.base_value = len(self.answer.replace(" ", "")) * 10

    def get_masked_answer(self, guessed_letters: set) -> str:
        """
        Returns the answer with letters/digits replaced by underscores,
        unless they are in the guessed_letters set.
        """
        masked_chars = []
        for char in self.answer:
            if char.isalnum():
                if char in guessed_letters:
                    masked_chars.append(char)
                else:
                    masked_chars.append("_")
            else:
                masked_chars.append(char)
        return "".join(masked_chars)

    def get_formatted_display(self, guessed_letters: set) -> str:
        """
        Returns a formatted string for displaying the clue, using
        category-specific nomenclature for hints and answers.
        """
        masked_ans = self.get_masked_answer(guessed_letters)

        # Determine nomenclature based on category
        cat = self.category.upper()
        if cat == "MOVIES":
            hint_label = "Tagline"
            answer_label = "Movie"
        elif cat == "MUSIC":
            hint_label = "Song"
            answer_label = "Artist"
        elif cat == "TV":
            hint_label = "Synopsis"
            answer_label = "TV"
        elif cat == "GAMES":
            hint_label = "Synopsis"
            answer_label = "Game"
        else:
            hint_label = "Hint"
            answer_label = "Answer"

        return (
            f"\n=== {self.category} ({self.release_date}) ===\n"
            f"{hint_label}: {self.hint_text}\n"
            f"{answer_label}: {masked_ans}"
        )

    def validate_guess(self, guess: str) -> bool:
        """
        Checks if the player's guess matches the answer (case-insensitive, trimmed).
        """
        return guess.strip().upper() == self.answer


class TriviaDatabase:
    """
    Manages loading and providing trivia clues from various CSV files.
    """

    def __init__(self, file_mapping: dict[str, Path]):
        self.file_mapping = file_mapping
        self.categories: dict[str, list[TriviaClue]] = {}
        self.load_all_csvs()

    def load_all_csvs(self):
        """
        Loads all CSV files specified in the file_mapping into memory.
        """
        for category_name, file_path in self.file_mapping.items():
            self.categories[category_name.upper()] = []

            # Using pathlib's .exists() method instead of os.path.exists
            if not file_path.exists():
                print(
                    f"[!] Warning: Could not find '{file_path}'. Skipping category: {category_name}."
                )
                continue

            records = []
            try:
                with open(file_path, mode="r", encoding="utf-8") as file:
                    reader = csv.DictReader(file)
                    for row in reader:
                        records.append(row)
            except Exception as e:
                print(
                    f"[!] Error reading '{file_path}': {e}. Skipping category: {category_name}."
                )
                continue

            if not records:
                print(
                    f"[!] Warning: '{file_path}' is empty or missing headers. Skipping category: {category_name}."
                )
                continue

            for row in records:
                clue = TriviaClue(row, category_name)
                self.categories[category_name.upper()].append(clue)

    def get_random_clue(
        self,
        category: str | None = None,
        min_year: int | None = None,
        max_year: int | None = None,
    ) -> TriviaClue | None:
        """
        Returns a random TriviaClue, optionally constrained by category and release year.
        """
        if not category:
            available_categories = [
                cat for cat, clues in self.categories.items() if clues
            ]
            if not available_categories:
                return None
            category = random.choice(available_categories)
        else:
            category = category.upper()

        if category in self.categories and self.categories[category]:
            valid_clues = self.categories[category]

            if min_year is not None:
                valid_clues = [
                    c for c in valid_clues if c.year is not None and c.year >= min_year
                ]
            if max_year is not None:
                valid_clues = [
                    c for c in valid_clues if c.year is not None and c.year <= max_year
                ]

            if not valid_clues:
                return None

            return random.choice(valid_clues)

        return None
