"""Отрисовка двух слоёв фона, игровых объектов и интерфейса."""

from math import cos, pi, sin
from pathlib import Path
from random import Random

import pygame

from game import (
    ASTEROID_RADII,
    EXPLOSION_LIFETIME,
    HEIGHT,
    WIDTH,
    Game,
)

# Изображения ищутся рядом с модулем, независимо от рабочей папки.
ASSETS = Path(__file__).parent / "assets"

# Скорость фонового слоя в пикселях в секунду и его непрозрачность.
BACKGROUND_SPEED = 27
BACKGROUND_OPACITY = 100
BACKGROUND_ROCKS = 54

# Каждая ячейка атласа содержит отдельный кадр анимации взрыва.
EXPLOSION_FRAMES = 12
EXPLOSION_TILE = 112

# Игровое поле справа от подсказок. Заставка в координатах поля.
FIELD = pygame.Rect(216, 8, WIDTH, HEIGHT)
WINDOW_SIZE = FIELD.right + 8, FIELD.bottom + 8
SPLASH = pygame.Rect(0, 0, 400, 300)
SPLASH.center = WIDTH // 2, HEIGHT // 2
START_AREA = SPLASH.move(FIELD.topleft)

# Цвета интерфейса.
WHITE = (239, 247, 255)
CYAN = (117, 224, 252)
HUD_GREEN = (70, 255, 53)
WINDOW_COLOR = (240, 240, 240)
SIDEBAR_TEXT = (36, 43, 55)
SIDEBAR_BORDER = (163, 170, 180)


def _ship_sprite(thrust: bool) -> pygame.Surface:
    """Нарисовать один из двух спрайтов корабля носом вправо."""
    surface = pygame.Surface((80, 80), pygame.SRCALPHA)
    if thrust:
        pygame.draw.polygon(
            surface, (49, 114, 242), [(5, 40), (27, 31), (36, 40), (27, 49)]
        )
        pygame.draw.polygon(
            surface, (101, 207, 255), [(12, 40), (31, 34), (35, 40), (31, 46)]
        )
        pygame.draw.polygon(
            surface, (231, 251, 255), [(22, 40), (32, 37), (32, 43)]
        )

    hull = [
        (64, 40),
        (44, 27),
        (27, 20),
        (33, 34),
        (33, 46),
        (27, 60),
        (44, 53),
    ]
    pygame.draw.polygon(surface, (167, 191, 215), hull)
    pygame.draw.polygon(
        surface,
        (66, 95, 128),
        [(64, 40), (49, 40), (33, 46), (27, 60), (44, 53)],
    )
    pygame.draw.polygon(surface, WHITE, hull, width=1)
    pygame.draw.polygon(
        surface,
        (19, 36, 60),
        [(57, 40), (44, 32), (34, 35), (34, 45), (44, 48)],
    )
    pygame.draw.polygon(
        surface, CYAN, [(56, 40), (45, 36), (38, 37), (38, 43), (45, 44)]
    )
    pygame.draw.line(surface, WHITE, (40, 38), (48, 38), width=2)
    pygame.draw.circle(surface, CYAN, (32, 27), 2)
    pygame.draw.circle(surface, CYAN, (32, 53), 2)
    return surface


def _rocket_sprite() -> pygame.Surface:
    """Нарисовать спрайт светящейся ракеты носом вправо."""
    surface = pygame.Surface((30, 16), pygame.SRCALPHA)
    pygame.draw.ellipse(surface, (255, 138, 65, 75), (1, 2, 28, 12))
    pygame.draw.polygon(
        surface,
        (255, 199, 100),
        [(2, 8), (14, 5), (24, 5), (29, 8), (24, 11), (14, 11)],
    )
    pygame.draw.line(surface, (255, 248, 215), (12, 8), (26, 8), width=3)
    return surface


def _blit_wrapped(
    destination: pygame.Surface,
    sprite: pygame.Surface,
    position: pygame.Vector2,
) -> None:
    """Дорисовать пересекающие край части спрайта с другой стороны поля."""
    rect = sprite.get_rect(center=(round(position.x), round(position.y)))
    destination.blit(sprite, rect)
    horizontal = (
        WIDTH if rect.left < 0 else -WIDTH if rect.right > WIDTH else 0
    )
    vertical = (
        HEIGHT if rect.top < 0 else -HEIGHT if rect.bottom > HEIGHT else 0
    )
    if horizontal:
        destination.blit(sprite, rect.move(horizontal, 0))
    if vertical:
        destination.blit(sprite, rect.move(0, vertical))
    if horizontal and vertical:
        destination.blit(sprite, rect.move(horizontal, vertical))


