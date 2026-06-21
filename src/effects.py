"""
effects.py
~~~~~~~~~~
Handles visual particles, animations, text decoration routines, decrypt
sequences, and transitional screen overrides for gameplay elements.
"""

import pygame
import math
import random
import string
from src.text_utils import wrap_text
from src.font_manager import FontManager


class UIAnimator:
    """A standalone component that calculates transform and particle effects."""

    def __init__(self):
        self.is_animating = False
        self.anim_progress = 0.0
        self.anim_duration = 0.8
        self.effect_index = 0
        self.particles = []

        self.current_x = 0
        self.current_y = 0
        self.current_size = 0
        self.current_rotation = 0
        self.current_color = (255, 255, 255)

        self.vel_x = 0
        self.vel_y = 0
        self.idle_enabled = True

    def trigger(self, base_x, base_y, effect_index=None):
        self.is_animating = True
        self.anim_progress = 0.0
        if effect_index is not None:
            self.effect_index = effect_index

        self.particles = []
        if self.effect_index == 0:
            for _ in range(20):
                angle = random.uniform(0, 2 * math.pi)
                speed = random.uniform(100, 300)
                self.particles.append(
                    {
                        "x": base_x,
                        "y": base_y,
                        "vx": math.cos(angle) * speed,
                        "vy": math.sin(angle) * speed,
                        "size": random.randint(4, 10),
                        "life": 1.0,
                    }
                )

        # Effects #8 and #9 require additional handeling
        # seen here

        elif self.effect_index == 8:
            angle = random.uniform(0, 2 * math.pi)
            self.vel_x = math.cos(angle) * 400
            self.vel_y = math.sin(angle) * 400
        elif self.effect_index == 9:
            for _ in range(12):
                angle = random.uniform(0, 2 * math.pi)
                speed = random.uniform(80, 250)
                self.particles.append(
                    {
                        "x": base_x,
                        "y": base_y,
                        "vx": math.cos(angle) * speed,
                        "vy": math.sin(angle) * speed,
                        "size": random.randint(3, 8),
                        "life": 1.0,
                        "star": True,
                    }
                )

    def update(self, dt, base_x, base_y, base_size, base_color):
        self.current_size = base_size
        self.current_color = base_color
        self.current_rotation = 0

        if not self.is_animating:
            if self.idle_enabled:
                t = pygame.time.get_ticks() / 1000.0
                phase_x = self.effect_index * 13.7
                phase_y = self.effect_index * 19.3
                self.current_x = base_x + math.sin(t * 1.5 + phase_x) * 5
                self.current_y = base_y + math.cos(t * 1.2 + phase_y) * 5
            else:
                self.current_x = base_x
                self.current_y = base_y
            return

        self.current_x = base_x
        self.current_y = base_y
        self.anim_progress += dt / self.anim_duration
        if self.anim_progress >= 1.0:
            self.is_animating = False
            return

        t = self.anim_progress

        # The following is 10 different geometry effects
        # They are for the modifiers and catagory selection

        if self.effect_index == 0:
            for p in self.particles:
                p["x"] += p["vx"] * dt
                p["y"] += p["vy"] * dt
                p["life"] -= dt * 1.5
            self.current_size = max(0, base_size * (1 - t * 2))
        elif self.effect_index == 1:
            self.current_rotation = t * math.pi * 6
            self.current_size = base_size * (1 + math.sin(t * math.pi * 4) * 0.3)
        elif self.effect_index == 2:
            self.current_size = base_size * (1 + t * 1.5)
        elif self.effect_index == 3:
            intensity = 30 * (1 - t)
            self.current_x = base_x + random.uniform(-intensity, intensity)
            self.current_y = base_y + random.uniform(-intensity, intensity)
            self.current_rotation = random.uniform(-0.3, 0.3) * (1 - t)
        elif self.effect_index == 4:
            self.current_size = base_size * (1 - t)
        elif self.effect_index == 5:
            r = int(128 + 127 * math.sin(t * math.pi * 10))
            g = int(128 + 127 * math.sin(t * math.pi * 10 + 2))
            b = int(128 + 127 * math.sin(t * math.pi * 10 + 4))
            self.current_color = (r, g, b)
            self.current_rotation = t * math.pi * 4
        elif self.effect_index == 6:
            bounce = abs(math.sin(t * math.pi * 3))
            self.current_size = base_size * (1 + bounce * 0.5)
            self.current_rotation = bounce * 0.5
        elif self.effect_index == 7:
            self.current_size = base_size * (1 + t * 0.3)
        elif self.effect_index == 8:
            self.current_x += self.vel_x * dt * (1 - t)
            self.current_y += self.vel_y * dt * (1 - t)
            self.current_rotation += dt * math.pi * 12
        elif self.effect_index == 9:
            for p in self.particles:
                p["x"] += p["vx"] * dt
                p["y"] += p["vy"] * dt
                p["life"] -= dt * 1.2
            self.current_rotation = t * math.pi * 8

    def draw_particles(self, surface):
        for p in self.particles:
            if p["life"] > 0:
                alpha = int(255 * p["life"])
                size = max(1, int(p["size"] * p["life"]))
                particle_surf = pygame.Surface((size * 2, size * 2), pygame.SRCALPHA)
                pygame.draw.circle(
                    particle_surf, (*self.current_color, alpha), (size, size), size
                )
                surface.blit(particle_surf, (int(p["x"] - size), int(p["y"] - size)))


