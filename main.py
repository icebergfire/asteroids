"""Точка входа игры «Астероиды» и главный цикл Pygame."""

import pygame

from game import Game
from graphics import START_AREA, WINDOW_SIZE, Renderer

# Частота кадров, шаг физики и предел накопленного времени после задержки.
FRAME_RATE = 60
PHYSICS_STEP = 1 / 120
MAX_FRAME_TIME = 0.25

# Физические клавиши работают при любой активной раскладке.
CONTROLS = {
    pygame.KSCAN_A: pygame.K_a,
    pygame.KSCAN_D: pygame.K_d,
    pygame.KSCAN_W: pygame.K_w,
    pygame.KSCAN_SPACE: pygame.K_SPACE,
}


def run() -> None:
    """Открыть окно, обработать ввод и запустить игру."""
    pygame.display.set_caption("Астероиды")
    screen = pygame.display.set_mode(WINDOW_SIZE)
    renderer = Renderer(screen)
    game = Game()
    clock = pygame.time.Clock()
    accumulated = 0.0
    fire_queued = False
    held = set()

    while True:
        elapsed = min(clock.tick(FRAME_RATE) / 1000, MAX_FRAME_TIME)
        accumulated += elapsed
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return
            if event.type in (pygame.KEYDOWN, pygame.KEYUP):
                key = CONTROLS.get(getattr(event, "scancode", None), event.key)
                if event.type == pygame.KEYUP:
                    held.discard(key)
                    continue
                if key == pygame.K_ESCAPE:
                    return
                if key == pygame.K_SPACE and game.playing:
                    fire_queued = True
                held.add(key)
            if event.type == pygame.WINDOWFOCUSLOST:
                held.clear()
                fire_queued = False
            if (
                event.type == pygame.MOUSEBUTTONDOWN
                and event.button == 1
                and not game.playing
                and START_AREA.collidepoint(event.pos)
            ):
                game.start()
                accumulated = 0.0
                fire_queued = False

        turn = int(pygame.K_d in held) - int(pygame.K_a in held)
        while accumulated >= PHYSICS_STEP:
            fire = fire_queued or pygame.K_SPACE in held
            game.update(PHYSICS_STEP, turn, pygame.K_w in held, fire)
            accumulated -= PHYSICS_STEP
            fire_queued = False

        hovered = not game.playing and START_AREA.collidepoint(
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
