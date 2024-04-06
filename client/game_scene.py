import pygame
import queue
from typing import List, Optional

from scene import Scene


class GameScene(Scene):
    def __init__(self):
        super().__init__()

    def process_input(
        self, ui_events: List[pygame.event.Event], messages: queue.Queue
    ) -> Optional[Scene]:
        for event in ui_events:
            pass

    def update(self, time_delta: float) -> None:
        pass

    def draw(self, screen: pygame.Surface) -> None:
        screen.fill((0, 0, 0))
        font = pygame.font.Font(None, 36)
        text = font.render("Welcome to the Game!", True, (255, 255, 255))
        text_rect = text.get_rect(center=(800 / 2, 600 / 2))
        screen.blit(text, text_rect)
        pass
