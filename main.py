#!/usr/bin/env python3
# =============================================================================
# Project: Syllable Syndicate
# Description: Main application entry point and game loop orchestrator.
#              Manages top-level application states (Menu, Playing, Store, etc.),
#              handles global event routing, and coordinates rendering between
#              various UI overlays and the underlying game logic manager.
# Author: Scott Steely
#
# MIT License
#
# Copyright (c) 2026 Scott Steely
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
# =============================================================================

import pygame
import math
import random

# Internal Modules
from src.state import GameManager  # Core logic, inventory, and scoring
from src.loader import DATA_CATEGORIES  # File ingestion and parsing
from src.starfield_bg import Starfield  # Global background rendering
from src.ui_overlay import (
    RightUIOverlay,
    LeftUIOverlay,
)  # HUD and gameplay interaction zones
from src.store_ui import VisualStore  # Dedicated store interface
from src.dates import DateSpinner  # Visual components
from src.effects import DecryptReveal, GoldMatrixTransition
from src.audio_manager import audio  # Centralized SFX handler
from src.constants import (
    WHITE,
    BLACK,
    GRAY,
    GREEN,
    RED,
    GOLD,
    GameState,
    DIFFICULTY_MAP,
)
from src.font_manager import FontManager  # Cached font loading
from src.text_utils import wrap_text, truncate_text
from src.ui_elements import CategoryCheckbox
from src.modifiers import STORE_CATALOG

pygame.init()


