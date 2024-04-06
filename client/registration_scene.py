import pygame
import pygame_gui
import asyncio
import queue
from typing import List, Optional

from globals import SCREEN_SIZE, LOGGER, current_nickname
from lobby_scene import LobbyScene
from scene import Scene
from connection_manager import ConnectionManager

connection = ConnectionManager()


class RegistrationScene(Scene):
    def __init__(self):
        super().__init__()

        self.manager = pygame_gui.UIManager(SCREEN_SIZE)

        # Create a font object
        self.font = pygame.font.Font(None, 50)  # Use the default font and a size of 50

        # Title
        self.title_text = self.font.render(
            "Racing Game", True, (0, 255, 255)
        )  # Cyan color

        # Username label
        self.username_label_text = self.font.render(
            "Username", True, (0, 255, 255)
        )  # Cyan color

        # Username input
        self.text_entry = pygame_gui.elements.UITextEntryLine(
            relative_rect=pygame.Rect((200, 300), (400, 50)),
            manager=self.manager,
        )

        # Submit button
        self.button_submit = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect((350, 400), (100, 50)),
            text="Submit",
            manager=self.manager,
        )

        # Error message
        self.error_message = self.font.render("", True, (255, 0, 0))

    def process_input(
        self, ui_events: List[pygame.event.Event], messages: queue.Queue
    ) -> Optional[Scene]:
        for event in ui_events:
            self.manager.process_events(event)
            if event.type == pygame.USEREVENT:
                if event.user_type == pygame_gui.UI_BUTTON_PRESSED:
                    if event.ui_element == self.button_submit:
                        username = self.text_entry.get_text()
                        current_nickname = username
                        LOGGER.info(
                            f"[UI Thread] [Registration] Username input: {username}"
                        )
                        if not all(char.isalnum() or char == "_" for char in username):
                            self.error_message = self.font.render(
                                "Username can only contain alphanumeric characters and underscores.",
                                True,
                                (255, 0, 0),
                            )
                            return None
                        elif len(username) > 10:
                            self.error_message = self.font.render(
                                "Username cannot be longer than 10 characters.",
                                True,
                                (255, 0, 0),
                            )
                            return None
                        elif len(username) == 0:
                            self.error_message = self.font.render(
                                "Username cannot be empty.", True, (255, 0, 0)
                            )
                            return None
                        else:
                            asyncio.run(connection.send_registration(username))

        while not messages.empty():
            command, *args = messages.get()
            if command == "REGISTRATION_SUCCESS":
                # TODO: Send to LobbyScene the list of current players in lobby
                return LobbyScene()
            elif command == "REGISTRATION_FAILURE":
                current_nickname = None
                self.error_message = self.font.render(args[0], True, (255, 0, 0))

    def update(self, time_delta: float) -> None:
        self.manager.update(time_delta)

    def draw(self, screen: pygame.Surface) -> None:
        screen.fill((0, 0, 50))  # Dark blue background
        screen.blit(self.title_text, (200, 50))  # Draw the title
        screen.blit(self.username_label_text, (200, 200))  # Draw the username label
        screen.blit(self.error_message, (200, 500))  # Draw the error message
        self.manager.draw_ui(screen)
