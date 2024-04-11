import asyncio
import pygame
import threading
import queue
from typing import Tuple, List, Optional

from registration_scene import RegistrationScene
from scene_manager import SceneManager
from globals import SCREEN_SIZE, LOGGER
from connection_manager import ConnectionManager

connection = ConnectionManager()


def game_loop() -> None:
    pygame.init()
    screen: pygame.Surface = pygame.display.set_mode(SCREEN_SIZE)
    clock: pygame.time.Clock = pygame.time.Clock()
    scene_manager: SceneManager = SceneManager(RegistrationScene())

    while True:
        ui_events: List[pygame.event.Event] = pygame.event.get()

        for event in ui_events:
            if event.type == pygame.QUIT:
                pygame.quit()
                return

        scene_manager.process_input(ui_events)
        scene_manager.update(clock.tick(60) / 1000.0)
        scene_manager.draw(screen)

        pygame.display.flip()


loop = asyncio.new_event_loop()
asyncio.run_coroutine_threadsafe(
    connection.handle_conversation("localhost", 54321), loop
)
game_thread = threading.Thread(target=loop.run_forever)
game_thread.start()

game_loop()
