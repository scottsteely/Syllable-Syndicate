"""
dates.py
~~~~~~~~~~~~~~~~
Creates a visual date spinning element with bounce. Takes a target year input.
"""

import pygame
import math
from src.font_manager import FontManager


class DateSpinner:
    def __init__(self, target_year, width=1000, height=150, screen_width=1920):
        self.target_year = int(target_year)
        self.total_time = 4.0
        self.bounces = 4.5
        self.decay = 11.0

        self.width = width
        self.height = height
        self.screen_width = screen_width

        # The final surface that goes on screen
        self.surface = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        # The temporary surface we draw the text and gradient onto before masking
        self.content_surface = pygame.Surface(
            (self.width, self.height), pygame.SRCALPHA
        )

        self.font = FontManager.get("brunson", 42)
        self.start_year = 1900
        self.end_year = 2026

        self.year_surfaces = {
            y: self.font.render(str(y), True, (0, 200, 255))
            for y in range(self.start_year, self.end_year + 1)
        }

        self.spacing = 120
        self.line_x = self.width / 2.0  # Center of our mini-canvas

        # Calculate scroll boundaries
        self.min_scroll_x = self.get_target_scroll_x(self.start_year)
        self.max_scroll_x = self.get_target_scroll_x(self.end_year)

        # Set up easing
        self.ease_start_x = self.min_scroll_x
        self.ease_target_x = self.get_target_scroll_x(self.target_year)
        self.ease_start_time = pygame.time.get_ticks() / 1000.0

        self.scroll_x = self.ease_start_x
        self.date_animation_complete = False

        # 1. Pre-render the vertical target line
        self.target_line_surface = pygame.Surface((4, self.height), pygame.SRCALPHA)
        half_height = self.height / 2.0
        for y in range(self.height):
            dist_y = abs(y - half_height) / half_height
            alpha_y = int(255 * (dist_y**2))
            pygame.draw.line(
                self.target_line_surface, (255, 255, 255, alpha_y), (0, y), (3, y)
            )

        # 2. Pre-render the horizontal gradient overlay (transparent center, black edges)
        self.horiz_overlay = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        half_width = self.width / 2.0
        horizontal_pinch = 1.5
        for x in range(self.width):
            dist_x = abs(x - half_width) / half_width
            adj_dist = min(1.0, dist_x * horizontal_pinch)
            alpha_x = int(255 * (adj_dist**2))
            # Fade to black on the edges to hide the scrolling numbers
            pygame.draw.line(
                self.horiz_overlay, (0, 0, 0, alpha_x), (x, 0), (x, self.height)
            )

    def get_target_scroll_x(self, year):
        i = year - self.start_year
        return (
            self.line_x - self.year_surfaces[year].get_width() / 2.0 + i * self.spacing
        )

    def spring_ease(self, t, bounces, decay):
        if t >= 1.0:
            return 1.0
        freq = bounces * 2 * math.pi
        amplitude = math.exp(-decay * t)
        return 1.0 - amplitude * math.cos(freq * t)

    def update(self, dt):
        if self.date_animation_complete:
            return

        current_time = pygame.time.get_ticks() / 1000.0
        elapsed = current_time - self.ease_start_time
        t = min(elapsed / self.total_time, 1.0)

        if t >= 1.0:
            self.date_animation_complete = True
            self.scroll_x = self.ease_target_x
            return

        eased_t = self.spring_ease(t, self.bounces, self.decay)
        raw_scroll_x = (
            self.ease_start_x + (self.ease_target_x - self.ease_start_x) * eased_t
        )
        self.scroll_x = max(self.min_scroll_x, min(raw_scroll_x, self.max_scroll_x))

    def draw(self, screen, screen_y_center):
        # 1. Clear the content canvas (make it fully transparent)
        self.content_surface.fill((0, 0, 0, 0))

        local_y_center = self.height // 2

        # 2. Draw target line onto the content canvas
        self.content_surface.blit(self.target_line_surface, (self.line_x, 0))

        # 3. Draw years onto the content canvas
        for i, year in enumerate(range(self.start_year, self.end_year + 1)):
            x = self.scroll_x - i * self.spacing
            y = local_y_center - self.year_surfaces[year].get_height() // 2

            # Only draw if the text is somewhat inside our container's width
            if -100 < x < self.width + 100:
                if year == self.target_year and self.date_animation_complete:
                    surf = self.font.render(
                        str(year), True, (255, 200, 0)
                    )  # Turn gold when finished
                else:
                    surf = self.year_surfaces[year]
                self.content_surface.blit(surf, (x, y))

        # 4. Apply the gradient overlay over the text
        self.content_surface.blit(self.horiz_overlay, (0, 0))

        # 5. Masking Magic
        # Clear the main container
        self.surface.fill((0, 0, 0, 0))

        # Draw the solid white mask. Setting border_radius to half the height ensures maximum, edgeless rounding.
        pygame.draw.rect(
            self.surface,
            (255, 255, 255, 255),
            self.surface.get_rect(),
            border_radius=self.height // 2,
        )

        # Stamp the content into the mask. The BLEND_RGBA_MIN flag cuts away the hard corners.
        self.surface.blit(
            self.content_surface, (0, 0), special_flags=pygame.BLEND_RGBA_MIN
        )

        # 6. Blit the finished, edgeless container onto the main screen
        screen_x = (self.screen_width - self.width) // 2
        screen_y = screen_y_center - (self.height // 2)

        screen.blit(self.surface, (screen_x, screen_y))
