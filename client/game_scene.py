# TODO: Show scores, countdown
import pygame
import pygame_gui
import queue
from typing import List, Optional, Tuple, Dict
from enum import Enum
import asyncio

from scene import Scene
from globals import SCREEN_SIZE, LOGGER
import globals
from connection_manager import ConnectionManager
import registration_scene


connection = ConnectionManager()


class InGameState(Enum):
    QUESTION = 1
    SHOW_RESULT = 2
    GAME_OVER = 3


class GameScene(Scene):
    def __init__(self):
        super().__init__()
        self.race_length = 0
        self.answer_time_limit = 0
        # For every player, save its nickname as key, and diff points last round, position as values
        self.players: Dict[str, Tuple[int, int]] = {}
        # Fastest player in the last round
        self.fastest_player = None
        # Whether this player is disqualified
        self.is_disqualified = False
        self.current_state = InGameState.QUESTION
        self.just_changed_state = False

        self.manager = pygame_gui.UIManager(SCREEN_SIZE)
        self.manager.get_theme().load_theme("client/assets/GameScene_Theme.json")

        # Create font objects
        self.annoucement_font = pygame.font.Font(
            "client/assets/Poppins-Regular.ttf", 48
        )
        self.annoucement_font.set_bold(False)
        self.body_font = pygame.font.Font("client/assets/Poppins-Regular.ttf", 20)
        self.body_font.set_bold(False)
        
        self.answer_error: Optional[str] = None
        self.answer_success: Optional[str] = None
        self.question_text: Optional[str] = None
        
        self.answer_input = pygame_gui.elements.UITextEntryLine( # Answer input (350, 525) (675, 585)
            relative_rect=pygame.Rect((350, 525), (325, 60)),
            manager=self.manager,
        )
        
        # button_submit_attrs = (SCREEN_SIZE[0] - 80, SCREENSIZE[1] - 35, 70, 30)
        self.button_submit = pygame_gui.elements.UIButton( # Submit button (680, 525) (785, 585)
            relative_rect=pygame.Rect((680, 525), (105, 60)),
            text="ANSWER",
            manager=self.manager,
        )
        
        # button_map_attrs = (SCREEN_SIZE[0] - 60, 10, 50, 50)
        self.button_map = pygame_gui.elements.UIButton( # Map button (700, 30) (780, 110)
            relative_rect=pygame.Rect((700, 30), (80, 80)),
            text="MAP",
            manager=self.manager,
        )

        self.current_round = pygame_gui.elements.UITextBox(
            relative_rect=pygame.Rect((350, 145), (430, 70)),
            html_text="Current round: 0/" + str(self.race_length),
            manager=self.manager,
        )
        
        self.question_display = pygame_gui.elements.UITextBox(
            relative_rect = pygame.Rect((350, 235), (430, 275)),
            html_text="8273/1238 = ?",
            manager=self.manager,
            object_id="#question_display",
        )
        
        self.score_board = pygame_gui.elements.UITextBox(
            relative_rect = pygame.Rect((15, 145), (320, 440)),
            html_text="Player 1: 87123\nPlayer 2: 1231236723",
            manager=self.manager,
            object_id="#score_board",
        )
        
        self.result_text: Optional[str] = None
        self.announcement_text: Optional[str] = None
        
        # self.current_round.set_text("Current round")
        
        

    def process_input(
        self, ui_events: List[pygame.event.Event], messages: queue.Queue
    ) -> Optional[Scene]:
        for event in ui_events:
            self.manager.process_events(event)
            if event.type == pygame.USEREVENT:
                if event.user_type == pygame_gui.UI_BUTTON_PRESSED:
                    LOGGER.info(
                        f"[UI Thread] [In Game] User pressed button {event.ui_element}"
                    )
                    if event.ui_element == self.button_submit:
                        if (
                            self.current_state == InGameState.QUESTION
                            and not self.is_disqualified
                        ):
                            answer = self.answer_input.get_text()
                            LOGGER.info(
                                f"[UI Thread] [In Game] User submit answer: {answer}"
                            )
                            if not answer.isdigit():
                                self.answer_success = None
                                self.answer_error = "Answer must be a number."
                            else:
                                self.answer_error = None
                                self.answer_success = "Answer submitted."
                                loop = asyncio.new_event_loop()
                                loop.run_until_complete(connection.send_answer(answer))

                        elif self.current_state == InGameState.GAME_OVER:
                            loop = asyncio.new_event_loop()
                            loop.run_until_complete(
                                connection.send_registration(globals.current_nickname)
                            )
                            LOGGER.info(
                                f"[UI Thread] [In Game] User wants to play again as {globals.current_nickname}"
                            )
                            return registration_scene.RegistrationScene()

        try:
            while message := messages.get(block=False):
                cmd, args = message
                if cmd == "QUESTION":
                    round_index, first_number, operator, second_number = args
                    self.question_text = f"Q#{round_index}: {first_number} {operator} {second_number} = ?"
                    self.answer_error = None
                    self.answer_success = None
                    self.just_changed_state = self.current_state != InGameState.QUESTION
                    self.current_state = InGameState.QUESTION

                elif cmd == "ANSWER_CORRECT":
                    answer = args[0]
                    self.result_text = f"Correct! The answer is {answer}"
                    self.just_changed_state = (
                        self.current_state != InGameState.SHOW_RESULT
                    )
                    self.current_state = InGameState.SHOW_RESULT

                elif cmd == "ANSWER_INCORRECT":
                    answer = args[0]
                    if self.is_disqualified:
                        # Current player is disqualified
                        self.result_text = f"The answer is {answer}"
                    else:
                        self.result_text = f"Incorrect! The answer is {answer}"
                    self.just_changed_state = (
                        self.current_state != InGameState.SHOW_RESULT
                    )
                    self.current_state = InGameState.SHOW_RESULT

                elif cmd == "ANSWER_FAILURE":
                    self.answer_error = args[0]

                elif cmd == "DISQUALIFICATION":
                    for nickname, values in self.players.items():
                        if nickname in args:
                            # Set the position of the disqualified player to -1
                            values[1] = -1
                    if globals.current_nickname in args:
                        self.announcement_text = "You have been disqualified!"
                        self.is_disqualified = True
                    self.just_changed_state = (
                        self.current_state != InGameState.SHOW_RESULT
                    )
                    self.current_state = InGameState.SHOW_RESULT
                    self.update_scoreboard_ui()

                elif cmd == "SCORE":
                    self.fastest_player, *rest = args
                    # Update score of every player if they are not disqualified
                    self.players.update(
                        {
                            player: (diff_points, score)
                            for player, diff_points, score in zip(
                                rest[::3], rest[1::3], rest[2::3]
                            )
                            if self.players[player][1] != -1
                        }
                    )
                    self.just_changed_state = (
                        self.current_state != InGameState.SHOW_RESULT
                    )
                    self.current_state = InGameState.SHOW_RESULT
                    self.update_scoreboard_ui()

                elif cmd == "GAME_OVER":
                    winner = args[0] if len(args) > 0 else None
                    if winner:
                        if winner == globals.current_nickname:
                            self.announcement_text = "Game over. You win!"
                        else:
                            self.announcement_text = f"Game over. {winner} wins!"
                    else:
                        self.announcement_text = "Game over. Nobody won."
                    self.just_changed_state = (
                        self.current_state != InGameState.GAME_OVER
                    )
                    self.current_state = InGameState.GAME_OVER

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
        
    def draw_Ingame(self, screen: pygame.Surface) -> None:
        pygame.draw.rect( # road (15, 15), (700, 100)
            screen, 
            (226,235,242), 
            (15, 15, 680, 115),
            border_radius=5,
        )
        
        # self.manager.draw_ui(screen)

    def draw(self, screen: pygame.Surface) -> None:
        self.draw_Ingame(screen)
        
        # screen.fill((25, 25, 25))
        # Get the size of the screen
        screen_width, screen_height = pygame.display.get_surface().get_size()

        if self.current_state == InGameState.QUESTION:
            if self.announcement_text:
                announcement_ui_element = self.annoucement_font.render(
                    self.announcement_text,
                    True,
                    (255, 255, 255),
                )
                screen.blit(
                    announcement_ui_element,
                    announcement_ui_element.get_rect(
                        center=(screen_width / 2, screen_height / 2 - 100)
                    ),
                )
            question_ui_element = self.annoucement_font.render(
                self.question_text,
                True,
                (255, 255, 255),
            )
            screen.blit(
                question_ui_element,
                question_ui_element.get_rect(
                    center=(screen_width / 2, screen_height / 2)
                ),
            )
            if not self.is_disqualified:
                if self.just_changed_state:
                    self.answer_input.enable()
                    self.answer_input.set_text("")
                    self.answer_input.focus()
                    self.button_submit.enable()

                if self.answer_error:
                    answer_error_ui_element = self.body_font.render(
                        self.answer_error,
                        True,
                        (200, 0, 0),
                    )
                    screen.blit(
                        answer_error_ui_element,
                        answer_error_ui_element.get_rect(
                            center=(screen_width / 2, screen_height / 2 + 200)
                        ),
                    )

                if self.answer_success:
                    answer_success_ui_element = self.body_font.render(
                        self.answer_success,
                        True,
                        (0, 200, 0),
                    )
                    screen.blit(
                        answer_success_ui_element,
                        answer_success_ui_element.get_rect(
                            center=(screen_width / 2, screen_height / 2 + 200)
                        ),
                    )

            elif self.just_changed_state:
                self.answer_input.disable()
                self.button_submit.disable()

        elif self.current_state == InGameState.SHOW_RESULT:
            if self.just_changed_state:
                self.answer_input.disable()
                self.button_submit.disable()

            if self.announcement_text:
                announcement_ui_element = self.annoucement_font.render(
                    self.announcement_text,
                    True,
                    (255, 255, 255),
                )
                screen.blit(
                    announcement_ui_element,
                    announcement_ui_element.get_rect(
                        center=(screen_width / 2, screen_height / 2 - 100)
                    ),
                )
            result_ui_element = self.body_font.render(
                self.result_text,
                True,
                (255, 255, 255),
            )
            screen.blit(
                result_ui_element,
                result_ui_element.get_rect(
                    center=(screen_width / 2, screen_height / 2)
                ),
            )

        elif self.current_state == InGameState.GAME_OVER:
            if self.just_changed_state:
                self.answer_input.kill()
                self.button_submit.kill()
                self.button_submit = pygame_gui.elements.UIButton(
                    relative_rect=pygame.Rect((screen_width / 2 - 75, 515), (150, 50)),
                    text="PLAY AGAIN?",
                    manager=self.manager,
                )
                self.button_submit.enable()
                self.answer_error = None

            announcement_ui_element = self.annoucement_font.render(
                self.announcement_text,
                True,
                (255, 255, 255),
            )
            screen.blit(
                announcement_ui_element,
                announcement_ui_element.get_rect(
                    center=(screen_width / 2, screen_height / 2)
                ),
            )

        self.just_changed_state = False
        self.manager.draw_ui(screen)
