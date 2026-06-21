"""
emote.py
~~~~~~~~
Renders a highly expressive, interactive user interface icon utilizing
the custom RETROMOTICONS font family. Applies real-time squash, stretch,
breathing, and rotation matrices based on emotional context.
"""

import math
import random
import pygame
from src.effects import ColorPulser
from src.font_manager import FontManager

# Initialize Pygame
pygame.init()
WIDTH, HEIGHT = 600, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
clock = pygame.time.Clock()

EMOTIONS = {
    "Happy": "ABLNUbilop",
    "Sad": "CM",
    "Mad": "JXDfF",
    "Very Mad": "cdQP",
    "Bored": "aEGHRZSmn",
    "Scared": "VYegrs",
    "Dead": "h",
}


class Emote:
    def __init__(self, x, y):
        self.base_x = x
        self.base_y = y

        # --- FONT SETUP VIA MANAGER ---
        self.font = FontManager.get("retromoticons", 250)

        # Start with a random bored face
        self.current_face = "Bored"
        self.face = random.choice(EMOTIONS[self.current_face])
        self.color_pulser = ColorPulser((255, 215, 0), (255, 140, 0), speed=2.5)

        # --- JUMP & SQUASH/STRETCH VARIABLES ---
        self.scale_x = 1.0
        self.scale_y = 1.0
        self.y_offset = 0.0
        self.shake_timer = 0.0
        self.shake_intensity = 8.0
        self.shake_offset_x = 0.0
        self.shake_offset_y = 0.0

        # --- PERSONALITY TIMERS ---
        self.breath_timer = random.uniform(0, 10)

        self.look_x = 0.0
        self.look_y = 0.0

        self.blink_timer = random.uniform(2.0, 6.0)
        self.is_blinking = False
        self.blink_duration = 0.0

        # --- STATE MACHINE & ROTATION ---
        self.angle = 0.0
        self.state = "waiting"
        self.time_since_interaction = 0.0
        self.wait_timer = random.uniform(5, 10)
        self.target_angle = 0.0
        self.twitch_speed = 0.0

    def trigger_face_change(self, emotion_category=None):
        """Changes the face, triggers the jump with squash & stretch, and starts shaking."""
        if emotion_category is None:
            emotion_category = random.choice(list(EMOTIONS.keys()))

        self.current_face = emotion_category
        self.face = random.choice(EMOTIONS[self.current_face])

        # Trigger the jump (Squash & Stretch!)
        self.scale_x = 0.7
        self.scale_y = 1.6
        self.y_offset = -50.0
        self.shake_timer = 0.4

        self.reset_interaction()

    def reset_interaction(self):
        self.time_since_interaction = 0.0
        self.angle = 0.0
        self.state = "waiting"
        self.wait_timer = random.uniform(5, 15)

    def start_new_twitch(self):
        self.state = "twitching"
        direction = random.choice([-1, 1])
        self.target_angle = random.uniform(10, 20) * direction
        duration = random.uniform(2.0, 4.0)
        self.twitch_speed = self.target_angle / duration

    def update(self, dt):
        """Updates logic, timers, physics, and personality quirks."""
        self.time_since_interaction += dt

        # --- BREATH OF LIFE ---
        self.breath_timer += dt

        # --- MOUSE TRACKING ---
        mx, my = pygame.mouse.get_pos()
        dx = mx - self.base_x
        dy = my - self.base_y
        distance = math.hypot(dx, dy)

        max_look = 12.0
        if distance > 0:
            self.look_x = (dx / distance) * min(max_look, distance * 0.05)
            self.look_y = (dy / distance) * min(max_look, distance * 0.05)
        else:
            self.look_x, self.look_y = 0.0, 0.0

        # --- BLINKING LOGIC ---
        if self.is_blinking:
            self.blink_duration -= dt
            if self.blink_duration <= 0:
                self.is_blinking = False
                self.blink_timer = random.uniform(2.0, 6.0)
        else:
            self.blink_timer -= dt
            if self.blink_timer <= 0:
                self.is_blinking = True
                self.blink_duration = 0.15

        # 1. Handle Shake Effect
        if self.shake_timer > 0:
            self.shake_timer -= dt
            self.shake_offset_x = random.uniform(
                -self.shake_intensity, self.shake_intensity
            )
            self.shake_offset_y = random.uniform(
                -self.shake_intensity, self.shake_intensity
            )
        else:
            self.shake_offset_x = 0.0
            self.shake_offset_y = 0.0

        # 2. Handle Rotation States
        if self.time_since_interaction > 30.0:
            self.state = "spinning"
            self.angle += 120 * dt
            if self.angle >= 360:
                self.angle -= 360
        else:
            if self.state == "waiting":
                self.angle = 0
                self.wait_timer -= dt
                if self.wait_timer <= 0:
                    self.start_new_twitch()

            elif self.state == "twitching":
                self.angle += self.twitch_speed * dt
                reached_target = False
                if self.twitch_speed > 0 and self.angle >= self.target_angle:
                    reached_target = True
                elif self.twitch_speed < 0 and self.angle <= self.target_angle:
                    reached_target = True

                if reached_target:
                    self.angle = 0
                    self.state = "waiting"
                    self.wait_timer = random.uniform(5, 15)

        # 3. Handle Excite Jump (Lerp squash/stretch back to normal)
        self.scale_x += (1.0 - self.scale_x) * 12 * dt
        self.scale_y += (1.0 - self.scale_y) * 12 * dt

        if self.y_offset < 0:
            self.y_offset += (0 - self.y_offset) * 10 * dt
            if self.y_offset > -0.5:
                self.y_offset = 0

    def draw(self, surface):
        """Renders the emote with all modifiers applied."""
        current_color = self.color_pulser.get_color()

        # Render using the cached font from FontManager
        base_surf = self.font.render(self.face, True, current_color)
        base_size = base_surf.get_size()

        # Combine scale factors: Squash/Stretch * Breathing * Blinking
        breath_y = 1.0 + math.sin(self.breath_timer * 3.0) * 0.05
        blink_mod = 0.1 if self.is_blinking else 1.0

        scaled_width = int(base_size[0] * self.scale_x)
        scaled_height = int(base_size[1] * self.scale_y * breath_y * blink_mod)

        scaled_width = max(1, scaled_width)
        scaled_height = max(1, scaled_height)

        if scaled_width != base_size[0] or scaled_height != base_size[1]:
            current_surf = pygame.transform.smoothscale(
                base_surf, (scaled_width, scaled_height)
            )
        else:
            current_surf = base_surf

        # Apply rotation
        rotated_surf = pygame.transform.rotate(current_surf, self.angle)

        # Combine positions
        final_x = self.base_x + self.shake_offset_x + self.look_x
        final_y = self.base_y + self.y_offset + self.shake_offset_y + self.look_y

        rot_rect = rotated_surf.get_rect(center=(final_x, final_y))
        surface.blit(rotated_surf, rot_rect)


