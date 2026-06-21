"""
starfield_bg.py
~~~~~~~~~~~~
Creates a dynamic starfield background with gradient and shooting stars
"""

import pygame
import random
import math


class Starfield:
    def __init__(self, width, height, speed=1.0):
        self.width = width
        self.height = height
        self.speed = speed
        self.center_x = width // 2
        self.center_y = height // 2
        self.k = 128.0

        self.STAR_COLORS = [
            (180, 160, 255),
            (150, 130, 230),
            (130, 110, 210),
            (100, 90, 180),
            (80, 70, 160),
        ]
        self.GOLDEN_COLOR = (255, 220, 100)

        # Generate stars
        self.stars = [
            [
                random.uniform(-self.width, self.width),
                random.uniform(-self.height, self.height),
                random.uniform(0.1, 2.0),
                random.uniform(0.01, 0.05),
                random.choice(self.STAR_COLORS),
                random.randint(3, 8),
            ]
            for _ in range(400)
        ]

        # Generate the hardware-accelerated gradient
        self.gradient_surface = self._create_gradient()

    def _create_gradient(self):
        surface = pygame.Surface((self.width, self.height))
        max_radius = int(math.sqrt(self.center_x**2 + self.center_y**2))

        for radius in range(max_radius, 0, -2):
            ratio = radius / max_radius
            if ratio < 0.4:
                t = ratio / 0.4
                r, g, b = (
                    int(20 * (1 - t) + 15 * t),
                    int(10 * (1 - t) + 10 * t),
                    int(40 * (1 - t) + 35 * t),
                )
            elif ratio < 0.7:
                t = (ratio - 0.4) / 0.3
                r, g, b = (
                    int(15 * (1 - t) + 10 * t),
                    int(10 * (1 - t) + 10 * t),
                    int(35 * (1 - t) + 25 * t),
                )
            else:
                t = (ratio - 0.7) / 0.3
                r, g, b = (
                    int(10 * (1 - t) + 5 * t),
                    int(10 * (1 - t) + 5 * t),
                    int(25 * (1 - t) + 15 * t),
                )
            pygame.draw.circle(
                surface, (r, g, b), (self.center_x, self.center_y), radius
            )

        return surface.convert()

    def draw(self, surface):
        """Draws the gradient and updates/draws the stars onto the provided surface."""
        # Draw gradient first (acts as screen wipe)
        surface.blit(self.gradient_surface, (0, 0))

        # Update and draw stars
        for star in self.stars:
            if star[2] <= 0.1:
                star[4] = (
                    self.GOLDEN_COLOR
                    if random.random() < 0.15
                    else random.choice(self.STAR_COLORS)
                )
                star[0] = random.uniform(-self.width, self.width)
                star[1] = random.uniform(-self.height, self.height)
                star[2] = random.uniform(1.5, 2.0)
                star[5] = random.randint(3, 8)

            star[2] -= star[3] * self.speed

            z_factor = star[2] + self.k
            x = star[0] * self.k / z_factor + self.center_x
            y = star[1] * self.k / z_factor + self.center_y

            if 0 <= x < self.width and 0 <= y < self.height:
                depth = 1.0 - min(1.0, star[2] / 2.0)
                size = max(1, int(2 * depth))
                brightness = 0.4 + 0.6 * depth

                base_color = star[4]
                color = (
                    int(base_color[0] * brightness),
                    int(base_color[1] * brightness),
                    int(base_color[2] * brightness),
                )

                pygame.draw.circle(surface, color, (int(x), int(y)), size)

                if depth > 0.3 and star[5] > 0:
                    dx, dy = x - self.center_x, y - self.center_y
                    dist_sq = dx * dx + dy * dy
                    if dist_sq > 0:
                        dist = math.sqrt(dist_sq)
                        dx, dy = dx / dist, dy / dist

                        trail_length = int(star[5] * depth)
                        trail_color = (
                            int(color[0] * 0.4),
                            int(color[1] * 0.4),
                            int(color[2] * 0.4),
                        )

                        pygame.draw.line(
                            surface,
                            trail_color,
                            (int(x), int(y)),
                            (int(x - dx * trail_length), int(y - dy * trail_length)),
                            1,
                        )
