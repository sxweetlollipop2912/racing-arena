import pygame
import pygame_gui
import queue
from typing import List, Optional

from player import Player
from scene import Scene
from game_scene import GameScene

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
    
        try:
            while (message := messages.get(block=False)):
                cmd, args = message
                if cmd == "GAME_STARTING":
                    race_length, answer_time_limit = args
                    next_scene = GameScene()
                    next_scene.players = {nickname: (0,0) for nickname in self.players}
                    next_scene.race_length = race_length
                    next_scene.answer_time_limit = answer_time_limit
                    return next_scene
        except queue.Empty:
            pass
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
