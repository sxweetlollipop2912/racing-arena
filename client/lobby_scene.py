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
        self.button_ready = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect((330, 510), (120, 80)),
            text="Ready",
            manager=self.manager,
        )

    def process_input(
        self, events: List[pygame.event.Event], messages: queue.Queue
    ) -> Optional[Scene]:
        for event in events:
            self.manager.process_events(event)
            if event.type == pygame.USEREVENT:
                if event.user_type == pygame_gui.UI_BUTTON_PRESSED:
                    if event.ui_element == self.button_ready:
                        if self.button_ready.text == "Ready":
                            # self.button_ready.set_text("Unready")
                            # send ready message to server
                            loop = asyncio.new_event_loop()
                            loop.run_until_complete(connection.send_ready_signal())
                            for player in self.players:
                                if player.nickname == globals.current_nickname:
                                    player.is_ready = True
                        else:
                            # self.button_ready.set_text("Ready")
                            # send unready message to server
                            loop = asyncio.new_event_loop()
                            loop.run_until_complete(connection.send_unready_signal())
                            for player in self.players:
                                if player.nickname == globals.current_nickname:
                                    player.is_ready = False

        try:
            while (message := messages.get(block=False)):
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
                    race_length, answer_time_limit = args
                    next_scene = GameScene()
                    next_scene.players = {nickname: (0,0) for nickname in self.players}
                    next_scene.race_length = race_length
                    next_scene.answer_time_limit = answer_time_limit
                    return next_scene
        except queue.Empty:
            pass

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
                if player.nickname == globals.current_nickname:
                    self.button_ready.set_text("Unready")
            else:
                player_status = player_font.render("Not Ready", True, (255, 0, 0))
                if player.nickname == globals.current_nickname:
                    self.button_ready.set_text("Ready")
            player_status_rect = player_status.get_rect(topleft=(630, 120 + 38 * i))
            screen.blit(player_name, player_name_rect)
            screen.blit(player_status, player_status_rect)

        self.manager.draw_ui(screen)
