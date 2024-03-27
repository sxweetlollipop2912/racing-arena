import socket
import json


class Client:
    def __init__(self, server_host: str, server_port: int):
        self.server_host = server_host
        self.server_port = server_port
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.nickname = None

    def connect_to_server(self):
        self.socket.connect((self.server_host, self.server_port))

    def register_nickname(self, nickname: str) -> bool:
        self.nickname = nickname
        self.socket.send(json.dumps({"name": self.nickname}).encode())
        response = self.socket.recv(1024)
        return response.decode()

    def receive_question(self):
        data = self.socket.recv(1024)
        return json.loads(data.decode())

    def send_answer(self, answer: int):
        self.socket.send(json.dumps({"type": "answer", "answer": answer}).encode())

    def receive_game_update(self):
        data = self.socket.recv(1024)
        return json.loads(data.decode())

    def disconnect(self):
        self.socket.close()


import pygame
import pygame_gui


# Scene classes
class Scene:
    def __init__(self):
        pass

    def process_input(self, events):
        pass

    def update(self, time_delta):
        pass

    def draw(self, screen):
        pass


class TitleScene(Scene):
    def __init__(self, server_host, server_port):
        super().__init__()

        self.client = Client(server_host, server_port)
        self.client.connect_to_server()

        self.manager = pygame_gui.UIManager((800, 600))

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
        self.button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect((350, 400), (100, 50)),
            text="Submit",
            manager=self.manager,
        )

    def process_input(self, events):
        for event in events:
            if event.type == pygame.USEREVENT:
                if event.user_type == pygame_gui.UI_BUTTON_PRESSED:
                    if event.ui_element == self.button:
                        username = self.text_entry.get_text()
                        if not username.isalnum() and "_" not in username:
                            print(
                                "Username can only contain alphanumeric characters and underscores."
                            )
                        elif len(username) > 10:
                            print("Username cannot be longer than 10 characters.")
                        else:
                            print(f"User Name: {username}")
                            success = self.client.register_nickname(username)
                            print(success)
                            if success:
                                return GameScene()  # Switch to the game scene
                            else:
                                print("Registration failed.")

            self.manager.process_events(event)

    def update(self, time_delta):
        self.manager.update(time_delta)

    def draw(self, screen):
        screen.fill((0, 0, 50))  # Dark blue background
        screen.blit(self.title_text, (200, 50))  # Draw the title
        screen.blit(self.username_label_text, (200, 200))  # Draw the username label
        self.manager.draw_ui(screen)


class GameScene(Scene):
    def __init__(self):
        super().__init__()

    def draw(self, screen):
        screen.fill((0, 0, 0))
        font = pygame.font.Font(None, 36)
        text = font.render("Welcome to the Game!", True, (255, 255, 255))
        text_rect = text.get_rect(center=(800 / 2, 600 / 2))
        screen.blit(text, text_rect)


# Scene manager
class SceneManager:
    def __init__(self, initial_scene):
        self.current_scene = initial_scene

    def process_input(self, events):
        new_scene = self.current_scene.process_input(events)
        if new_scene is not None:
            self.current_scene = new_scene

    def update(self, time_delta):
        self.current_scene.update(time_delta)

    def draw(self, screen):
        self.current_scene.draw(screen)


# Main game loop
def game_loop():
    pygame.init()
    screen = pygame.display.set_mode((800, 600))
    clock = pygame.time.Clock()
    scene_manager = SceneManager(
        TitleScene("localhost", 12345)
    )  # replace with your server host and port

    while True:
        events = pygame.event.get()
        for event in events:
            if event.type == pygame.QUIT:
                pygame.quit()
                return

        scene_manager.process_input(events)
        scene_manager.update(clock.tick(60) / 1000.0)
        scene_manager.draw(screen)

        pygame.display.flip()


game_loop()
