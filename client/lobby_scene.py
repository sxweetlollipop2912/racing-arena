import pygame
import pygame_gui
import queue
import asyncio
from typing import List, Optional
import globals

from player import Player
from scene import Scene
from game_scene import GameScene
from connection_manager import ConnectionManager

connection = ConnectionManager()


class LobbyScene(Scene):
    def __init__(self, players: List[Player] = []):
        super().__init__()
        self.players = players
        self.manager = pygame_gui.UIManager((800, 600))
        self.manager.get_theme().load_theme("client/assets/ready_button.json")
        self.background = pygame.image.load("client/assets/wallpaper.jpg")
        self.button_ready = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect((330, 530), (150, 50)),
            text="READY",
            manager=self.manager,
        )
        self.ready_button_timer = None
        self.READY_BUTTON_TIMEOUT = 5000
        self.font = pygame.font.Font("client/assets/Poppins-Regular.ttf", 32)
        self.font.set_bold(False)
        self.player_font = pygame.font.Font("client/assets/Poppins-Regular.ttf", 20)
        self.player_font.set_bold(False)

    def process_input(
        self, events: List[pygame.event.Event], messages: queue.Queue
    ) -> Optional[Scene]:
        for event in events:
            self.manager.process_events(event)
            if event.type == pygame.USEREVENT:
                if event.user_type == pygame_gui.UI_BUTTON_PRESSED:
                    if event.ui_element == self.button_ready:
                        if self.button_ready.text == "READY":
                            self.button_ready.disable()
                            self.ready_button_timer = pygame.time.set_timer(
                                self.READY_BUTTON_TIMEOUT, 0
                            )
                            self.ready_button_timer = pygame.time.set_timer(
                                self.READY_BUTTON_TIMEOUT, 100, 1
                            )
                            loop = asyncio.new_event_loop()
                            loop.run_until_complete(connection.send_ready_signal())
                            for player in self.players:
                                if player.nickname == globals.current_nickname:
                                    player.is_ready = True
                        else:
                            self.button_ready.disable()
                            self.ready_button_timer = pygame.time.set_timer(
                                self.READY_BUTTON_TIMEOUT, 0
                            )
                            self.ready_button_timer = pygame.time.set_timer(
                                self.READY_BUTTON_TIMEOUT, 100, 1
                            )
                            loop = asyncio.new_event_loop()
                            loop.run_until_complete(connection.send_unready_signal())
                            for player in self.players:
                                if player.nickname == globals.current_nickname:
                                    player.is_ready = False
            elif event.type == self.READY_BUTTON_TIMEOUT:
                self.button_ready.enable()
                self.ready_button_timer = pygame.time.set_timer(
                    self.READY_BUTTON_TIMEOUT, 0, 1
                )

        try:
            while message := messages.get(block=False):
                command, args = message
                if command == "PLAYER_READY":
                    for player in self.players:
                        if player.nickname == args[0]:
                            player.is_ready = True
                elif command == "PLAYER_UNREADY":
                    for player in self.players:
                        if player.nickname == args[0]:
                            player.is_ready = False
                elif command == "PLAYER_JOINED":
                    self.players.append(Player(args[0]))
                elif command == "PLAYER_LEFT":
                    for player in self.players:
                        if player.nickname == args[0]:
                            self.players.remove(player)
                elif command == "GAME_STARTING":
                    race_length, answer_time_limit, prepare_time_limit = args
                    answer_time_limit = int(answer_time_limit)
                    prepare_time_limit = int(prepare_time_limit)
                    next_scene = GameScene()
                    next_scene.players = {nickname: (0, 0) for nickname in self.players}
                    next_scene.race_length = race_length
                    next_scene.answer_time_limit = answer_time_limit
                    next_scene.prepare_time_limit = prepare_time_limit
                    next_scene.countdown.set_start_time(prepare_time_limit)
                    return next_scene
        except queue.Empty:
            pass

        return self

    def update(self, time_delta: float):
        self.manager.update(time_delta)

    def draw(self, screen: pygame.Surface):
        screen.fill((0, 0, 0))
        screen.blit(self.background, (0, 0))
        text = self.font.render("Waiting for other players...", True, (255, 255, 255))
        text_rect = text.get_rect(center=(800 / 2, 35))
        screen.blit(text, text_rect)

        # pygame.draw.rect(screen, (204, 255, 255), (50, 100, 700, 400))

        box_color = (50, 50, 50)
        box_width = 700
        box_height = 41
        box_margin = 10  # Margin between the text and the box edges
        box_gap = 5  # Gap between the boxes

        status_box_width = 150
        status_box_height = 41

        for i, player in enumerate(self.players):
            # Draw the player box
            box_rect = pygame.Rect(
                50, 70 + box_height * i + box_gap * i, box_width, box_height
            )
            pygame.draw.rect(screen, box_color, box_rect)

            # Render the player's name
            player_name = self.player_font.render(
                player.nickname, True, (230, 230, 230)
            )
            player_name_rect = player_name.get_rect(
                center=(
                    box_rect.left + box_margin + player_name.get_width() / 2,
                    box_rect.centery,
                )
            )

            # Draw the status box and render the player's status
            status_box_rect = pygame.Rect(
                box_rect.right - status_box_width,
                box_rect.top,
                status_box_width,
                status_box_height,
            )
            if player.is_ready:
                # 00BFA5
                pygame.draw.rect(screen, (0, 200, 0), status_box_rect)
                player_status = self.player_font.render("Ready", True, (0, 0, 0))
                if player.nickname == globals.current_nickname:
                    self.button_ready.set_text("UNREADY")
            else:
                pygame.draw.rect(screen, (255, 0, 0), status_box_rect)
                player_status = self.player_font.render("Not Ready", True, (0, 0, 0))
                if player.nickname == globals.current_nickname:
                    self.button_ready.set_text("READY")
            player_status_rect = player_status.get_rect(center=status_box_rect.center)

            # Draw the player's name and status on the screen
            screen.blit(player_name, player_name_rect)
            screen.blit(player_status, player_status_rect)

        self.manager.draw_ui(screen)
