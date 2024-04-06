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

        self.background = pygame.image.load("client/assets/wallpaper-2.jpg")
        # Create a font object

        self.title_font = pygame.font.Font("client/assets/Poppins-Regular.ttf", 72)
        self.title_font.set_bold(False)
        self.body_font = pygame.font.Font("client/assets/Poppins-Regular.ttf", 20)
        self.body_font.set_bold(False)

        # Title
        self.title_text = self.title_font.render(
            "Racing Game", True, (200, 200, 200)
        )  # Cyan color

        # Username label
        self.username_text = self.body_font.render(
            "Register Username", True, (255, 255, 255), (0, 0, 0)
        )  # Cyan color

        # Username input
        self.text_entry = pygame_gui.elements.UITextEntryLine(
            relative_rect=pygame.Rect((170, 515), (300, 50)),
            manager=self.manager,
        )

        # Get the size of the screen
        screen_width, screen_height = pygame.display.get_surface().get_size()

        # Error message
        self.error_message = self.body_font.render("", True, (200, 0, 0))

        # Create the button
        self.button_submit = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect((470, 515), (150, 50)),
            text="Submit",
            manager=self.manager,
        )

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
                            self.error_message = self.body_font.render(
                                "Username can only contain alphanumeric characters and underscores.",
                                False,
                                (200, 0, 0),
                            )
                            return None
                        elif len(username) > 10:
                            self.error_message = self.body_font.render(
                                "Username cannot be longer than 10 characters.",
                                False,
                                (200, 0, 0),
                            )
                            return None
                        elif len(username) == 0:
                            self.error_message = self.body_font.render(
                                "Username cannot be empty.", False, (200, 0, 0)
                            )
                            return None
                        else:
                            loop = asyncio.new_event_loop()
                            loop.run_until_complete(connection.send_registration(username))

        while not messages.empty():
            command, *args = messages.get()
            if command == "REGISTRATION_SUCCESS":
                # TODO: Send to LobbyScene the list of current players in lobby
                return LobbyScene()
            elif command == "REGISTRATION_FAILURE":
                current_nickname = None
                self.error_message = self.body_font.render(args[0], True, (200, 0, 0))

    def update(self, time_delta: float) -> None:
        self.manager.update(time_delta)

    def draw(self, screen: pygame.Surface) -> None:
        screen.blit(self.background, (0, 0))
        # Get the size of the screen
        screen_width, screen_height = pygame.display.get_surface().get_size()

        # Calculate the position of the title
        title_width, title_height = self.title_text.get_size()
        title_x = (screen_width - title_width) / 2
        title_y = (screen_height - title_height) / 2

        # Draw the title
        screen.blit(self.title_text, (title_x, 330))

        # Draw the username_text
        screen.blit(self.username_text, (170, 480))  # Draw the username label
        screen.blit(self.error_message, (175, 565))  # Draw the error message
        self.manager.draw_ui(screen)
