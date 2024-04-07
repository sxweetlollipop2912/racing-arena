import pygame
import pygame_gui
import queue
from typing import List, Optional, Tuple, Dict

from scene import Scene
from globals import current_nickname, SCREEN_WIDTH, SCREEN_HEIGHT


class GameScene(Scene):
    def __init__(self):
        super().__init__()
        self.race_length = 0
        self.answer_time_limit = 0
        # For every player, save its nickname as key, and diff points last round, position as values
        self.players: Dict[str, Tuple[int, int]] = {}
        # Fastest player in the last round
        self.fastest_player = None

        self.normal_font = pygame.font.Font(None, 36)
        self.big_font = pygame.font.Font(None, 72)
        # Question text
        self.question_text = None
        # Answer input
        self.answer_input = pygame_gui.elements.UITextEntryLine(
            relative_rect=pygame.Rect((200, 300), (400, 50)),
            manager=self.manager,
        )
        # Submit button
        self.button_submit = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect((350, 400), (100, 50)),
            text="Submit",
            manager=self.manager,
        )
        # Result text
        self.result_text = None
        # Huge announcement text
        self.announcement_text = None

    def process_input(
        self, ui_events: List[pygame.event.Event], messages: queue.Queue
    ) -> Optional[Scene]:
        for event in ui_events:
            self.manager.process_events(event)
        try:
            while (message := messages.get(block=False)):
                cmd, args = message
                if cmd == "QUESTION":
                    round_index, first_number, operator, second_number = args
                    self.question_text = self.normal_font.render(f"Q#{round_index}: {first_number} {operator} {second_number} = ?", True, (255, 255, 255))
                    if self.players[current_nickname][1] != -1:
                        # Enable the input and submit button if the player is not disqualified
                        self.button_submit.enable()
                        self.answer_input.set_text("")
                        self.answer_input.enable()
                    self.result_text = None

                elif cmd == "ANSWER_CORRECT":
                    answer = args[0]
                    self.result_text = self.normal_font.render(f"Correct! The answer is {answer}", True, (0, 255, 0))
                    self.button_submit.disable()
                    self.answer_input.disable()

                elif cmd == "ANSWER_INCORRECT":
                    answer = args[0]
                    if self.players[current_nickname][1] == -1:
                        # Current player is disqualified
                        self.result_text = self.normal_font.render(f"The answer is {answer}", True, (255, 0, 0))
                    else:
                        self.result_text = self.normal_font.render(f"Incorrect! The answer is {answer}", True, (255, 0, 0))
                        self.button_submit.disable()
                        self.answer_input.disable()

                elif cmd == "DISQUALIFICATION":
                    for nickname, values in self.players.items():
                        if nickname in args:
                            # Set the position of the disqualified player to -1
                            values[1] = -1
                    if current_nickname in args:
                        self.announcement_text = self.big_font.render("You have been disqualified!", True, (255, 0, 0))
                        self.answer_input = None
                        self.button_submit = None
                    self.update_scoreboard_ui()
                
                elif cmd == "SCORE":
                    self.fastest_player, *rest = args
                    # Update score of every player if they are not disqualified
                    self.players.update({player: (diff_points, score) for player, diff_points, score in zip(rest[::3], rest[1::3], rest[2::3]) if self.players[player][1] != -1})
                    self.update_scoreboard_ui()
                
                elif cmd == "GAME_OVER":
                    winner = args[0]
                    if winner:
                        self.announcement_text = self.big_font.render(f"Game over. {winner} wins!", True, (0, 255, 0))
                    else:
                        self.announcement_text = self.big_font.render("Game over. Nobody won.", True, (255, 255, 0))
                
                elif cmd == "PLAYER_LEFT":
                    nickname = args[0]
                    self.players[nickname][1] = -1
                    self.update_scoreboard_ui()
        except queue.Empty:
            pass
    
    def update_scoreboard_ui(self):
        # Draw the lanes
        pass

    def update(self, time_delta: float) -> None:
        self.manager.update(time_delta)

    def draw(self, screen: pygame.Surface) -> None:
        screen.fill((0, 0, 0))
        font = pygame.font.Font(None, 36)
        text = font.render("Welcome to the Game!", True, (255, 255, 255))
        text_rect = text.get_rect(center=(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2))

        if self.question_text:
            screen.blit(self.question_text, self.question_text.get_rect(center=(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2)))
        if self.result_text:
            screen.blit(self.result_text, self.result_text.get_rect(center=(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2 + 100)))
        if self.announcement_text:
            screen.blit(self.announcement_text, self.announcement_text.get_rect(center=(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2)))
        self.manager.draw_ui(screen)
