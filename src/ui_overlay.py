"""
ui_overlay.py
~~~~~~~~~~~~~
Renders complex HUD panels, text trackers, interactive alphanumeric layout grids,
and performance caching states for managing primary sidebar displays.
"""

import pygame
import math
import random
from src.modifiers import STORE_CATALOG
from src.effects import FXManager, PulsingText
from src.ui_elements import Square
from src.emote import Emote
from src.constants import SQUARE_COLORS, STORE_SYMBOLS, ALPHABET, GOLD, WHITE
from src.font_manager import FontManager


class RightUIOverlay:
    def __init__(self, width, height, game_manager):
        self.width = width
        self.height = height
        self.manager = game_manager

        # --- Refactored Fonts via FontManager ---
        self.font_title = FontManager.get("capitolcity", 48)
        self.font_symbol = FontManager.get("portraits", 120)
        self.font_cost = FontManager.get("bricks", 15)
        self.font_doodles = FontManager.get("doodles", 22)
        self.font_count = FontManager.get(None, 28)

        self.squares = []
        self._init_squares()
        self.title_fx = PulsingText(
            self.font_title,
            "MOD SQUAD",
            GOLD,  # Using Constant
            (255, 140, 0),  # End: Orange
            speed=2.5,
        )

        self._panel_surf = pygame.Surface((400, self.height), pygame.SRCALPHA)
        self._panel_surf.fill((20, 20, 25, 180))

    def _init_squares(self):
        modifiers_data = list(STORE_CATALOG.values())
        mod_keys = list(STORE_CATALOG.keys())

        spacing_y = self.height // 6

        for i in range(min(10, len(modifiers_data))):
            col = i % 2
            row = i // 2

            x = (self.width - 400) + 110 + (col * 180)
            y = spacing_y * (row + 1)

            square = Square(
                x,
                y,
                45,
                SQUARE_COLORS[i],  # Using Constant
                i,
                STORE_SYMBOLS[i],  # Using Constant
                modifiers_data[i],
                self.font_symbol,
                self.font_cost,
                style="inventory",
                font_name=self.font_doodles,
            )
            square.mod_id = mod_keys[i]
            square.original_color = SQUARE_COLORS[i]  # Using Constant
            self.squares.append(square)

    def handle_click(self, mx, my):
        for sq in self.squares:
            if sq.check_hover(mx, my):
                if self.manager.inventory.get(sq.mod_id, 0) > 0:
                    res = self.manager.activate_item(sq.mod_id)
                    if res.get("success"):
                        sq.start_effect()
                    return sq.mod_id, res
                else:
                    return sq.mod_id, {
                        "success": False,
                        "message": "You don't own this!",
                        "results": [],
                    }

        return None, {}

    def update(self, dt):
        for sq in self.squares:
            count = self.manager.inventory.get(sq.mod_id, 0)
            sq.animator.idle_enabled = count > 0
            sq.base_color = sq.original_color
            sq.update(dt)

    def draw(self, surface):
        panel_rect = pygame.Rect(self.width - 400, 0, 400, self.height)
        surface.blit(self._panel_surf, panel_rect)

        self.title_fx.draw(surface, (self.width - 200, 50))

        for sq in self.squares:
            count = self.manager.inventory.get(sq.mod_id, 0)
            sq.draw(surface, is_owned=(count > 0), count=count)