# The DecryptReveal slowly shows the hint text
# while displaying symbols in place takes hint
# text, font, rect size, and speed as input
#


class DecryptReveal:
    TEXT_COLOR = (45, 255, 100)
    SCRAMBLE_COLOR = (100, 150, 100)

    def __init__(self, text, font, rect, reveal_speed_ms=30):
        self.font = font
        self.rect = pygame.Rect(rect)
        self.target_lines = wrap_text(text, font, self.rect.width)
        self.reveal_speed_ms = reveal_speed_ms
        self.last_update = pygame.time.get_ticks()

        self.current_line_idx = 0
        self.locked_chars = 0
        self.finished = False

        self.charset = (
            string.ascii_uppercase + string.digits + "!@#$%^&*()_+-=[]{}|;:,.<>?"
        )

        # --- OPTIMIZATION: Pre-render character caches ---
        self._char_cache = {}
        for line in self.target_lines:
            for char in line:
                if char not in self._char_cache:
                    self._char_cache[char] = font.render(char, True, self.TEXT_COLOR)

        self._scramble_cache = {}
        for char in self.charset:
            self._scramble_cache[char] = font.render(char, True, self.SCRAMBLE_COLOR)

        self._space_width = font.size(" ")[0]

    def update(self):
        if self.finished:
            return

        now = pygame.time.get_ticks()
        if now - self.last_update > self.reveal_speed_ms:
            self.last_update = now
            self.locked_chars += 1

            if self.locked_chars > len(self.target_lines[self.current_line_idx]):
                self.locked_chars = 0
                self.current_line_idx += 1

                if self.current_line_idx >= len(self.target_lines):
                    self.finished = True
                    self.current_line_idx = len(self.target_lines) - 1
                    self.locked_chars = len(self.target_lines[-1])

    def draw(self, surface):
        y_offset = self.rect.y
        line_height = self.font.get_linesize()

        for i in range(self.current_line_idx + 1):
            target_text = self.target_lines[i]

            if i < self.current_line_idx or (
                i == self.current_line_idx and self.finished
            ):
                text_surf = self.font.render(target_text, True, self.TEXT_COLOR)
                surface.blit(text_surf, (self.rect.x, y_offset))
            elif i == self.current_line_idx and not self.finished:
                x_offset = self.rect.x
                for char_idx, char in enumerate(target_text):
                    if char == " ":
                        x_offset += self._space_width
                        continue

                    if char_idx < self.locked_chars:
                        surface.blit(self._char_cache[char], (x_offset, y_offset))
                    else:
                        random_char = random.choice(self.charset)
                        surface.blit(
                            self._scramble_cache[random_char], (x_offset, y_offset)
                        )

                    x_offset += self.font.size(char)[0]
            y_offset += line_height