class Game:
    def __init__(self):
        # Global Pygame setup
        self.width, self.height = 1920, 1080

        # Dynamic Screen Resize mechanics
        self.window_width, self.window_height = self.width, self.height
        self.screen = pygame.display.set_mode(
            (self.window_width, self.window_height), pygame.RESIZABLE
        )
        self.virtual_screen = pygame.Surface((self.width, self.height))
        pygame.display.set_caption("Syllable Syndicate - A Word Game.")
        self.clock = pygame.time.Clock()

        # Instantiate primary logic manager (headless) and visual overlays (stateful)
        self.manager = GameManager()
        self.background = Starfield(self.width, self.height, speed=1.0)
        self.visual_store = VisualStore(self.width, self.height, self.manager)
        self.right_ui = RightUIOverlay(self.width, self.height, self.manager)
        self.left_ui = LeftUIOverlay(self.width, self.height, self.manager)
        self.gold_transition = GoldMatrixTransition(self.width, self.height)

        # High-level state tracking
        self.state = GameState.MENU
        self.round_result = {}
        self.status_message = ""
        self.status_timer = 0.0
        self.click_zones = {}

        # Round-specific visual trackers
        self.date_spinner = None
        self.hint_reveal = None
        self.ding_played = False
        self.post_ding_timer = 0.0
        self.cheat_buffer = ""
        self.current_hint_lines = 0

        # Menu and Configuration Defaults
        self.current_difficulty = "Mediocris"
        self.guesses_allowed = 5
        self.diff_colors = {"Imbecillus": GREEN, "Mediocris": GOLD, "Altus": RED}
        self.selected_categories = set(DATA_CATEGORIES.keys())

        # Dynamically build category select boxes based on loader data
        self.category_boxes = {}
        cb_y = 570
        for key, (name, _) in DATA_CATEGORIES.items():
            self.category_boxes[key] = CategoryCheckbox(
                self.width // 2 - 120, cb_y + 15, 12, GOLD
            )
            cb_y += 40

        self.transition_progress = 0.0
        self.menu_snapshot = None

        # Main Menu Date Slider Configuration
        self.SLIDER_MIN_VAL, self.SLIDER_MAX_VAL = 1970, 2026
        self.current_min_year, self.current_max_year = 1970, 2026
        self.slider_x, self.slider_w, self.slider_y = self.width // 2 - 250, 500, 440
        self.dragging_min, self.dragging_max = False, False

        # Pre-load shared fonts
        self.font_large = FontManager.get("capitolcity", 48)
        self.font_med = FontManager.get(None, 32)
        self.font_small = FontManager.get(None, 24)
        self.hint_font = FontManager.get("typewriter", 32)

    def get_virtual_mouse_pos(self, mx, my):
        """Translates real window mouse coordinates to virtual surface coordinates."""
        scale_x = self.window_width / self.width
        scale_y = self.window_height / self.height
        scale = min(scale_x, scale_y)

        scaled_w = int(self.width * scale)
        scaled_h = int(self.height * scale)

        offset_x = (self.window_width - scaled_w) // 2
        offset_y = (self.window_height - scaled_h) // 2

        # Translate and scale the coordinates
        virtual_x = (mx - offset_x) / scale
        virtual_y = (my - offset_y) / scale

        return virtual_x, virtual_y

    def set_status(self, msg, duration_seconds=2.0):
        """Displays temporary notification text at the bottom of the screen."""
        self.status_message = msg
        self.status_timer = duration_seconds

    def play_guess_sound(self, result_dict):
        """Routes audio based on logical outcomes from the GameManager."""
        if result_dict.get("is_bounty"):
            audio.play("bounty")
        elif result_dict.get("status") == "correct":
            audio.play("correct")
        elif result_dict.get("status") == "incorrect":
            audio.play("wrong")

    def draw_text(
        self, surface, text, x, y, font, color=WHITE, action_id=None, center=False
    ):
        """Helper to render text and optionally register its bounding box as a click zone."""
        img = font.render(str(text), True, color)
        actual_x = self.width // 2 - img.get_width() // 2 if center else x
        rect = surface.blit(img, (actual_x, y))
        if action_id is not None:
            self.click_zones[action_id] = rect.inflate(10, 10)

    def draw_wrapped_text(
        self, surface, text, y_start, font, color=WHITE, max_width=1200, center=True
    ):
        """Handles multiline text blocks for long hints or multi-word answers."""
        lines = wrap_text(text, font, max_width)
        current_y, line_height = y_start, font.get_linesize()
        for line in lines:
            img = font.render(line, True, color)
            x = (
                self.width // 2 - img.get_width() // 2
                if center
                else (self.width - max_width) // 2
            )
            surface.blit(img, (x, current_y))
            current_y += line_height
        return current_y

    def _check_round_complete(self):
        """Synchronizes visual state when the logic manager signals a round end."""
        if self.manager.current_round and self.manager.current_round.is_completed():
            self.round_result = self.manager.process_round_end()
            self.state = GameState.ROUND_OVER
            audio.stop("hint")
            if self.round_result.get("won"):
                audio.play("win")
                self.gold_transition.start(self.screen, duration_seconds=2.0)

    def run(self):
        """Primary application loop."""
        running = True
        while running:
            dt = self.clock.tick(60) / 1000.0

            # Clear and draw to VIRTUAL SCREEN
            self.virtual_screen.fill(BLACK)
            self.background.draw(self.virtual_screen)

            # Snapshot click zones from the previous frame
            current_click_zones = self.click_zones.copy()
            self.click_zones.clear()

            # Get real mouse pos and translate to VIRTUAL pos
            raw_mx, raw_my = pygame.mouse.get_pos()
            mx, my = self.get_virtual_mouse_pos(raw_mx, raw_my)

            running = self._handle_events(dt, current_click_zones, mx, my)
            if not running:
                break

            self._update(dt, mx, my)
            self._draw(dt, mx, my)

            # Scale virtual screen to fit the actual window while keeping aspect ratio
            scale = min(
                self.window_width / self.width, self.window_height / self.height
            )
            scaled_w = int(self.width * scale)
            scaled_h = int(self.height * scale)

            scaled_surf = pygame.transform.scale(
                self.virtual_screen, (scaled_w, scaled_h)
            )

            offset_x = (self.window_width - scaled_w) // 2
            offset_y = (self.window_height - scaled_h) // 2

            # Draw the scaled surface onto the actual screen (with letterbox background)
            self.screen.fill(BLACK)  # Fills the "letterbox/pillarbox" bars
            self.screen.blit(scaled_surf, (offset_x, offset_y))

            pygame.display.flip()

    def _handle_events(self, dt, current_click_zones, mx, my):
        """Global event router. Branches logic based on current GameState."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False

            if event.type == pygame.VIDEORESIZE:
                # Guard clause to prevent the Windows infinite resize loop
                if event.w != self.window_width or event.h != self.window_height:
                    self.window_width, self.window_height = event.w, event.h
                    self.screen = pygame.display.set_mode(
                        (self.window_width, self.window_height), pygame.RESIZABLE
                    )
                continue

            # Global ambient audio hooks
            if (
                event.type == pygame.KEYDOWN
                and event.unicode
                and event.unicode.isalpha()
            ):
                audio.play(None, category="keystroke")

            if (
                self.state
                in [
                    GameState.MENU,
                    GameState.PAUSE,
                    GameState.STORE,
                    GameState.INVENTORY,
                ]
                and event.type == pygame.MOUSEBUTTONDOWN
                and event.button == 1
            ):
                audio.play(None, category="menu")

            # --- MAIN MENU SLIDER LOGIC ---
            if self.state == GameState.MENU:
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    min_pos_x = (
                        self.slider_x
                        + (
                            (self.current_min_year - self.SLIDER_MIN_VAL)
                            / (self.SLIDER_MAX_VAL - self.SLIDER_MIN_VAL)
                        )
                        * self.slider_w
                    )
                    max_pos_x = (
                        self.slider_x
                        + (
                            (self.current_max_year - self.SLIDER_MIN_VAL)
                            / (self.SLIDER_MAX_VAL - self.SLIDER_MIN_VAL)
                        )
                        * self.slider_w
                    )
                    if math.hypot(mx - min_pos_x, my - self.slider_y) < 20:
                        self.dragging_min = True
                    elif math.hypot(mx - max_pos_x, my - self.slider_y) < 20:
                        self.dragging_max = True
                elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                    self.dragging_min, self.dragging_max = False, False
                elif event.type == pygame.MOUSEMOTION:
                    if self.dragging_min:
                        ratio = max(0, min((mx - self.slider_x) / self.slider_w, 1))
                        val = int(
                            self.SLIDER_MIN_VAL
                            + ratio * (self.SLIDER_MAX_VAL - self.SLIDER_MIN_VAL)
                        )
                        self.current_min_year = min(val, self.current_max_year - 1)
                    elif self.dragging_max:
                        ratio = max(0, min((mx - self.slider_x) / self.slider_w, 1))
                        val = int(
                            self.SLIDER_MIN_VAL
                            + ratio * (self.SLIDER_MAX_VAL - self.SLIDER_MIN_VAL)
                        )
                        self.current_max_year = max(val, self.current_min_year + 1)

            # Resolve click zones mapped during the draw phase
            clicked_action = None
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                for action_id, rect in current_click_zones.items():
                    if rect.collidepoint(mx, my):
                        clicked_action = action_id
                        break

            # --- STATE: MENU ---
            if self.state == GameState.MENU:
                if (
                    event.type == pygame.KEYDOWN and event.unicode.upper() == "Q"
                ) or clicked_action == "QUIT":
                    return False
                elif (
                    event.type == pygame.KEYDOWN and event.unicode.upper() == "R"
                ) or clicked_action == "RESET_GAME":
                    self.manager = GameManager()
                    self.visual_store = VisualStore(
                        self.width, self.height, self.manager
                    )
                    self.right_ui = RightUIOverlay(
                        self.width, self.height, self.manager
                    )
                    self.left_ui = LeftUIOverlay(self.width, self.height, self.manager)
                    self.set_status("Game Progress Reset!")
                elif clicked_action == "DIFF_IMBECILLUS":
                    self.current_difficulty, self.guesses_allowed = "Imbecillus", 7
                elif clicked_action == "DIFF_MEDIOCRIS":
                    self.current_difficulty, self.guesses_allowed = "Mediocris", 5
                elif clicked_action == "DIFF_ALTUS":
                    self.current_difficulty, self.guesses_allowed = "Altus", 3
                elif clicked_action and clicked_action.startswith("CAT_"):
                    cat_key = clicked_action.split("_")[1]
                    box = self.category_boxes[cat_key]
                    if cat_key in self.selected_categories:
                        self.selected_categories.remove(cat_key)
                        box.checked = False
                    else:
                        self.selected_categories.add(cat_key)
                        box.checked = True
                    box.trigger_effect(random.randint(0, 9))
                elif clicked_action == "START_GAME" or (
                    event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN
                ):
                    # Ensure parameters are passed down to logic manager before game start
                    if not self.selected_categories:
                        self.set_status("Please select at least one category!")
                    else:
                        self.manager.difficulty = DIFFICULTY_MAP[
                            self.current_difficulty
                        ][0]
                        self.manager.guesses_allowed = self.guesses_allowed
                        self.manager.min_year, self.manager.max_year = (
                            self.current_min_year,
                            self.current_max_year,
                        )
                        selected_mapping = {
                            DATA_CATEGORIES[k][0]: DATA_CATEGORIES[k][1]
                            for k in self.selected_categories
                        }
                        if self.manager.load_databases(selected_mapping):
                            if (
                                self.manager.start_round()
                                and self.manager.current_round
                            ):
                                self.menu_snapshot = self.screen.copy()
                                self.state = GameState.TRANSITION_TO_PLAY
                                self.transition_progress = 0.0
                                audio.play("transition")
                                self.date_spinner = None
                                self.hint_reveal = None
                            else:
                                self.set_status(
                                    "No clues available in that date range!"
                                )
                        else:
                            self.set_status("Failed to load databases.")

            # --- STATE: PLAYING ---
            elif self.state == GameState.PLAYING:
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    # Delegate clicks to specific UI overlay modules based on screen position
                    if mx >= self.width - 400:
                        clicked_mod_id, res_dict = self.right_ui.handle_click(mx, my)
                        if clicked_mod_id and isinstance(res_dict, dict):
                            self.set_status(res_dict.get("message", ""))
                            if res_dict.get("success"):
                                audio.play(
                                    clicked_mod_id, category="mod", stop_all=True
                                )
                                if "results" in res_dict:
                                    for guess_res in res_dict["results"]:
                                        self.left_ui.trigger_guess_fx(guess_res)
                                self._check_round_complete()
                    elif mx <= 400:
                        clicked_item = self.left_ui.handle_click(mx, my)
                        if clicked_item == "OPEN_STORE":
                            audio.play(None, category="menu")
                            self.state = GameState.STORE
                        elif clicked_item:
                            result_dict = self.manager.submit_guess(clicked_item)
                            self.left_ui.trigger_guess_fx(result_dict)
                            self.play_guess_sound(result_dict)
                            self._check_round_complete()

                if (
                    event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE
                ) or clicked_action == "PAUSE":
                    self.state = GameState.PAUSE
                    audio.stop("hint")
                elif event.type == pygame.KEYDOWN and (
                    event.unicode.isalpha() or event.unicode.isdigit()
                ):
                    # Cheat code parsing
                    self.cheat_buffer += event.unicode.lower()
                    if self.cheat_buffer.endswith("money"):
                        self.manager.total_score += 200
                        self.set_status("Secret Found! +$200k Points")
                        self.cheat_buffer = ""
                    if len(self.cheat_buffer) > 10:
                        self.cheat_buffer = self.cheat_buffer[-10:]

                    # Standard keyboard guessing
                    if event.unicode.isalpha():
                        result_dict = self.manager.submit_guess(event.unicode)
                        self.left_ui.trigger_guess_fx(result_dict)
                        self.play_guess_sound(result_dict)
                        self._check_round_complete()
                    elif event.unicode.isdigit():
                        self.set_status("Letters only, please!")

            # --- STATE: PAUSE ---
            elif self.state == GameState.PAUSE:
                if (
                    event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE
                ) or clicked_action == "RESUME":
                    self.state = GameState.PLAYING
                    if self.hint_reveal and not self.hint_reveal.finished:
                        audio.play("hint", loops=-1)
                elif (
                    event.type == pygame.KEYDOWN and event.key == pygame.K_1
                ) or clicked_action == "STORE":
                    self.state = GameState.STORE
                elif (
                    event.type == pygame.KEYDOWN and event.key == pygame.K_2
                ) or clicked_action == "INVENTORY":
                    self.state = GameState.INVENTORY
                elif (
                    event.type == pygame.KEYDOWN and event.unicode.upper() == "Q"
                ) or clicked_action == "QUIT_TO_MENU":
                    self.state = GameState.MENU

            # --- STATE: STORE ---
            elif self.state == GameState.STORE:
                # Delegate store logic and rendering entirely to visual_store
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        self.state = GameState.PAUSE
                    elif event.unicode.isalpha():
                        success, item_name, mod_id = self.visual_store.handle_keydown(
                            event.unicode
                        )
                        if item_name:
                            self.set_status(
                                f"Bought {item_name}!"
                                if success
                                else "Not enough funds!"
                            )
                            if success:
                                audio.play(mod_id, category="mod", stop_all=True)
                            else:
                                audio.play("wrong")
                elif clicked_action == "BACK":
                    self.state = GameState.PAUSE
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    success, item_name, mod_id = self.visual_store.handle_click(mx, my)
                    if item_name:
                        self.set_status(
                            f"Bought {item_name}!" if success else "Not enough funds!"
                        )
                        if success:
                            audio.play(mod_id, category="mod", stop_all=True)
                        else:
                            audio.play("wrong")

            # --- STATE: INVENTORY ---
            elif self.state == GameState.INVENTORY:
                if (
                    event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE
                ) or clicked_action == "BACK":
                    self.state = GameState.PAUSE
                else:
                    owned = [k for k, v in self.manager.inventory.items() if v > 0]
                    idx_map = {str(i + 1): k for i, k in enumerate(owned)}
                    chosen_key = None
                    if clicked_action and clicked_action.startswith("USE_"):
                        chosen_key = clicked_action.split("_", 1)[1]
                    elif event.type == pygame.KEYDOWN and event.unicode in idx_map:
                        chosen_key = idx_map[event.unicode]
                    if chosen_key:
                        res = self.manager.activate_item(chosen_key)
                        self.set_status(res["message"])
                        if res["success"]:
                            audio.play(chosen_key, category="mod", stop_all=True)
                            # Special case: Reroll overrides current game flow
                            if chosen_key == "REROLL" and self.manager.current_round:
                                self.state = GameState.PLAYING
                                self.date_spinner = DateSpinner(
                                    self.manager.current_round.clue.release_date
                                )
                                audio.play("date_spinner")
                                self.hint_reveal = None
                                self.ding_played = False
                                self.post_ding_timer = 0.0

            # --- STATE: ROUND OVER ---
            elif self.state == GameState.ROUND_OVER:
                if (
                    event.type == pygame.KEYDOWN and event.key == pygame.K_1
                ) or clicked_action == "PLAY_AGAIN":
                    if self.manager.start_round() and self.manager.current_round:
                        self.state = GameState.PLAYING
                        self.date_spinner = DateSpinner(
                            self.manager.current_round.clue.release_date
                        )
                        audio.play("date_spinner")
                        self.hint_reveal = None
                        self.ding_played = False
                        self.post_ding_timer = 0.0
                    else:
                        self.state = GameState.MENU
                elif (
                    event.type == pygame.KEYDOWN and event.key == pygame.K_2
                ) or clicked_action == "MAIN_MENU":
                    self.state = GameState.MENU

        return True

    def _update(self, dt, mx, my):
        """Advances active logic/animations for subsystems."""
        self.left_ui.update(dt)
        self.right_ui.update(dt)
        self.gold_transition.update()

        if self.status_timer > 0:
            self.status_timer -= dt

    def _draw(self, dt, mx, my):
        """Delegates draw commands depending on the current active view."""
        if self.state == GameState.MENU:
            self.draw_text(
                self.virtual_screen,
                "SYLLABLE SYNDICATE",
                0,
                100,
                self.font_large,
                center=True,
            )
            self.draw_text(
                self.virtual_screen,
                f"Bankroll: ${int(self.manager.total_score * 1000):,}k",
                0,
                170,
                self.font_med,
                GREEN,
                center=True,
            )
            self.draw_text(
                self.virtual_screen, "DIFFICULTY:", 0, 240, self.font_med, center=True
            )

            diff_y = 290
            for i, diff in enumerate(["Imbecillus", "Mediocris", "Altus"]):
                bx = (self.width // 2) + ((i - 1) * 200)
                color = (
                    self.diff_colors[diff] if diff == self.current_difficulty else GRAY
                )
                btn_rect = pygame.Rect(bx - 80, diff_y - 20, 160, 40)
                pygame.draw.rect(
                    self.virtual_screen, (30, 30, 35), btn_rect, border_radius=5
                )
                pygame.draw.rect(
                    self.virtual_screen, color, btn_rect, width=2, border_radius=5
                )
                self.draw_text(
                    self.virtual_screen,
                    diff,
                    bx - self.font_small.size(diff)[0] // 2,
                    diff_y - 10,
                    self.font_small,
                    color,
                    action_id=f"DIFF_{diff.upper()}",
                )

            self.draw_text(
                self.virtual_screen,
                f"{self.current_min_year} - {self.current_max_year}",
                0,
                370,
                self.font_large,
                GOLD,
                center=True,
            )

            min_pos_x = (
                self.slider_x
                + (
                    (self.current_min_year - self.SLIDER_MIN_VAL)
                    / (self.SLIDER_MAX_VAL - self.SLIDER_MIN_VAL)
                )
                * self.slider_w
            )
            max_pos_x = (
                self.slider_x
                + (
                    (self.current_max_year - self.SLIDER_MIN_VAL)
                    / (self.SLIDER_MAX_VAL - self.SLIDER_MIN_VAL)
                )
                * self.slider_w
            )
            pygame.draw.rect(
                self.virtual_screen,
                (40, 40, 50),
                (self.slider_x, self.slider_y - 4, self.slider_w, 8),
                border_radius=4,
            )
            if (max_pos_x - min_pos_x) > 0:
                pygame.draw.rect(
                    self.virtual_screen,
                    GREEN,
                    (int(min_pos_x), self.slider_y - 4, int(max_pos_x - min_pos_x), 8),
                    border_radius=4,
                )

            for pos_x in [min_pos_x, max_pos_x]:
                handle_rect = pygame.Rect(int(pos_x) - 10, self.slider_y - 16, 20, 32)
                pygame.draw.rect(
                    self.virtual_screen, (200, 200, 210), handle_rect, border_radius=5
                )
                pygame.draw.rect(
                    self.virtual_screen,
                    (100, 100, 110),
                    handle_rect,
                    width=1,
                    border_radius=5,
                )
                pygame.draw.line(
                    self.virtual_screen,
                    (80, 80, 90),
                    (int(pos_x) - 3, self.slider_y - 6),
                    (int(pos_x) - 3, self.slider_y + 6),
                    2,
                )
                pygame.draw.line(
                    self.virtual_screen,
                    (80, 80, 90),
                    (int(pos_x) + 3, self.slider_y - 6),
                    (int(pos_x) + 3, self.slider_y + 6),
                    2,
                )

            self.draw_text(
                self.virtual_screen,
                "Select Categories:",
                0,
                510,
                self.font_med,
                center=True,
            )
            y_offset = 570
            for key, (name, _) in DATA_CATEGORIES.items():
                box = self.category_boxes[key]
                box.update(dt)
                box.draw(self.virtual_screen)
                self.draw_text(
                    self.virtual_screen,
                    name,
                    self.width // 2 - 90,
                    y_offset,
                    self.font_med,
                    WHITE,
                    action_id=f"CAT_{key}",
                )
                self.click_zones[f"CAT_{key}"] = pygame.Rect(
                    self.width // 2 - 140, y_offset, 250, 30
                )
                y_offset += 40

            y_offset += 20
            self.draw_text(
                self.virtual_screen,
                "START GAME [ENTER]",
                0,
                y_offset,
                self.font_large,
                GREEN,
                center=True,
                action_id="START_GAME",
            )
            self.draw_text(
                self.virtual_screen,
                "R. Reset Save Data",
                0,
                y_offset + 60,
                self.font_med,
                GOLD,
                center=True,
                action_id="RESET_GAME",
            )
            self.draw_text(
                self.virtual_screen,
                "Q. Quit Game",
                0,
                y_offset + 100,
                self.font_med,
                RED,
                center=True,
                action_id="QUIT",
            )

        elif self.state == GameState.TRANSITION_TO_PLAY:
            # Animation block: Slides the UI overlays in while fading the main menu
            self.transition_progress += dt * 0.2
            if self.transition_progress >= 1.0:
                self.transition_progress = 1.0
                self.state = GameState.PLAYING
                if self.manager.current_round:
                    self.date_spinner = DateSpinner(
                        self.manager.current_round.clue.release_date
                    )
                audio.play("date_spinner")
                self.ding_played = False
                self.post_ding_timer = 0.0

            t = self.transition_progress
            scaled_w, scaled_h = int(self.width * (1 - t)), int(self.height * (1 - t))
            if scaled_w > 0 and scaled_h > 0 and self.menu_snapshot is not None:
                scaled_menu = pygame.transform.smoothscale(
                    self.menu_snapshot, (scaled_w, scaled_h)
                )
                scaled_menu.set_alpha(int(255 * (1 - t)))
                self.virtual_screen.blit(
                    scaled_menu,
                    (self.width // 2 - scaled_w // 2, self.height // 2 - scaled_h // 2),
                )

            left_surf = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
            self.left_ui.draw(left_surf)
            self.virtual_screen.blit(left_surf, (0, -self.height * (1 - t)))

            right_surf = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
            self.right_ui.draw(right_surf)
            self.virtual_screen.blit(right_surf, (0, self.height * (1 - t)))

        elif self.state == GameState.PLAYING:
            r = self.manager.current_round
            if r:
                # Top header bar text
                self.draw_text(
                    self.virtual_screen,
                    f"Bankroll: ${int(self.manager.total_score * 1000):,} | Guesses Left: {r.guesses_remaining}",
                    0,
                    50,
                    self.font_med,
                    center=True,
                )
                self.draw_text(
                    self.virtual_screen,
                    "[ESC] Pause / Store / Inventory",
                    0,
                    90,
                    self.font_small,
                    GRAY,
                    action_id="PAUSE",
                    center=True,
                )

                # Center game area: Hint reveals and hidden word formatting
                center_y = self.height // 2 - 250
                if self.date_spinner:
                    self.date_spinner.update(dt)
                    self.date_spinner.draw(self.virtual_screen, center_y)

                if self.date_spinner and self.date_spinner.date_animation_complete:
                    if not self.ding_played:
                        audio.play("date_ding")
                        self.ding_played = True
                        self.post_ding_timer = 0.8

                    if self.post_ding_timer > 0:
                        self.post_ding_timer -= dt
                    else:
                        next_y = center_y + 150
                        if self.hint_reveal is None:
                            final_hint, hint_lines_count = truncate_text(
                                r.clue.hint_text,
                                self.hint_font,
                                max_width=1000,
                                max_lines=4,
                            )
                            self.hint_reveal = DecryptReveal(
                                final_hint,
                                self.hint_font,
                                (self.width // 2 - 500, next_y, 1000, 400),
                                reveal_speed_ms=25,
                            )
                            self.current_hint_lines = hint_lines_count
                            audio.play("hint", loops=-1)

                        was_finished = self.hint_reveal.finished
                        self.hint_reveal.update()
                        self.hint_reveal.draw(self.virtual_screen)

                        if self.hint_reveal.finished and not was_finished:
                            audio.stop("hint")

                        if self.hint_reveal.finished:
                            spaced_masked = " ".join(
                                list(r.clue.get_masked_answer(r.guessed_letters))
                            )
                            ans_max_width = 1020
                            ans_lines = wrap_text(
                                spaced_masked, self.font_large, ans_max_width
                            )
                            ans_height = len(ans_lines) * self.font_large.get_linesize()
                            hint_bottom_y = next_y + (
                                self.current_hint_lines * self.hint_font.get_linesize()
                            )
                            ans_y_start = (
                                hint_bottom_y
                                + (self.height - hint_bottom_y) // 2
                                - (ans_height // 2)
                            )
                            self.draw_wrapped_text(
                                self.virtual_screen,
                                spaced_masked,
                                ans_y_start,
                                self.font_large,
                                GREEN,
                                max_width=ans_max_width,
                                center=True,
                            )

                # Render sidebar UI
                self.right_ui.draw(self.virtual_screen)
                self.left_ui.draw(self.virtual_screen)

        elif self.state == GameState.PAUSE:
            self.draw_text(self.virtual_screen, "PAUSED", 50, 50, self.font_large)
            self.draw_text(
                self.virtual_screen,
                "1. Visit Store",
                50,
                120,
                self.font_med,
                action_id="STORE",
            )
            self.draw_text(
                self.virtual_screen,
                "2. Open Inventory",
                50,
                170,
                self.font_med,
                action_id="INVENTORY",
            )
            self.draw_text(
                self.virtual_screen,
                "Q. Quit to Main Menu",
                50,
                220,
                self.font_med,
                RED,
                action_id="QUIT_TO_MENU",
            )
            self.draw_text(
                self.virtual_screen,
                "[ESC] Return to Game",
                50,
                280,
                self.font_small,
                GRAY,
                action_id="RESUME",
            )

        elif self.state == GameState.STORE:
            self.visual_store.update(dt)
            self.visual_store.draw(self.virtual_screen, mx, my)
            self.draw_text(
                self.virtual_screen,
                "[ESC] Back",
                50,
                50,
                self.font_small,
                GRAY,
                action_id="BACK",
            )

        elif self.state == GameState.INVENTORY:
            self.draw_text(self.virtual_screen, "INVENTORY", 50, 50, self.font_large)
            self.draw_text(
                self.virtual_screen,
                "[ESC] Back",
                50,
                100,
                self.font_small,
                GRAY,
                action_id="BACK",
            )
            y_offset = 140
            owned = [(k, v) for k, v in self.manager.inventory.items() if v > 0]
            if not owned:
                self.draw_text(
                    self.virtual_screen,
                    "Your inventory is empty.",
                    50,
                    y_offset,
                    self.font_med,
                )
            else:
                for i, (mod_id, count) in enumerate(owned):
                    self.draw_text(
                        self.virtual_screen,
                        f"{i+1}. {STORE_CATALOG[mod_id].name} (Own: {count})",
                        50,
                        y_offset,
                        self.font_med,
                        action_id=f"USE_{mod_id}",
                    )
                    y_offset += 40

        elif self.state == GameState.ROUND_OVER:
            self.draw_text(self.virtual_screen, "ROUND OVER", 50, 50, self.font_large)
            msg = (
                f"CORRECT! Earned ${int(self.round_result.get('points_earned', 0) * 1000):,}."
                if self.round_result.get("won")
                else "GAME OVER. Out of guesses."
            )
            if self.round_result.get("is_all_in"):
                msg += " (ALL OR NOTHING)"
            self.draw_text(
                self.virtual_screen,
                msg,
                50,
                120,
                self.font_med,
                GREEN if self.round_result.get("won") else RED,
            )
            self.draw_text(
                self.virtual_screen,
                f"Answer: {self.round_result.get('answer')}",
                50,
                170,
                self.font_med,
            )
            self.draw_text(
                self.virtual_screen,
                "1. Play Again",
                50,
                250,
                self.font_med,
                action_id="PLAY_AGAIN",
            )
            self.draw_text(
                self.virtual_screen,
                "2. Main Menu",
                50,
                300,
                self.font_med,
                action_id="MAIN_MENU",
            )

        if self.status_timer > 0:
            self.draw_text(
                self.virtual_screen,
                self.status_message,
                self.width // 2 - 150,
                self.height - 50,
                self.font_small,
                (255, 255, 0),
            )

        # Win Effect
        self.gold_transition.draw(self.virtual_screen)


if __name__ == "__main__":
    game = Game()
    game.run()
