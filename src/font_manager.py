"""
font_manager.py
~~~~~~~~~~~~~~~
Manages game font loading, custom TTF mappings, and caching to avoid
redundant disk reads across platforms.
"""

import pygame
from src.constants import get_resource_path


class FontManager:
    _cache = {}

    _FONT_DIR = get_resource_path("assets/fonts")

    PATHS = {
        "capitolcity": _FONT_DIR / "capitolcity.ttf",
        "portraits": _FONT_DIR / "PortraitsDeFemmesRegular-yYmxM.ttf",
        "bricks": _FONT_DIR / "BricksAndWires.ttf",
        "doodles": _FONT_DIR / "Doodles.ttf",
        "led_display": _FONT_DIR / "The Led Display St.ttf",
        "skittled": _FONT_DIR / "Skittled.ttf",
        "bank_gothic": _FONT_DIR / "BankGothic.ttf",
        "typewriter": _FONT_DIR / "JMH_Typewriter.ttf",
        "retromoticons": _FONT_DIR / "Retromoticons.ttf",
        "brunson": _FONT_DIR / "Brunson.ttf",
    }

    @classmethod
    def get(cls, name, size):
        if not pygame.font.get_init():
            pygame.font.init()

        key = (name, size)
        if key not in cls._cache:
            path = cls.PATHS.get(name)
            # Check if the path exists on disk
            if path and path.exists():
                # Convert Path object to string format for Pygame's font loader
                cls._cache[key] = pygame.font.Font(str(path), size)
            else:
                if path:
                    print(
                        f"Warning: Font file not found at {path}. Falling back to default."
                    )
                cls._cache[key] = pygame.font.Font(None, size)
        return cls._cache[key]