class LeftUIOverlay:
    def __init__(self, width, height, game_manager):
        self.width = width
        self.height = height
        self.manager = game_manager

        # --- Fonts via FontManager ---
        self.font_cat = FontManager.get("capitolcity", 48)
        self.font_letter = FontManager.get("led_display", 48)
        self.font_store = FontManager.get(None, 40)
        self.font_ticker = FontManager.get("led_display", 36)
        self.font_dollar = FontManager.get(None, 24)

        self.cat_fx = PulsingText(
            self.font_cat,
            lambda: (
                self.manager.current_category
                if self.manager.current_category
                else "NO CAT"
            ),
            GOLD,  # Using Constant
            (255, 140, 0),
            speed=2.5,
        )

        # --- Layout Alignment ---
        self.emote = Emote(200, 200)
        self.ticker_y = 350
        self.store_y = self.height - 60

        self.grid_cols = 5
        self.spacing_x = 65
        self.spacing_y = 65
        grid_width = (self.grid_cols - 1) * self.spacing_x
        grid_height = ((len(ALPHABET) // self.grid_cols)) * self.spacing_y

        available_space_top = self.ticker_y + 40
        available_space_bottom = self.store_y - 40
        middle_y = (
            available_space_top + (available_space_bottom - available_space_top) // 2
        )

        self.start_x = 200 - (grid_width // 2)
        self.start_y = middle_y - (grid_height // 2)

        # --- State Tracking ---
        self.scared_timer = 0.0
        self.last_guesses_remaining = 0
        self.current_round_ref = None

        # --- Visual FX Trackers ---
        self.displayed_score = float(self.manager.total_score)
        self.target_score = self.manager.total_score
        self.current_heat = 0
        self.fx_manager = FXManager()

        self.letter_data = {}
        for i, letter in enumerate(ALPHABET):  # Using Constant
            col = i % self.grid_cols
            row = i // self.grid_cols
            x = self.start_x + (col * self.spacing_x)
            y = self.start_y + (row * self.spacing_y)

            self.letter_data[letter] = {
                "x": x,
                "y": y,
                "base_x": x,
                "base_y": y,
                "state": "UNPICKED",
                "particles": [],
                "timer": 0.0,
                "rect": pygame.Rect(x - 20, y - 20, 40, 40),
            }

        self.store_rect = None

        # --- OPTIMIZATION: Pre-render panel and letters ---
        self._panel_surf = pygame.Surface((400, self.height), pygame.SRCALPHA)
        self._panel_surf.fill((20, 20, 25, 180))

        self._letter_surfs = {}
        for char in ALPHABET:  # Using Constant
            # 1. Render the text and immediately convert to support per-pixel alpha
            unpicked = self.font_letter.render(char, True, WHITE).convert_alpha()
            correct = self.font_letter.render(char, True, GOLD).convert_alpha()
            wrong = self.font_letter.render(char, True, (100, 40, 40)).convert_alpha()

            # 2. Use BLEND_RGBA_MULT to safely lower the alpha channel
            #    without triggering the bounding box bug during scaling.
            unpicked.fill((255, 255, 255, 40), special_flags=pygame.BLEND_RGBA_MULT)
            wrong.fill((255, 255, 255, 150), special_flags=pygame.BLEND_RGBA_MULT)

            self._letter_surfs[char] = {
                "UNPICKED": unpicked,
                "CORRECT": correct,
                "WRONG": wrong,
            }

        # --- OPTIMIZATION: Cache for dynamic glow and particle surfaces ---
        self._glow_cache = {}
        self._particle_cache = {}

    def trigger_guess_fx(self, result: dict):
        char = result.get("char")
        status = result.get("status")

        if not char or status == "ignored":
            return

        if len(char) != 1 or char not in self.letter_data:
            return

        ld = self.letter_data[char]
        points = result.get("points", 0)
        self.current_heat = result.get("heat", 0)

        if status == "correct":
            ld["state"] = "CORRECT"
            ld["timer"] = 1.0
            self.emote.trigger_face_change("Happy")
            if self.current_heat >= 3:
                self.fx_manager.spawn_fire(200, self.ticker_y + 30)

            is_bounty = result.get("is_bounty", False)
            if is_bounty:
                self.fx_manager.spawn_fireworks(self.width // 2, self.height // 2)

            for _ in range(25):
                angle = random.uniform(0, math.pi * 2)
                speed = random.uniform(80, 200)
                ld["particles"].append(
                    {
                        "x": ld["base_x"],
                        "y": ld["base_y"],
                        "vx": math.cos(angle) * speed,
                        "vy": math.sin(angle) * speed,
                        "life": 1.0,
                        "color": GOLD,  # Using Constant
                    }
                )

            display_val = int(points * 1000)
            float_text = f"+${display_val:,}"
            if is_bounty:
                float_text = "BOUNTY! " + float_text

            self.fx_manager.spawn_floating_text(
                ld["base_x"],
                ld["base_y"],
                float_text,
                (0, 255, 0) if not is_bounty else (255, 0, 255),
                (150, 250),
            )

        elif status == "incorrect":
            ld["state"] = "WRONG"
            ld["timer"] = 0.5
            for _ in range(15):
                angle = random.uniform(0, math.pi)
                speed = random.uniform(50, 120)
                ld["particles"].append(
                    {
                        "x": ld["base_x"],
                        "y": ld["base_y"],
                        "vx": math.cos(angle) * speed,
                        "vy": abs(math.sin(angle)) * speed,
                        "life": 0.8,
                        "color": (100, 30, 30),
                    }
                )

            display_penalty = int(abs(points) * 1000)
            self.fx_manager.spawn_floating_text(
                ld["base_x"],
                ld["base_y"],
                f"-${display_penalty:,}",
                (255, 0, 0),
                (100, 150),
            )

    def update(self, dt):
        r = self.manager.current_round

        if not r:
            self.last_guesses_remaining = 0
            self.current_round_ref = None
            self.scared_timer = 0.0
            self.current_heat = 0
            return

        if r != self.current_round_ref:
            self.current_round_ref = r
            self.last_guesses_remaining = r.guesses_remaining
            self.scared_timer = 0.0
            self.current_heat = 0

            self.emote.trigger_face_change("Bored")
            for ld in self.letter_data.values():
                ld["state"] = "UNPICKED"
                ld["particles"] = []
                ld["timer"] = 0.0

        current_remaining = r.guesses_remaining
        if current_remaining < self.last_guesses_remaining:
            if current_remaining <= 0:
                self.emote.trigger_face_change("Dead")
            elif current_remaining == 1:
                self.emote.trigger_face_change("Very Mad")
                self.scared_timer = 3.0
            else:
                self.emote.trigger_face_change("Mad")
        elif (
            current_remaining == self.last_guesses_remaining
            and r.is_won
            and not self.emote.current_face == "Happy"
        ):
            self.emote.trigger_face_change("Happy")

        if self.scared_timer > 0:
            self.scared_timer -= dt
            if self.scared_timer <= 0:
                self.emote.trigger_face_change("Scared")

        self.last_guesses_remaining = current_remaining
        self.emote.update(dt)

        if self.current_heat >= 3:
            self.fx_manager.spawn_fire(200, self.ticker_y + 30)

        self.fx_manager.update(dt)

        self.target_score = self.manager.total_score
        diff = self.target_score - self.displayed_score
        if abs(diff) > 0.01:
            self.displayed_score += diff * min(1.0, 8.0 * dt)
            if abs(self.target_score - self.displayed_score) < 0.01:
                self.displayed_score = self.target_score
        else:
            self.displayed_score = self.target_score

        for char, ld in self.letter_data.items():
            if ld["timer"] > 0:
                ld["timer"] -= dt

            if ld["state"] == "WRONG" and ld["timer"] > 0:
                shake = ld["timer"] * 8
                ld["x"] = ld["base_x"] + random.uniform(-shake, shake)
            else:
                ld["x"] = ld["base_x"]

            for p in ld["particles"]:
                p["x"] += p["vx"] * dt
                p["y"] += p["vy"] * dt
                p["life"] -= dt * 1.5
            ld["particles"] = [p for p in ld["particles"] if p["life"] > 0]

    def handle_click(self, mx, my):
        if self.store_rect and self.store_rect.inflate(20, 20).collidepoint(mx, my):
            return "OPEN_STORE"

        for char, ld in self.letter_data.items():
            if ld["rect"].collidepoint(mx, my):
                if self.manager.current_round and ld["state"] == "UNPICKED":
                    return char
        return None

    def draw(self, surface):
        panel_rect = pygame.Rect(0, 0, 400, self.height)
        surface.blit(self._panel_surf, panel_rect)

        self.fx_manager.draw_fireworks(surface)
        self.cat_fx.draw(surface, (200, 50))
        self.emote.draw(surface)
        self.fx_manager.draw_fire(surface)

        ticker_rect = pygame.Rect(0, 0, 280, 60)
        ticker_rect.center = (200, self.ticker_y)
        pygame.draw.rect(surface, (15, 15, 20), ticker_rect, border_radius=8)

        if int(self.displayed_score) != int(self.target_score):
            pulse = abs(math.sin(pygame.time.get_ticks() / 100)) * 255
            pygame.draw.rect(
                surface,
                (int(pulse), 255, int(pulse)),
                ticker_rect,
                width=3,
                border_radius=8,
            )
        elif self.current_heat >= 3:
            pygame.draw.rect(
                surface, (255, 100, 0), ticker_rect, width=3, border_radius=8
            )
        else:
            pygame.draw.rect(
                surface, GOLD, ticker_rect, width=2, border_radius=8  # Using Constant
            )

        display_val = int(self.displayed_score * 1000)
        score_str = f"${display_val:,}"
        score_surf = self.font_ticker.render(score_str, True, (0, 255, 0))
        surface.blit(score_surf, score_surf.get_rect(center=ticker_rect.center))

        self.fx_manager.draw_floating_text(surface, self.font_dollar)

        for char, ld in self.letter_data.items():
            state = ld["state"]
            letter_surf = self._letter_surfs[char][state]

            if state == "CORRECT":
                glow_radius = int(25 + math.sin(pygame.time.get_ticks() / 150.0) * 5)

                if glow_radius not in self._glow_cache:
                    glow_surf = pygame.Surface(
                        (glow_radius * 2, glow_radius * 2), pygame.SRCALPHA
                    )
                    pygame.draw.circle(
                        glow_surf,
                        (255, 215, 0, 40),  # Gold with custom Alpha, kept raw
                        (glow_radius, glow_radius),
                        glow_radius,
                    )
                    self._glow_cache[glow_radius] = glow_surf.convert_alpha()

                glow_surf = self._glow_cache[glow_radius]
                surface.blit(glow_surf, glow_surf.get_rect(center=(ld["x"], ld["y"])))

            rect = letter_surf.get_rect(center=(ld["x"], ld["y"]))
            surface.blit(letter_surf, rect)

            for p in ld["particles"]:
                p_alpha = int(255 * max(0, p["life"]))
                if p_alpha > 0:
                    alpha_q = (p_alpha // 16) * 16
                    key = (p["color"], alpha_q)

                    if key not in self._particle_cache:
                        p_surf = pygame.Surface((6, 6), pygame.SRCALPHA)
                        pygame.draw.circle(p_surf, (*p["color"], alpha_q), (3, 3), 3)
                        self._particle_cache[key] = p_surf.convert_alpha()

                    surface.blit(self._particle_cache[key], (int(p["x"]), int(p["y"])))

        store_surf = self.font_store.render("STORE", True, WHITE)  # Using Constant
        self.store_rect = store_surf.get_rect(center=(200, self.store_y))

        btn_bg = self.store_rect.inflate(30, 20)
        pygame.draw.rect(surface, (50, 50, 60), btn_bg, border_radius=8)
        pygame.draw.rect(surface, (100, 100, 110), btn_bg, width=2, border_radius=8)
        surface.blit(store_surf, self.store_rect)
