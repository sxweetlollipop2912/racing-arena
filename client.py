import asyncio
import pygame
import pygame_gui
import logging
import threading
import queue
from typing import Tuple, List, Dict, Optional

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(message)s",
    datefmt="%m/%d/%Y %H:%M:%S",
)
LOGGER = logging.getLogger(__name__)

SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
SCREEN_SIZE = (SCREEN_WIDTH, SCREEN_HEIGHT)

current_nickname = ""


class Player:
    def __init__(self, nickname: str):
        self.nickname: str = nickname
        self.diff_points: int = 0
        self.position: int = 1
        self.is_ready: bool = False
        self.is_disqualified: bool = False


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


class LobbyScene(Scene):
    def __init__(self):
        super().__init__()
        self.players: List[Player] = [
            Player("Player 1"),
            Player("Player 2"),
            Player("Player 3"),
            Player("Player 4"),
            Player("Player 5"),
            Player("Player 6"),
            Player("Player 7"),
            Player("Player 8"),
            Player("Player 9"),
            Player("Player 10"),
        ]
        self.players[1].is_ready = True
        self.manager = pygame_gui.UIManager((800, 600))
        self.button_submit = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect((330, 510), (120, 80)),
            text="Ready",
            manager=self.manager,
        )

    def process_input(
        self, events: List[pygame.event.Event], messages: queue.Queue
    ) -> Optional[Scene]:
        for event in events:
            self.manager.process_events(event)
            if event.type == pygame.QUIT:
                pygame.quit()
                return
            return self
        # def check_gamestart(self):

        # def starting_game(self):
        return self

    def update(self, time_delta: float):
        self.manager.update(time_delta)

    def draw(self, screen: pygame.Surface):
        screen.fill((0, 0, 50))
        font = pygame.font.Font(None, 36)
        text = font.render("Waiting for other players...", True, (255, 255, 255))
        text_rect = text.get_rect(center=(800 / 2, 50))
        screen.blit(text, text_rect)

        # draw a rectangle for player list
        player_font = pygame.font.Font(None, 30)
        pygame.draw.rect(screen, (204, 255, 255), (50, 100, 700, 400))
        for i in range(0, len(self.players)):
            player = self.players[i]
            player_name = player_font.render(player.nickname, True, (0, 0, 0))
            player_name_rect = player_name.get_rect(topleft=(70, 120 + 38 * i))
            if player.is_ready:
                player_status = player_font.render("Ready", True, (0, 255, 0))
            else:
                player_status = player_font.render("Not Ready", True, (255, 0, 0))
            player_status_rect = player_status.get_rect(topleft=(630, 120 + 38 * i))
            screen.blit(player_name, player_name_rect)
            screen.blit(player_status, player_status_rect)

        self.manager.draw_ui(screen)


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


class ConnectionManager:
    def __init__(self):
        self.writer: Optional[asyncio.StreamWriter] = None
        self.messages: queue.Queue = queue.Queue()

    async def write_to_server(self, message: str) -> None:
        byte_message: bytes = (message + "\n").encode()
        self.writer.write(byte_message)
        await self.writer.drain()

    async def send_ready_signal(self, nickname: str) -> None:
        LOGGER.info("[Connection Thread] Sending READY signal to server.")
        await self.write_to_server("READY")

    async def send_unready_signal(self, nickname: str) -> None:
        LOGGER.info("[Connection Thread] Sending UNREADY signal to server.")
        await self.write_to_server("UNREADY")

    async def send_answer(self, answer: int) -> None:
        LOGGER.info(f"[Connection Thread] Sending answer to server: {answer}")
        await self.write_to_server(f"ANSWER;{answer}")

    async def send_registration(self, nickname: str) -> None:
        LOGGER.info(
            f"[Connection Thread] Sending REGISTER signal to server: {nickname}"
        )
        await self.write_to_server(f"REGISTER;{nickname}")

    async def handle_conversation(self, host: str, port: int) -> None:
        try:
            reader, writer = await asyncio.open_connection(host, port)
            self.writer = writer

            address: Tuple[str, int] = writer.get_extra_info("peername")
            LOGGER.info(f"[Connection Thread] Accepted connection from {address}.")
            while True:
                data: bytes = await reader.readline()
                if not data:
                    break
                message: str = data.decode().strip()
                LOGGER.info(
                    f"[Connection Thread] Received message from {address}: {message}"
                )

                command: str
                args: List[str]
                command, *args = message.split(";")
                command = command.upper()
                self.messages.put((command, args))

                LOGGER.info(
                    f"[Connection Thread] Received message from {address}: {message}"
                )

        except ConnectionResetError:
            LOGGER.info(
                f"[Connection Thread] Connection reset by peer, address {address}."
            )
        finally:
            self.writer = None
            writer.close()


game_thread = threading.Thread(target=game_loop)
game_thread.start()

connection = ConnectionManager()
asyncio.run(connection.handle_conversation("localhost", 54321))
