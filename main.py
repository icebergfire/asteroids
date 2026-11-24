"""Точка входа игры «Астероиды» и главный цикл Pygame."""

import pygame

from game import HEIGHT, WIDTH, Game
from graphics import SPLASH, Renderer

# Частота кадров, шаг физики и предел накопленного времени после задержки.
FRAME_RATE = 60
PHYSICS_STEP = 1 / 120
MAX_FRAME_TIME = 0.25


def run() -> None:
    """Открыть окно, обработать ввод и запустить игру."""
    pygame.display.set_caption("Астероиды")
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    renderer = Renderer(screen)
    game = Game()
    clock = pygame.time.Clock()
    accumulated = 0.0
    fire_queued = False

    while True:
        elapsed = min(clock.tick(FRAME_RATE) / 1000, MAX_FRAME_TIME)
        accumulated += elapsed
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return
                if event.key == pygame.K_SPACE and game.playing:
                    fire_queued = True
            if (
                event.type == pygame.MOUSEBUTTONDOWN
                and event.button == 1
                and not game.playing
                and SPLASH.collidepoint(event.pos)
            ):
                game.start()
                accumulated = 0.0
                fire_queued = False

        keys = pygame.key.get_pressed()
        turn = int(keys[pygame.K_RIGHT]) - int(keys[pygame.K_LEFT])
        while accumulated >= PHYSICS_STEP:
            fire = fire_queued or keys[pygame.K_SPACE]
            game.update(PHYSICS_STEP, turn, keys[pygame.K_UP], fire)
            accumulated -= PHYSICS_STEP
            fire_queued = False

        hovered = not game.playing and SPLASH.collidepoint(
            pygame.mouse.get_pos()
        )
        renderer.draw(game, elapsed, hovered)
        pygame.display.flip()


def main() -> None:
    """Подготовить Pygame и закрыть его при выходе из игры."""
    pygame.display.init()
    pygame.font.init()
    try:
        run()
    finally:
        pygame.quit()


if __name__ == "__main__":
    main()
