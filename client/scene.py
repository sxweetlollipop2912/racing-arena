import pygame
import queue
from typing import List, Optional


class Scene:
    def __init__(self):
        pass

    def process_input(
        self, ui_events: List[pygame.event.Event], messages: queue.Queue
    ) -> Optional["Scene"]:
        pass

    def update(self, time_delta: float) -> None:
        pass

    def draw(self, screen: pygame.Surface) -> None:
        pass