class ColorPulser:
    def __init__(self, color_start, color_end, speed=3.0):
        self.color_start = (
            pygame.Color(*color_start)
            if not isinstance(color_start, pygame.Color)
            else color_start
        )
        self.color_end = (
            pygame.Color(*color_end)
            if not isinstance(color_end, pygame.Color)
            else color_end
        )
        self.speed = speed

    def get_color(self):
        time_now = pygame.time.get_ticks() / 1000.0
        pulse = (math.sin(time_now * self.speed) + 1) / 2.0
        return self.color_start.lerp(self.color_end, pulse)


class PulsingText:
    def __init__(self, font, text_content, color_start, color_end, speed=3.0):
        self.font = font
        self.text_content = text_content
        self.pulser = ColorPulser(color_start, color_end, speed)
        self._last_text = None
        self._last_color = None
        self._cached_surf = None

    def draw(self, surface, center_pos):
        text_string = (
            self.text_content() if callable(self.text_content) else self.text_content
        )
        current_color = self.pulser.get_color()

        # --- OPTIMIZATION: Only re-render if text or color changed significantly ---
        color_key = (current_color.r // 8, current_color.g // 8, current_color.b // 8)
        if text_string != self._last_text or color_key != self._last_color:
            self._cached_surf = self.font.render(
                text_string, True, current_color
            ).convert_alpha()
            self._last_text = text_string
            self._last_color = color_key

        text_rect = self._cached_surf.get_rect(center=center_pos)
        surface.blit(self._cached_surf, text_rect)


# These are LeftUISpecific effects
# they are for when consecutive
# guess are correct or when a correct
# letter guess is made they are x,y
# dependant so the letter location
# must be passed in


class FXManager:
    def __init__(self):
        self.fireworks = []
        self.fire_particles = []
        self.floating_scores = []

    def spawn_fireworks(self, x, y):
        for _ in range(150):
            angle = random.uniform(0, math.pi * 2)
            speed = random.uniform(100, 800)
            colors = [
                (255, 0, 0),
                (0, 255, 0),
                (0, 0, 255),
                (255, 215, 0),
                (255, 0, 255),
            ]
            self.fireworks.append(
                {
                    "x": x,
                    "y": y,
                    "vx": math.cos(angle) * speed,
                    "vy": math.sin(angle) * speed,
                    "life": random.uniform(1.0, 2.5),
                    "color": random.choice(colors),
                    "size": random.randint(2, 6),
                }
            )

    def spawn_fire(self, x, y, spread=100):
        self.fire_particles.append(
            {
                "x": x + random.uniform(-spread, spread),
                "y": y,
                "vx": random.uniform(-15, 15),
                "vy": random.uniform(-80, -150),
                "life": 1.0,
                "color": random.choice([(255, 100, 0), (255, 50, 0), (255, 200, 0)]),
            }
        )

    def spawn_floating_text(self, x, y, text, color, vy_range):
        self.floating_scores.append(
            {
                "x": x,
                "y": y,
                "vy": random.uniform(*vy_range),
                "alpha": 255.0,
                "text": text,
                "color": color,
            }
        )

    def update(self, dt):
        # --- OPTIMIZATION: List comprehension instead of removing during iteration ---
        for fw in self.fireworks:
            fw["x"] += fw["vx"] * dt
            fw["y"] += fw["vy"] * dt
            fw["vy"] += 300 * dt
            fw["life"] -= dt
        self.fireworks = [fw for fw in self.fireworks if fw["life"] > 0]

        for fp in self.fire_particles:
            fp["x"] += fp["vx"] * dt
            fp["y"] += fp["vy"] * dt
            fp["life"] -= dt * 1.5
        self.fire_particles = [fp for fp in self.fire_particles if fp["life"] > 0]

        for fs in self.floating_scores:
            fs["y"] -= fs["vy"] * dt
            fs["alpha"] -= 150 * dt
        self.floating_scores = [fs for fs in self.floating_scores if fs["alpha"] > 0]

    def draw_fireworks(self, surface):
        for fw in self.fireworks:
            fw_alpha = int(255 * min(1.0, fw["life"]))
            if fw_alpha > 0:
                fw_surf = pygame.Surface(
                    (fw["size"] * 2, fw["size"] * 2), pygame.SRCALPHA
                )
                pygame.draw.circle(
                    fw_surf,
                    (*fw["color"], fw_alpha),
                    (fw["size"], fw["size"]),
                    fw["size"],
                )
                surface.blit(fw_surf, (int(fw["x"]), int(fw["y"])))

    def draw_fire(self, surface):
        for fp in self.fire_particles:
            f_alpha = int(255 * fp["life"])
            if f_alpha > 0:
                f_surf = pygame.Surface((12, 12), pygame.SRCALPHA)
                pygame.draw.circle(
                    f_surf, (*fp["color"], f_alpha), (6, 6), random.randint(3, 6)
                )
                surface.blit(f_surf, (int(fp["x"]), int(fp["y"])))

    def draw_floating_text(self, surface, font):
        for fs in self.floating_scores:
            d_surf = font.render(fs["text"], True, fs["color"]).convert_alpha()
            d_surf.fill(
                (255, 255, 255, int(max(0, min(255, fs["alpha"])))),
                special_flags=pygame.BLEND_RGBA_MULT,
            )
            d_rect = d_surf.get_rect(center=(int(fs["x"]), int(fs["y"])))
            surface.blit(d_surf, d_rect)


# This is an effect for a win condition
# it rains gold $ signs


class GoldMatrixTransition:
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.font_size = 30
        self.font = FontManager.get("brunson", self.font_size)
        self.columns = self.width // self.font_size

        self.head_color = (255, 255, 200)
        self.tail_color = (255, 215, 0)

        # --- OPTIMIZATION: convert_alpha on pre-rendered assets ---
        self.head_image = self.font.render("$", True, self.head_color).convert_alpha()

        self.tail_length = 15
        self.tail_images = []
        for i in range(self.tail_length):
            alpha = int(255 * (1.0 - (i / self.tail_length)))
            img = self.font.render("$", True, self.tail_color).convert_alpha()

            # Swap set_alpha() for the BLEND_RGBA_MULT fix
            img.fill((255, 255, 255, alpha), special_flags=pygame.BLEND_RGBA_MULT)

            self.tail_images.append(img)

        # --- REFACTOR: Non-blocking state ---
        self.active = False
        self.start_time = 0
        self.duration_ms = 2000
        self.drops = []
        self.background = None

    def start(self, screen, duration_seconds=2.0):
        self.active = True
        self.duration_ms = duration_seconds * 1000
        self.start_time = pygame.time.get_ticks()
        self.drops = [random.randint(-30, -5) for _ in range(self.columns)]
        self.background = screen.copy()

    def update(self):
        if not self.active:
            return
        if pygame.time.get_ticks() - self.start_time > self.duration_ms:
            self.active = False
            return

        for i in range(self.columns):
            self.drops[i] += 1
            if self.drops[i] * self.font_size > self.height and random.random() > 0.8:
                self.drops[i] = random.randint(-5, 0)

    def draw(self, screen):
        if not self.active:
            return

        screen.blit(self.background, (0, 0))

        for i in range(self.columns):
            x = i * self.font_size
            head_y = self.drops[i]

            for j in range(self.tail_length):
                tail_y_pos = (head_y - j) * self.font_size
                if -self.font_size < tail_y_pos < self.height:
                    screen.blit(self.tail_images[j], (x, tail_y_pos))

            head_y_pos = head_y * self.font_size
            if -self.font_size < head_y_pos < self.height:
                screen.blit(self.head_image, (x, head_y_pos))
