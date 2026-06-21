"""
audio_manager.py
~~~~~~~~~~~~~~~~
Handles game sound effects, keystrokes, and modifier sounds cross-platform.
"""

import pygame
import random
from src.constants import get_resource_path  # Or src.utils


class AudioManager:
    def __init__(self):
        pygame.mixer.init()

        # 2. Use Path objects and the / operator to cleanly build paths
        assets_dir = get_resource_path("assets/sounds")
        # Keystrokes and menu clicks
        keystroke_dir = assets_dir / "key stroke sounds"
        self.keystrokes = [self._load(keystroke_dir / f"{i}.mp3") for i in range(1, 11)]

        menu_dir = assets_dir / "menu clicks"
        self.menu_clicks = [self._load(menu_dir / f"{i}.mp3") for i in range(1, 8)]

        # Standard SFX
        self.sfx = {
            "correct": self._load(assets_dir / "correct.mp3"),
            "wrong": self._load(assets_dir / "wrong.mp3"),
            "bounty": self._load(assets_dir / "hidden_letter.mp3"),
            "transition": self._load(assets_dir / "transition.mp3"),
            "date_spinner": self._load(assets_dir / "date_spinner.mp3"),
            "date_ding": self._load(assets_dir / "date_ding.mp3"),
            "hint": self._load(assets_dir / "hint_reveal.mp3"),
            "win": self._load(assets_dir / "win.mp3"),
        }

        # Modifier sounds
        mod_dir = assets_dir / "modifier sounds"
        self.mod_sounds = {
            "FIRST_LAST": self._load(mod_dir / "book_ends.mp3"),
            "RANDOM_2": self._load(mod_dir / "double_dip.mp3"),
            "REROLL": self._load(mod_dir / "garbage_clue.mp3"),
            "RANDOM_3": self._load(mod_dir / "hat_trick.mp3"),
            "DOUBLE_POINTS": self._load(mod_dir / "inflation.mp3"),
            "RANDOM_1": self._load(mod_dir / "lucky_dip.mp3"),
            "EXTRA_GUESSES": self._load(mod_dir / "second_wind.mp3"),
            "RSTLN": self._load(mod_dir / "the_sajak.mp3"),
            "VOWELS": self._load(mod_dir / "vowel_movement.mp3"),
            "ALL_OR_NOTHING": self._load(mod_dir / "yolo.mp3"),
        }

    def _load(self, path):
        try:
            # pygame.mixer.Sound accepts Path objects directly!
            return pygame.mixer.Sound(path)
        except Exception as e:
            print(f"Warning: Could not load sound {path}: {e}")
            return None

    def play(self, sound_key, category="sfx", loops=0, stop_all=False):
        if stop_all:
            pygame.mixer.stop()

        snd = None
        if category == "sfx":
            snd = self.sfx.get(sound_key)
        elif category == "mod":
            snd = self.mod_sounds.get(sound_key)
        elif category == "keystroke" and any(self.keystrokes):
            snd = random.choice([s for s in self.keystrokes if s])
        elif category == "menu" and any(self.menu_clicks):
            snd = random.choice([s for s in self.menu_clicks if s])

        if snd:
            snd.play(loops=loops)

    def stop(self, sound_key):
        snd = self.sfx.get(sound_key)
        if snd:
            snd.stop()


# Instantiate a global audio manager to be imported where needed
audio = AudioManager()