if __name__ == "__main__":
    my_emote = Emote(WIDTH // 2, HEIGHT // 2)

    running = True
    while running:
        dt = clock.tick(60) / 1000.0

        pygame.display.set_caption(
            f"Animated Emote | Current Emotion: {my_emote.current_face}"
        )

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_1:
                    my_emote.trigger_face_change("Happy")
                elif event.key == pygame.K_2:
                    my_emote.trigger_face_change("Sad")
                elif event.key == pygame.K_3:
                    my_emote.trigger_face_change("Mad")
                elif event.key == pygame.K_4:
                    my_emote.trigger_face_change("Very Mad")
                elif event.key == pygame.K_5:
                    my_emote.trigger_face_change("Bored")
                elif event.key == pygame.K_6:
                    my_emote.trigger_face_change("Scared")
                elif event.key == pygame.K_7:
                    my_emote.trigger_face_change("Dead")
                elif event.key == pygame.K_SPACE:
                    my_emote.trigger_face_change()
                else:
                    my_emote.reset_interaction()

            if event.type == pygame.MOUSEBUTTONDOWN:
                my_emote.reset_interaction()

        screen.fill((40, 40, 45))

        my_emote.update(dt)
        my_emote.draw(screen)

        pygame.display.flip()

    pygame.quit()
