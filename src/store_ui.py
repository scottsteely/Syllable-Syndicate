"""
store_ui.py
~~~~~~~~~~~
Renders and controls the visual modular store matrix interface. Manages
mouse/keyboard selection hooks, item layout calculation, dynamic tooltips,
and transaction display synchronization.
"""

import pygame
from src.modifiers import STORE_CATALOG
from src.effects import PulsingText
from src.ui_elements import Square
from src.constants import SQUARE_COLORS, STORE_SYMBOLS
from src.font_manager import FontManager
from src.text_utils import wrap_text


class VisualStore:
    def __init__(self, width, height, game_manager):
        self.width = width
        self.height = height
        self.manager = game_manager

        self.font_symbol = FontManager.get("portraits", 200)
        self.font_title = FontManager.get("skittled", 25)
        self.font_cost = FontManager.get("bricks", 25)
        self.font_tooltip = FontManager.get("doodles", 30)
        self.font_instructions = FontManager.get("bank_gothic", 80)

        self.DARK_GOLD = pygame.Color(130, 90, 0)
        self.LIGHT_GOLD = pygame.Color(255, 215, 0)

        self.title_effect = PulsingText(
            self.font_instructions,
            lambda: f"Store | Bankroll: ${int(self.manager.total_score * 1000):,}k",
            self.DARK_GOLD,
            self.LIGHT_GOLD,
        )

        self.symbols_list = STORE_SYMBOLS
        self.squares = []
        self._init_squares()

        # --- OPTIMIZATION: Cache labels and tooltips ---
        self._label_surfs = {}
        for sq in self.squares:
            display_name = sq.name if len(sq.name) < 25 else sq.name[:22] + "..."
            self._label_surfs[sq.mod_id] = self.font_title.render(
                display_name, True, (200, 200, 200)
            ).convert_alpha()

        self._tooltip_cache = {}

    def _init_squares(self):
        modifiers_data = list(STORE_CATALOG.values())
        mod_keys = list(STORE_CATALOG.keys())

        cols, rows = 5, 2
        spacing_x = self.width // (cols + 1)
        spacing_y = self.height // (rows + 1)

        for i in range(min(10, len(modifiers_data))):
            col = i % cols
            row = i // cols
            x = spacing_x * (col + 1)
            y = spacing_y * (row + 1) + 80
            keybind = self.symbols_list[i]

            square = Square(
                x,
                y,
                50,
                SQUARE_COLORS[i],
                i,
                keybind,
                modifiers_data[i],
                self.font_symbol,
                self.font_cost,
                style="store",
                keybind=keybind,
            )
            square.mod_id = mod_keys[i]
            self.squares.append(square)

    def handle_click(self, mx, my):
        for sq in self.squares:
            if sq.check_hover(mx, my):
                success = self.manager.buy_item(sq.mod_id)
                if success:
                    sq.start_effect()
                return success, sq.name, sq.mod_id
        return None, None, None

    def handle_keydown(self, unicode_char):
        char = unicode_char.upper()
        for sq in self.squares:
            if sq.keybind == char:
                success = self.manager.buy_item(sq.mod_id)
                if success:
                    sq.start_effect()
                return success, sq.name, sq.mod_id
        return None, None, None

    def update(self, dt):
        for sq in self.squares:
            sq.update(dt)

    def draw(self, surface, mx, my):
        self.title_effect.draw(surface, (self.width // 2, self.height // 6))

        hovered_desc = None
        hover_x, hover_y = mx, my

        for sq in self.squares:
            sq.draw(surface)
            if sq.check_hover(mx, my):
                hovered_desc = sq.description

        self._draw_labels(surface)

        if hovered_desc:
            self._draw_tooltip(surface, hovered_desc, hover_x + 15, hover_y + 15)

    def _draw_labels(self, surface):
        for sq in self.squares:
            label = self._label_surfs[sq.mod_id]
            surface.blit(label, (sq.base_x - label.get_width() // 2, sq.base_y + 60))

    def _draw_tooltip(self, surface, text, x, y):
        # --- OPTIMIZATION: Cache tooltip wrapping/rendering ---
        if text not in self._tooltip_cache:
            lines = wrap_text(text, self.font_tooltip, 250)
            height = len(lines) * self.font_tooltip.get_linesize() + 16
            width = (
                max([self.font_tooltip.size(line)[0] for line in lines]) + 16
                if lines
                else 16
            )

            tooltip_surf = pygame.Surface((width, height), pygame.SRCALPHA)
            pygame.draw.rect(
                tooltip_surf, (30, 30, 45, 230), (0, 0, width, height), border_radius=4
            )
            pygame.draw.rect(
                tooltip_surf, (150, 150, 150), (0, 0, width, height), 2, border_radius=4
            )

            for i, line in enumerate(lines):
                text_surf = self.font_tooltip.render(line, True, (240, 240, 240))
                tooltip_surf.blit(
                    text_surf, (8, 8 + i * self.font_tooltip.get_linesize())
                )

            self._tooltip_cache[text] = (tooltip_surf, width, height)

        tooltip_surf, width, height = self._tooltip_cache[text]

        if x + width > self.width:
            x = self.width - width - 10
        if y + height > self.height:
            y = self.height - height - 10

        surface.blit(tooltip_surf, (x, y))
