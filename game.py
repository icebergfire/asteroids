"""Модель игрового поля, объектов и столкновений."""

from dataclasses import dataclass
from random import Random

from pygame.math import Vector2

# Размер тороидального поля в пикселях.
WIDTH = 800
HEIGHT = 600

# Число жизней на заставке и в начале каждого раунда.
START_LIVES = 3

# Размер и параметры движения корабля в пикселях и секундах.
SHIP_RADIUS = 17
SHIP_NOSE = 24
SHIP_TURN_SPEED = 235  # Градусов в секунду.
SHIP_ACCELERATION = 320
SHIP_MAX_SPEED = 345
SHIP_DRAG = 106

# Скорость и время полёта задают дальность, меньшую короткой стороны поля.
ROCKET_RADIUS = 4
ROCKET_SPEED = 580
ROCKET_LIFETIME = 0.86
SHOT_INTERVAL = 0.19

# Период появления астероидов, разброс размеров и скоростей.
SPAWN_INTERVAL = 0.8
SPAWN_CLEARANCE = 136
ASTEROID_RADII = (26, 32, 38, 44)
ASTEROID_SPEED_RANGE = (42, 125)
ASTEROID_SPIN_LIMIT = 125  # Градусов в секунду.

# Длительность покадрового взрыва.
EXPLOSION_LIFETIME = 0.48


def wrap(point: Vector2) -> Vector2:
    """Перенести координату через край поля с сохранением остатка пути."""
    return Vector2(point.x % WIDTH, point.y % HEIGHT)


def torus_distance_sq(first: Vector2, second: Vector2) -> float:
    """Вернуть квадрат кратчайшего расстояния между точками на торе."""
    dx = abs(first.x - second.x) % WIDTH
    dy = abs(first.y - second.y) % HEIGHT
    # По каждой оси сравниваем прямой путь с путём через склейку краёв.
    dx = min(dx, WIDTH - dx)
    dy = min(dy, HEIGHT - dy)
    return dx * dx + dy * dy


@dataclass
class Body:
    """Движущийся объект с круглой областью столкновения."""

    position: Vector2
    velocity: Vector2
    angle: float
    radius: int
    spin: float = 0.0

    def move(self, dt: float) -> None:
        """Передвинуть и повернуть объект за dt секунд."""
        self.position = wrap(self.position + self.velocity * dt)
        self.angle = (self.angle + self.spin * dt) % 360

    def overlaps(self, other: "Body") -> bool:
        """Проверить, соприкасаются ли окружности двух объектов."""
        radius_sum = self.radius + other.radius
        return (
            torus_distance_sq(self.position, other.position) <= radius_sum**2
        )


class Ship(Body):
    """Корабль игрока с тягой, вращением и сопротивлением среды."""

    def __init__(self) -> None:
        """Создать неподвижный корабль в центре поля носом вверх."""
        super().__init__(
            Vector2(WIDTH / 2, HEIGHT / 2), Vector2(), -90, SHIP_RADIUS
        )
        self.thrust = False

    def forward(self) -> Vector2:
        """Вернуть единичный вектор по направлению носа."""
        return Vector2(1, 0).rotate(self.angle)

    def steer(self, dt: float, turn: int, thrust: bool) -> None:
        """Обновить направление, тягу и положение корабля."""
        self.spin = turn * SHIP_TURN_SPEED
        self.thrust = thrust
        if thrust:
            direction = Vector2(1, 0).rotate(self.angle + self.spin * dt / 2)
            self.velocity += direction * SHIP_ACCELERATION * dt
            if self.velocity.length_squared() > SHIP_MAX_SPEED**2:
                self.velocity.scale_to_length(SHIP_MAX_SPEED)
        elif self.velocity.length_squared():
            speed = max(0.0, self.velocity.length() - SHIP_DRAG * dt)
            self.velocity.scale_to_length(speed)
        self.move(dt)


@dataclass
class Rocket(Body):
    """Ракета с постоянной скоростью и ограниченным временем полёта."""

    remaining: float = ROCKET_LIFETIME


@dataclass
class Explosion:
    """Неподвижная анимация в точке уничтожения астероида."""

    position: Vector2
    radius: int
    age: float = 0.0


