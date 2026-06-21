"""
ui_elements.py
~~~~~~~~~~~~~~
Implements dynamic visual components for the user interface, including
custom interactive checkboxes and customizable modular display squares.
"""

import pygame
import math
from src.effects import UIAnimator
from src.constants import GOLD
from src.font_manager import FontManager


class CategoryCheckbox:
    def __init__(self, x, y, size, color):
        self.base_x = x
        self.base_y = y
        self.base_size = size
        self.base_color = color
        self.checked = True
        self.animator = UIAnimator()

    def trigger_effect(self, effect_idx):
        self.animator.trigger(self.base_x, self.base_y, effect_idx)

    def update(self, dt):
        self.animator.update(
            dt, self.base_x, self.base_y, self.base_size, self.base_color
        )

    def draw(self, surface):
        self.animator.draw_particles(surface)

        if self.animator.current_size > 0:
            current_size = int(self.animator.current_size * 2)
            square_surf = pygame.Surface((current_size, current_size), pygame.SRCALPHA)
            current_color = (
                self.animator.current_color if self.checked else (100, 100, 100)
            )

            if self.checked:
                pygame.draw.rect(
                    square_surf,
                    (*current_color, 255),
                    (0, 0, current_size, current_size),
                    border_radius=4,
                )
            else:
                pygame.draw.rect(
                    square_surf,
                    (*current_color, 255),
                    (0, 0, current_size, current_size),
                    width=3,
                    border_radius=4,
                )

            # --- OPTIMIZATION: Skip rotation math if angle is near zero ---
            if abs(self.animator.current_rotation) < 0.01:
                rect = square_surf.get_rect(
                    center=(int(self.animator.current_x), int(self.animator.current_y))
                )
                surface.blit(square_surf, rect)
            else:
                rotated = pygame.transform.rotate(
                    square_surf, math.degrees(self.animator.current_rotation) % 360
                )
                rect = rotated.get_rect(
                    center=(int(self.animator.current_x), int(self.animator.current_y))
                )
                surface.blit(rotated, rect)


class Square:
    def __init__(
        self,
        x,
        y,
        size,
        color,
        effect_index,
        symbol,
        modifier,
        font_symbol,
        font_cost,
        style="store",
        keybind="",
        font_name=None,
    ):
        self.base_x = x
        self.base_y = y
        self.base_size = size
        self.base_color = color

        self.effect_index = effect_index
        self.symbol = symbol
        self.modifier = modifier
        self.mod_id = modifier.id
        self.name = modifier.name
        self.description = modifier.description

        self.font_symbol = font_symbol
        self.font_cost = font_cost
        self.font_name = font_name

        self.font_count = FontManager.get(None, 42)

        self.style = style
        self.keybind = keybind

        self.animator = UIAnimator()
        self.animator.effect_index = effect_index
        self.animator.idle_enabled = True

    def check_hover(self, mx, my):
        rect = pygame.Rect(
            self.base_x - self.base_size,
            self.base_y - self.base_size,
            self.base_size * 2,
            self.base_size * 2,
        )
        return rect.collidepoint(mx, my)

    def start_effect(self):
        self.animator.trigger(self.base_x, self.base_y, self.effect_index)

    def update(self, dt):
        self.animator.update(
            dt, self.base_x, self.base_y, self.base_size, self.base_color
        )

    def draw(self, surface, is_owned=False, count=0):
        self.animator.draw_particles(surface)

        if self.animator.current_size > 0:
            current_size = int(self.animator.current_size * 2)
            sq_surf = pygame.Surface((current_size, current_size), pygame.SRCALPHA)

            bg_color = (*self.animator.current_color, 255)
            pygame.draw.rect(
                sq_surf, bg_color, (0, 0, current_size, current_size), border_radius=8
            )

            if self.style == "inventory" and not is_owned:
                pygame.draw.rect(
                    sq_surf,
                    (40, 40, 40, 130),
                    (0, 0, current_size, current_size),
                    border_radius=8,
                )

            if self.style == "inventory" and not is_owned:
                sym_color = (255, 255, 255)
                sym_alpha = 200
            else:
                sym_color = (0, 0, 0)
                sym_alpha = 255

            sym_surf = self.font_symbol.render(self.symbol, True, sym_color)
            if sym_alpha < 255:
                sym_surf.set_alpha(sym_alpha)

            y_offset = -10 if (self.style == "inventory" and is_owned) else 0
            sq_surf.blit(
                sym_surf,
                sym_surf.get_rect(
                    center=(current_size // 2, current_size // 2 + y_offset)
                ),
            )

            if self.style == "inventory" and is_owned and self.font_name:
                if current_size > 15:
                    name_surf = self.font_name.render(self.name, True, (0, 0, 0))
                    target_width = current_size - 6
                    if name_surf.get_width() > target_width:
                        name_surf = pygame.transform.smoothscale(
                            name_surf, (target_width, name_surf.get_height())
                        )
                    sq_surf.blit(
                        name_surf,
                        name_surf.get_rect(
                            center=(current_size // 2, current_size - 15)
                        ),
                    )

            # --- OPTIMIZATION: Skip rotation math if angle is near zero ---
            if abs(self.animator.current_rotation) < 0.01:
                rect = sq_surf.get_rect(
                    center=(int(self.animator.current_x), int(self.animator.current_y))
                )
                surface.blit(sq_surf, rect)
            else:
                rotated = pygame.transform.rotate(
                    sq_surf, math.degrees(self.animator.current_rotation) % 360
                )
                rect = rotated.get_rect(
                    center=(int(self.animator.current_x), int(self.animator.current_y))
                )
                surface.blit(rotated, rect)

            if self.style == "store":
                cost_surf = self.font_cost.render(
                    f"${self.modifier.cost}", True, (255, 255, 255)
                )
                cost_rect = cost_surf.get_rect(topleft=(rect.left - 10, rect.top - 10))
                tag_bg = cost_rect.inflate(12, 8)
                pygame.draw.rect(surface, (40, 80, 40), tag_bg, border_radius=4)
                pygame.draw.rect(
                    surface, (255, 215, 0), tag_bg, width=2, border_radius=4
                )
                surface.blit(cost_surf, cost_rect)

                key_surf = self.font_cost.render(
                    f"[{self.keybind}]", True, (200, 200, 200)
                )
                key_rect = key_surf.get_rect(
                    bottomright=(rect.right + 10, rect.bottom + 5)
                )
                pygame.draw.rect(
                    surface, (30, 30, 35), key_rect.inflate(8, 6), border_radius=4
                )
                surface.blit(key_surf, key_rect)

            elif self.style == "inventory" and count > 1:
                text = f"x{count}"
                text_x, text_y = rect.left - 10, rect.top - 15

                # --- OPTIMIZATION: Render outline once, blit 8 times ---
                out_surf = self.font_count.render(text, True, (0, 0, 0))
                in_surf = self.font_count.render(text, True, GOLD)

                for dx, dy in [
                    (-2, -2),
                    (-2, 2),
                    (2, -2),
                    (2, 2),
                    (0, -2),
                    (-2, 0),
                    (2, 0),
                    (0, 2),
                ]:
                    surface.blit(out_surf, (text_x + dx, text_y + dy))
                surface.blit(in_surf, (text_x, text_y))
