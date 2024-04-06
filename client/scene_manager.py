import pygame
from typing import List

from connection_manager import ConnectionManager
from scene import Scene

connection = ConnectionManager()


class SceneManager:
    def __init__(self, initial_scene: Scene):
        self.current_scene = initial_scene

    def process_input(self, ui_events: List[pygame.event.Event]) -> None:
        new_scene = self.current_scene.process_input(ui_events, connection.messages)
        if new_scene is not None:
            self.current_scene = new_scene

    def update(self, time_delta: float) -> None:
        self.current_scene.update(time_delta)

    def draw(self, screen: pygame.Surface) -> None:
        self.current_scene.draw(screen)
