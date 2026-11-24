"""Отрисовка двух слоёв фона, игровых объектов и интерфейса."""

from math import cos, pi, sin
from pathlib import Path
from random import Random

import pygame

from game import (
    ASTEROID_RADII,
    EXPLOSION_LIFETIME,
    HEIGHT,
    START_LIVES,
    WIDTH,
    Game,
)

# Изображения ищутся рядом с модулем, независимо от рабочей папки.
ASSETS = Path(__file__).parent / "assets"

# Скорость фонового слоя в пикселях в секунду и его непрозрачность.
BACKGROUND_SPEED = 27
BACKGROUND_OPACITY = 90
BACKGROUND_ROCKS = 30

# Каждая ячейка атласа содержит отдельный кадр анимации взрыва.
EXPLOSION_FRAMES = 12
EXPLOSION_TILE = 112

# Заставка находится в центре. Её прямоугольник служит областью клика.
SPLASH = pygame.Rect(0, 0, 506, 336)
SPLASH.center = WIDTH // 2, HEIGHT // 2

# Цвета интерфейса.
WHITE = (239, 247, 255)
TEXT_SECONDARY = (177, 197, 223)
CYAN = (117, 224, 252)
LINE = (53, 76, 106)
DARK = (9, 18, 34)


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


def _control_legend(font: pygame.font.Font) -> pygame.Surface:
    """Подписать клавиши управления, рисуя стрелки независимо от шрифта."""
    legend = pygame.Surface((364, 26), pygame.SRCALPHA)
    for x, angle in ((2, 180), (28, 0), (151, -90)):
        pygame.draw.rect(legend, LINE, (x, 2, 23, 22), 1, 4)
        center = pygame.Vector2(x + 11, 13)
        tail = center + pygame.Vector2(-5, 0).rotate(angle)
        tip = center + pygame.Vector2(5, 0).rotate(angle)
        wing_top = center + pygame.Vector2(1, -4).rotate(angle)
        wing_bottom = center + pygame.Vector2(1, 4).rotate(angle)
        pygame.draw.aaline(legend, CYAN, tail, tip)
        pygame.draw.aalines(legend, CYAN, False, (wing_top, tip, wing_bottom))

    pygame.draw.rect(legend, LINE, (227, 2, 80, 22), 1, 4)
    for x, label in (
        (58, "Поворот"),
        (181, "Тяга"),
        (235, "Пробел"),
        (315, "Огонь"),
    ):
        text = font.render(label, True, TEXT_SECONDARY)
        legend.blit(text, text.get_rect(midleft=(x, 13)))
    return legend


class Renderer:
    """Рисовать окно по текущему состоянию игры."""

    def __init__(self, surface: pygame.Surface) -> None:
        """Загрузить фон и подготовить спрайты и шрифты."""
        self.surface = surface
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
        self.label = pygame.font.Font(None, 23)
        self.value = pygame.font.Font(None, 34)
        self.title = pygame.font.Font(None, 68)
        self.button = pygame.font.Font(None, 29)
        self.hud = pygame.Surface((WIDTH, 84), pygame.SRCALPHA)
        for y in range(self.hud.get_height()):
            opacity = round(170 * (1 - y / self.hud.get_height()))
            pygame.draw.line(self.hud, (*DARK, opacity), (0, y), (WIDTH, y))
        self.controls = _control_legend(self.label)
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

    def _draw_hud(self, game: Game) -> None:
        """Нарисовать постоянные индикаторы жизней и очков над полем."""
        self.surface.blit(self.hud, (0, 0))
        lives = self.label.render("ЖИЗНИ", True, TEXT_SECONDARY)
        score = self.label.render("ОЧКИ", True, TEXT_SECONDARY)
        life_value = self.value.render(str(game.lives), True, WHITE)
        score_value = self.value.render(str(game.score), True, WHITE)
        self.surface.blit(lives, (27, 12))
        self.surface.blit(life_value, (27, 33))
        self.surface.blit(score, score.get_rect(topright=(WIDTH - 27, 12)))
        self.surface.blit(
            score_value, score_value.get_rect(topright=(WIDTH - 27, 33))
        )

        for index in range(START_LIVES):
            x = 63 + index * 19
            points = [(x, 39), (x - 6, 53), (x, 50), (x + 6, 53)]
            color = CYAN if index < game.lives else LINE
            pygame.draw.polygon(self.surface, color, points)

    def _splash_panel(self, finished: bool, hovered: bool) -> pygame.Surface:
        """Подготовить центральную панель запуска или повторной игры."""
        panel = pygame.Surface(SPLASH.size, pygame.SRCALPHA)
        center = SPLASH.width // 2
        opacity = 208 if finished else 240
        pygame.draw.rect(
            panel, (*DARK, opacity), panel.get_rect(), border_radius=20
        )
        pygame.draw.rect(
            panel, CYAN if hovered else LINE, panel.get_rect(), 1, 20
        )
        emblem = pygame.transform.rotozoom(self.asteroids[26], 20, 0.66)
        orbit = pygame.Rect(0, 0, 56, 48)
        orbit.center = center, 61
        pygame.draw.arc(panel, CYAN, orbit, 0.1, 2.4, 2)
        pygame.draw.arc(panel, CYAN, orbit, 3.0, 5.3, 2)
        panel.blit(emblem, emblem.get_rect(center=(center, 61)))

        title = self.title.render("Астероиды", True, WHITE)
        panel.blit(title, title.get_rect(center=(center, 126)))
        legend = (
            self.label.render("Раунд завершён", True, TEXT_SECONDARY)
            if finished
            else self.controls
        )
        panel.blit(legend, legend.get_rect(center=(center, 179)))

        rect = pygame.Rect(0, 0, 244, 52)
        rect.center = center, 248
        pygame.draw.rect(
            panel, (172, 239, 255) if hovered else CYAN, rect, border_radius=9
        )
        action = "Играть снова" if finished else "Начать игру"
        text = self.button.render(action, True, DARK)
        panel.blit(text, text.get_rect(center=rect.center))
        return panel