def _background_layer(asteroids: dict[int, pygame.Surface]) -> pygame.Surface:
    """Подготовить повторяемую полупрозрачную панораму мелких астероидов."""
    rng = Random(73)
    surface = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    for _ in range(BACKGROUND_ROCKS):
        point = pygame.Vector2(rng.randrange(WIDTH), rng.randrange(HEIGHT))
        sprite = asteroids[rng.choice(ASTEROID_RADII)]
        sprite = pygame.transform.rotozoom(
            sprite, rng.randrange(360), rng.uniform(0.06, 0.24)
        )
        _blit_wrapped(surface, sprite, point)
    surface.set_alpha(BACKGROUND_OPACITY)
    return surface


def _explosion_atlas() -> pygame.Surface:
    """Собрать полосу кадров с расширением вспышки и разлётом искр."""
    tile = EXPLOSION_TILE
    atlas = pygame.Surface((tile * EXPLOSION_FRAMES, tile), pygame.SRCALPHA)
    rng = Random(29)
    sparks = [(rng.uniform(0, 2 * pi), rng.uniform(21, 51)) for _ in range(26)]
    center = pygame.Vector2(tile // 2, tile // 2)
    for index in range(EXPLOSION_FRAMES):
        phase = index / EXPLOSION_FRAMES
        fade = 1 - phase
        frame = pygame.Surface((tile, tile), pygame.SRCALPHA)
        radius = int(11 + phase * 35)
        pygame.draw.circle(
            frame, (255, 107, 63, int(112 * fade)), center, radius, 2
        )
        pygame.draw.circle(
            frame, (255, 123, 45, int(140 * fade**2)), center, radius - 4
        )
        core = max(1, int(15 * fade))
        pygame.draw.circle(
            frame, (255, 222, 153, int(250 * fade**2)), center, core
        )
        for angle, distance in sparks:
            direction = pygame.Vector2(cos(angle), sin(angle))
            head = center + direction * distance * (0.25 + 0.75 * phase)
            tail = head - direction * (2 + 9 * fade)
            pygame.draw.line(
                frame, (255, 182, 91, int(245 * fade)), tail, head, 2
            )
        atlas.blit(frame, (index * tile, 0))
    return atlas


def _sidebar(font: pygame.font.Font) -> pygame.Surface:
    """Подготовить панель подсказок слева от игрового поля."""
    sidebar = pygame.Surface((FIELD.left - 12, HEIGHT)).convert()
    sidebar.fill(WINDOW_COLOR)
    width = sidebar.get_width() - 2
    top = HEIGHT * 2 // 3
    sections = (
        (
            "Управление",
            (
                ("W", "Разгон"),
                ("A", "Поворот влево"),
                ("D", "Поворот вправо"),
                ("Пробел", "Выстрел"),
            ),
        ),
        ("Старт", (("", "Щелчок по заставке"),)),
    )
    for title, rows in sections:
        height = 15 + 22 * len(rows)
        pygame.draw.rect(sidebar, SIDEBAR_BORDER, (1, top, width, height), 1)
        heading = font.render(title, True, SIDEBAR_TEXT, WINDOW_COLOR)
        sidebar.blit(heading, heading.get_rect(midleft=(10, top)))
        for y, (key, label) in enumerate(rows, start=1):
            row_top = top + 22 * y - 9
            if key:
                keycap = pygame.Rect(10, row_top - 2, 55, 18)
                pygame.draw.rect(sidebar, (226, 230, 236), keycap)
                pygame.draw.rect(sidebar, SIDEBAR_BORDER, keycap, 1)
                cap = font.render(key, True, SIDEBAR_TEXT)
                sidebar.blit(cap, cap.get_rect(center=keycap.center))
            text = font.render(label, True, SIDEBAR_TEXT)
            sidebar.blit(text, (73 if key else 10, row_top))
        top += height + 16
    return sidebar


class Renderer:
    """Рисовать окно по текущему состоянию игры."""

    def __init__(self, surface: pygame.Surface) -> None:
        """Загрузить фон и подготовить спрайты и шрифты."""
        self.window = surface
        self.surface = pygame.Surface((WIDTH, HEIGHT)).convert()
        self.background = pygame.image.load(ASSETS / "nebula.jpg").convert()
        asteroid = pygame.image.load(ASSETS / "asteroid.png").convert_alpha()
        self.asteroids = {
            radius: pygame.transform.smoothscale(asteroid, (2 * radius,) * 2)
            for radius in ASTEROID_RADII
        }
        self.layer = _background_layer(self.asteroids)
        self.layer_offset = 0.0
        self.ships = (_ship_sprite(False), _ship_sprite(True))
        self.rocket = _rocket_sprite()
        self.explosions = _explosion_atlas()
        self.hud = pygame.font.SysFont("arial,liberationsans", 27)
        self.title = pygame.font.Font(None, 62)
        self.title.set_italic(True)
        self.label = pygame.font.Font(None, 24)
        self.sidebar = _sidebar(pygame.font.Font(None, 17))
        self.panels = {
            (finished, hovered): self._splash_panel(finished, hovered)
            for finished in (False, True)
            for hovered in (False, True)
        }

    def draw(self, game: Game, elapsed: float, hovered: bool) -> None:
        """Нарисовать фон, активные объекты, взрывы, HUD и заставку."""
        self.layer_offset = (
            self.layer_offset + elapsed * BACKGROUND_SPEED
        ) % WIDTH
        offset = int(self.layer_offset)
        self.surface.blit(self.background, (0, 0))
        self.surface.blit(self.layer, (-offset, 0))
        self.surface.blit(self.layer, (WIDTH - offset, 0))

        if game.playing:
            for asteroid in game.asteroids:
                sprite = self.asteroids[asteroid.radius]
                sprite = pygame.transform.rotozoom(sprite, -asteroid.angle, 1)
                _blit_wrapped(self.surface, sprite, asteroid.position)
            for rocket in game.rockets:
                sprite = pygame.transform.rotozoom(
                    self.rocket, -rocket.angle, 1
                )
                _blit_wrapped(self.surface, sprite, rocket.position)
            ship = game.ship
            sprite = pygame.transform.rotozoom(
                self.ships[ship.thrust], -ship.angle, 1
            )
            _blit_wrapped(self.surface, sprite, ship.position)

        for explosion in game.explosions:
            index = int(explosion.age / EXPLOSION_LIFETIME * EXPLOSION_FRAMES)
            area = pygame.Rect(
                index * EXPLOSION_TILE, 0, EXPLOSION_TILE, EXPLOSION_TILE
            )
            size = round(explosion.radius * 2.6)
            frame = pygame.transform.smoothscale(
                self.explosions.subsurface(area), (size, size)
            )
            _blit_wrapped(self.surface, frame, explosion.position)

        self._draw_hud(game)
        if not game.playing:
            self.surface.blit(self.panels[game.finished, hovered], SPLASH)
        self.window.fill(WINDOW_COLOR)
        pygame.draw.rect(self.window, (52, 52, 55), FIELD.inflate(4, 4), 2)
        self.window.blit(self.sidebar, (6, FIELD.top))
        self.window.blit(self.surface, FIELD)

    def _draw_hud(self, game: Game) -> None:
        """Нарисовать постоянные индикаторы жизней и очков над полем."""
        for caption, alignment in (
            (f"Жизни: {game.lives}", {"topleft": (80, 0)}),
            (f"Счёт: {game.score}", {"topright": (WIDTH - 80, 0)}),
        ):
            text = self.hud.render(caption, True, HUD_GREEN)
            shadow = self.hud.render(caption, True, (0, 15, 0))
            rect = text.get_rect(**alignment)
            self.surface.blit(shadow, rect.move(1, 1))
            self.surface.blit(text, rect)

    def _splash_panel(self, finished: bool, hovered: bool) -> pygame.Surface:
        """Подготовить центральную панель запуска или повторной игры."""
        panel = pygame.Surface(SPLASH.size, pygame.SRCALPHA)
        center = SPLASH.width // 2
        panel.fill((15, 25, 77, 157 if hovered else 178))
        border = (105, 147, 255) if hovered else (51, 76, 163)
        pygame.draw.rect(panel, border, panel.get_rect(), 3)

        title = self.title.render("АСТЕРОИДЫ", True, WHITE)
        outline = self.title.render("АСТЕРОИДЫ", True, (40, 67, 146))
        rect = title.get_rect(center=(center, 131))
        for dx, dy in ((-3, 0), (3, 0), (0, -3), (0, 3), (2, 4)):
            panel.blit(outline, rect.move(dx, dy))
        panel.blit(title, rect)
        if finished:
            status = self.label.render("Раунд завершён", True, WHITE)
            panel.blit(status, status.get_rect(center=(center, 86)))

        action = "ИГРАТЬ СНОВА" if finished else "ЩЁЛКНИТЕ ДЛЯ СТАРТА"
        text = self.label.render(action, True, CYAN if hovered else WHITE)
        rect = text.get_rect(center=(center, 190))
        panel.blit(text, rect)
        for edge, delta in ((rect.left - 12, -24), (rect.right + 12, 24)):
            pygame.draw.line(
                panel, border, (edge, 190), (edge + delta, 190), 2
            )
        return panel