class Game:
    """Управлять раундом, счётом, жизнями и игровыми объектами."""

    def __init__(self) -> None:
        """Подготовить начальную заставку и счётчики."""
        self.random = Random()
        self.ship = Ship()
        self.asteroids: list[Body] = []
        self.rockets: list[Rocket] = []
        self.explosions: list[Explosion] = []
        self.playing = False
        self.finished = False
        self.lives = START_LIVES
        self.score = 0
        self.spawn_in = SPAWN_INTERVAL
        self.shot_in = 0.0

    def start(self) -> None:
        """Начать новый раунд со стартовым кораблём и счётчиками."""
        self.ship = Ship()
        self.asteroids.clear()
        self.rockets.clear()
        self.explosions.clear()
        self.playing = True
        self.finished = False
        self.lives = START_LIVES
        self.score = 0
        self.spawn_in = SPAWN_INTERVAL
        self.shot_in = 0.0

    def update(self, dt: float, turn: int, thrust: bool, fire: bool) -> None:
        """Продвинуть игру на один шаг отрисовки или симуляции."""
        for explosion in self.explosions:
            explosion.age += dt
        self.explosions = [
            item for item in self.explosions if item.age < EXPLOSION_LIFETIME
        ]
        if not self.playing:
            return

        self.ship.steer(dt, turn, thrust)
        self.shot_in = max(0.0, self.shot_in - dt)
        self.spawn_in -= dt
        while self.spawn_in <= 0:
            self._spawn_asteroid()
            self.spawn_in += SPAWN_INTERVAL

        for asteroid in self.asteroids:
            asteroid.move(dt)
        for rocket in self.rockets:
            rocket.move(min(dt, rocket.remaining))
            rocket.remaining -= dt
        self.rockets = [
            rocket for rocket in self.rockets if rocket.remaining > 0
        ]

        if fire and self.shot_in <= 0:
            self._fire()
        self._rocket_hits()
        self._ship_hit()

    def _spawn_asteroid(self) -> None:
        """Добавить астероид в случайной точке вне зоны корабля."""
        position = Vector2(
            self.random.uniform(0, WIDTH), self.random.uniform(0, HEIGHT)
        )
        while (
            torus_distance_sq(self.ship.position, position)
            < SPAWN_CLEARANCE**2
        ):
            position.update(
                self.random.uniform(0, WIDTH), self.random.uniform(0, HEIGHT)
            )
        velocity = Vector2(self.random.uniform(*ASTEROID_SPEED_RANGE), 0)
        velocity.rotate_ip(self.random.uniform(0, 360))
        self.asteroids.append(
            Body(
                position,
                velocity,
                self.random.uniform(0, 360),
                self.random.choice(ASTEROID_RADII),
                self.random.uniform(-ASTEROID_SPIN_LIMIT, ASTEROID_SPIN_LIMIT),
            )
        )

    def _fire(self) -> None:
        """Выпустить ракету из носа с собственной постоянной скоростью."""
        direction = self.ship.forward()
        position = wrap(self.ship.position + direction * SHIP_NOSE)
        self.rockets.append(
            Rocket(
                position,
                direction * ROCKET_SPEED,
                self.ship.angle,
                ROCKET_RADIUS,
            )
        )
        self.shot_in = SHOT_INTERVAL

    def _explode(self, asteroid: Body) -> None:
        """Убрать астероид и оставить взрыв на его месте."""
        self.asteroids.remove(asteroid)
        self.explosions.append(Explosion(asteroid.position, asteroid.radius))

    def _rocket_hits(self) -> None:
        """Уничтожить каждую попавшую ракету и начислить очко за её цель."""
        for rocket in self.rockets[:]:
            for asteroid in self.asteroids:
                if rocket.overlaps(asteroid):
                    self._explode(asteroid)
                    self.rockets.remove(rocket)
                    self.score += 1
                    break

    def _ship_hit(self) -> None:
        """Обработать одно столкновение корабля с астероидом за шаг."""
        for asteroid in self.asteroids:
            if not self.ship.overlaps(asteroid):
                continue
            self._explode(asteroid)
            # По условию проверяем остаток жизней до его уменьшения.
            if self.lives == 0:
                self.playing = False
                self.finished = True
                self.asteroids.clear()
                self.rockets.clear()
            else:
                self.lives -= 1
                self.ship = Ship()
            return
