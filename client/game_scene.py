# TODO: Show scores, countdown
import re
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
    # ROAD_MAP = 4

class Countdown:
    def __init__(self, start_time: float):
        self.start_time: float = start_time
        self.time: float = start_time

    def set_start_time(self, start_time: float) -> None:
        self.start_time = start_time
        self.reset()

    def update(self, dt: float) -> None:
        if self.time - dt > 0:
            self.time -= dt
        else:
            self.time = 0.0

    def reset(self) -> None:
        self.time = self.start_time


class GameScene(Scene):

    def __init__(self):
        super().__init__()
        self.countdown = Countdown(5.0)
        self.background = pygame.image.load("client/assets/wallpaper.jpg")
        self.race_length = 0
        self.answer_time_limit = 0
        self.prepare_time_limit = 0
        # For every player, save its nickname as key, and diff points last round, position as values
        self.players: Dict[str, List[int, int]] = {}
        # Fastest player in the last round
        self.fastest_player = None
        # Whether this player is disqualified
        self.is_disqualified = False
        self.current_state = InGameState.SHOW_RESULT
        self.just_changed_state = False

        self.manager = pygame_gui.UIManager(SCREEN_SIZE)
        self.manager.get_theme().load_theme("client/assets/answer_submit_button.json")
        self.manager.get_theme().load_theme("client/assets/text_entry_line.json")

        # Create font objects
        self.announcement_font = pygame.font.Font(
            "client/assets/Poppins-Regular.ttf", 42
        )
        self.announcement_font.set_bold(False)
        self.label_font = pygame.font.Font("client/assets/Poppins-Regular.ttf", 36)
        self.label_font.set_bold(False)
        self.disqualified_font = pygame.font.Font(
            "client/assets/Poppins-Regular.ttf", 20
        )
        self.disqualified_font.set_bold(False)
        self.body_font = pygame.font.Font("client/assets/Poppins-Regular.ttf", 20)
        self.body_font.set_bold(False)

        self.answer_input = pygame_gui.elements.UITextEntryLine(
            relative_rect=pygame.Rect((280, 530), (350, 50)),
            manager=self.manager,
        )
        self.answer_error: Optional[str] = None
        self.answer_success: Optional[str] = None
        self.question_text: Optional[str] = None
        self.question_number_text: Optional[str] = None
        self.button_submit = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect((630, 530), (150, 50)),
            text="SUBMIT",
            manager=self.manager,
        )
        self.button_map = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect((720, 15), (65, 65)),
            text="MAP",
            manager=self.manager,
        )
        self.result_text: Optional[str] = None
        self.announcement_text: Optional[str] = None
        self.result_number_text: Optional[str] = "Next round in:"
        self.answer_input.disable()
        self.button_submit.disable()

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

                            if re.match(r"^[-+]*\d+$", answer):
                                self.answer_error = None
                                self.answer_success = "Answer submitted."
                                loop = asyncio.new_event_loop()
                                loop.run_until_complete(connection.send_answer(answer))
                            else:
                                self.answer_success = None
                                self.answer_error = "Answer must be an integer."

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
                    self.handle_question_command(args)
                elif cmd == "ANSWER_CORRECT":
                    self.handle_answer_correct_command(args)
                elif cmd == "ANSWER_INCORRECT":
                    self.handle_answer_incorrect_command(args)
                elif cmd == "ANSWER":
                    self.handle_answer_disqualified_command(args)
                elif cmd == "ANSWER_FAILURE":
                    self.handle_answer_failure_command(args)
                elif cmd == "DISQUALIFICATION":
                    self.handle_disqualification_command(args)
                elif cmd == "SCORES":
                    self.handle_score_command(args)
                elif cmd == "GAME_OVER":
                    self.handle_game_over_command(args)
                elif cmd == "PLAYER_LEFT":
                    self.handle_player_left_command(args)
        except queue.Empty:
            pass

    def switch_state(self, new_state: InGameState) -> None:
        self.just_changed_state = self.current_state != new_state
        self.current_state = new_state
        if new_state == InGameState.QUESTION:
            self.countdown.set_start_time(self.answer_time_limit)
        elif new_state == InGameState.SHOW_RESULT:
            self.countdown.set_start_time(self.prepare_time_limit)

    def handle_question_command(self, args):
        round_index, first_number, operator, second_number = args
        self.question_text = f"{first_number} {operator} {second_number} = ?"
        self.question_number_text = (
            f"Question #{round_index.zfill(2)}/{self.race_length}"
        )
        self.answer_error = None
        self.answer_success = None
        self.switch_state(InGameState.QUESTION)

    def handle_answer_correct_command(self, args):
        answer = args[0]
        # TODO, make the result not out of the box
        self.result_text = f"Correct! The answer is {answer}"
        self.switch_state(InGameState.SHOW_RESULT)

    def handle_answer_incorrect_command(self, args):
        answer = args[0]
        # TODO, make the result not out of the box
        self.result_text = f"Incorrect! The answer is {answer}"
        self.switch_state(InGameState.SHOW_RESULT)

    def handle_answer_disqualified_command(self, args):
        answer = args[0]
        # TODO, make the result not out of the box
        self.result_text = f"The answer is {answer}"
        self.switch_state(InGameState.SHOW_RESULT)

    def handle_answer_failure_command(self, args):
        self.answer_error = args[0]

    def handle_disqualification_command(self, args):
        for nickname, values in self.players.items():
            if nickname in args:
                values[1] = -1
        if globals.current_nickname in args:
            self.announcement_text = "You have been disqualified!"
            self.is_disqualified = True
        self.switch_state(InGameState.SHOW_RESULT)

    def handle_score_command(self, args):
        self.fastest_player, *rest = args
        for player_points in rest:
            player, diff_points, score = player_points.split(",")
            if player not in self.players or self.players[player][1] != -1:
                self.players[player] = [int(diff_points), int(score)]
        self.switch_state(InGameState.SHOW_RESULT)

    def handle_game_over_command(self, args):
        winner = args[0] if len(args) > 0 else None
        if winner:
            if winner == globals.current_nickname:
                self.announcement_text = "Game over. You win!"
            else:
                self.announcement_text = f"Game over. {winner} wins!"
        else:
            self.announcement_text = "Game over. Nobody won."
        self.just_changed_state = self.current_state != InGameState.GAME_OVER
        self.current_state = InGameState.GAME_OVER

    def handle_player_left_command(self, args):
        nickname = args[0]
        self.players[nickname][1] = -1

    def update(self, time_delta: float) -> None:
        self.manager.update(time_delta)
        self.countdown.update(time_delta)

    def draw_skeleton(self, screen: pygame.Surface) -> None:
        screen.fill((0, 0, 0))
        screen.blit(self.background, (0, 0))
        screen_width, screen_height = pygame.display.get_surface().get_size()

        box_color = (25, 25, 25)
        padding = 20
        height = 480
        gap = 10
        left_box_width = (screen_width - 2 * padding - gap) / 3
        right_box_width = 2 * left_box_width
        box_height = height

        # Create the boxes
        left_box = pygame.Rect(padding, 100, left_box_width, box_height)
        top_right_box = pygame.Rect(
            padding + left_box_width + gap, 100, right_box_width, 90
        )
        right_box = pygame.Rect(
            padding + left_box_width + gap, 200, right_box_width, box_height - 160
        )

        pygame.draw.rect(screen, box_color, left_box)
        pygame.draw.rect(screen, box_color, top_right_box)
        pygame.draw.rect(screen, box_color, right_box)

    def draw_countdown(self, screen: pygame.Surface) -> None:
        countdown_text = f"{max(round(self.countdown.time, 1), 0.0)}"
        countdown_ui_element = self.label_font.render(
            countdown_text,
            True,
            (255, 255, 255),
        )
        screen.blit(
            countdown_ui_element,
            countdown_ui_element.get_rect(left=700, top=120),
        )

    def draw_leaderboard(self, screen: pygame.Surface) -> None:
        # qualified_players = [(nickname, self.players[nickname]) for nickname in self.players if self.players[nickname][1] >= 0]
        # disqualified_players = [(nickname, self.players[nickname]) for nickname in self.players if self.players[nickname][1] < 0]
        # qualified_players.sort(key=lambda x: x[1][1], reverse=True)

        # mock data
        qualified_players = [
            ("p1", (1, 100)),
            ("p2", (-10, 200)),
            ("p3", (-3, 300)),
            ("p4", (4, 400)),
            ("p5", (5, 500)),
            ("p6", (-1, 600)),
            ("p7", (7, 700)),
        ]
        disqualified_players = [
            ("p8", (-1, 800)),
            ("p9", (-1, 900)),
            ("p10", (-1, 1000)),
        ]
        qualified_players.sort(key=lambda x: x[1][1], reverse=True)
        disqualified_players.sort(key=lambda x: x[0])

        screen_width, screen_height = pygame.display.get_surface().get_size()
        # fixed size copied from draw_skeleton()
        outside_padding = 20
        outside_gap = 10
        inside_padding = 10
        inside_height = 480 - inside_padding * 2
        inside_width = (
            screen_width - 2 * outside_padding - outside_gap
        ) / 3 - 2 * inside_padding
        box_rect = pygame.Rect(
            outside_padding + inside_padding,
            100 + inside_padding,
            inside_width,
            inside_height,
        )

        column_gap = 10
        column_width = (inside_width - 2 * column_gap) / 3
        column_1_box_rect = pygame.Rect(
            box_rect.left, box_rect.top, column_width, inside_height
        )
        column_2_box_rect = pygame.Rect(
            box_rect.left + column_width + column_gap,
            box_rect.top,
            column_width,
            inside_height,
        )
        column_3_box_rect = pygame.Rect(
            box_rect.left + 2 * column_width + 2 * column_gap,
            box_rect.top,
            column_width,
            inside_height,
        )

        strike_body_font = pygame.font.Font("client/assets/Poppins-Regular.ttf", 20)
        strike_body_font.set_strikethrough(True)

        ###############
        # Draw nicknames on first column
        ###############
        i: int = -1
        for nickname, (_, score) in qualified_players:
            i += 1
            if i > 0:
                column_1_box_rect.y += inside_height / 10
            if nickname == globals.current_nickname:
                pygame.draw.rect(
                    screen,
                    (125, 58, 6),
                    pygame.Rect(
                        column_1_box_rect.left,
                        column_1_box_rect.top,
                        inside_width,
                        inside_height / 10,
                    ),
                )
            player_name = self.body_font.render(
                limit_text_width(f"{nickname}", column_width, self.label_font),
                True,
                (230, 230, 230),
            )
            screen.blit(
                player_name,
                player_name.get_rect(
                    center=(
                        column_1_box_rect.centerx,
                        column_1_box_rect.top + inside_height / 20,
                    ),
                ),
            )

        for nickname, (_, score) in disqualified_players:
            i += 1
            if i > 0:
                column_1_box_rect.y += inside_height / 10
            if nickname == globals.current_nickname:
                pygame.draw.rect(
                    screen,
                    (125, 58, 6),
                    pygame.Rect(
                        column_1_box_rect.left,
                        column_1_box_rect.top,
                        inside_width,
                        inside_height / 10,
                    ),
                )
            player_name = strike_body_font.render(
                limit_text_width(f"{nickname}", column_width, self.label_font),
                True,
                (135, 134, 134),
            )
            screen.blit(
                player_name,
                player_name.get_rect(
                    center=(
                        column_1_box_rect.centerx,
                        column_1_box_rect.top + inside_height / 20,
                    ),
                ),
            )

        ###############
        # Draw score on second column
        ###############
        i = -1
        for nickname, (_, score) in qualified_players:
            i += 1
            if i > 0:
                column_2_box_rect.y += inside_height / 10
            player_score = self.body_font.render(
                f"{score}",
                True,
                (230, 230, 230),
            )
            screen.blit(
                player_score,
                player_score.get_rect(
                    center=(
                        column_2_box_rect.centerx,
                        column_2_box_rect.top + inside_height / 20,
                    ),
                ),
            )

        ###############
        # Draw diff points on third column
        ###############
        i = -1
        for nickname, (diff_points, _) in qualified_players:
            i += 1
            if i > 0:
                column_3_box_rect.y += inside_height / 10
            if diff_points > 0:
                player_diff_points = self.body_font.render(
                    f"+{diff_points}",
                    True,
                    (0, 200, 0),
                )
            elif diff_points < 0:
                player_diff_points = self.body_font.render(
                    f"{diff_points}",
                    True,
                    (200, 0, 0),
                )
            else:
                player_diff_points = self.body_font.render(
                    f"{diff_points}",
                    True,
                    (230, 230, 230),
                )
            screen.blit(
                player_diff_points,
                player_diff_points.get_rect(
                    center=(
                        column_3_box_rect.centerx,
                        column_3_box_rect.top + inside_height / 20,
                    ),
                ),
            )
    
    def draw_lane(self, screen: pygame.Surface) -> None:
        # Draw the lane
        lane = pygame.image.load("client/assets/lane.jpg")
        lane = pygame.transform.scale(lane, (690, 80))
        screen.blit(lane, lane.get_rect(top = 10, left = 20, width = 690, height = 90))
        
        # Draw the car
        car = pygame.image.load("client/assets/sprites/orange_car.png")
        car = pygame.transform.scale(car, (64, 64))
        # get car top (x position)
        # x = 20 + (690 - 60) * (maxpoint / currentpoint)
        screen.blit(car, car.get_rect(top = 18, left = 20, width = 64, height = 64))
        
        
    def draw(self, screen: pygame.Surface) -> None:
        screen_width, screen_height = pygame.display.get_surface().get_size()

        if self.current_state == InGameState.QUESTION:
            self.draw_skeleton(screen)
            self.draw_countdown(screen)
            self.draw_leaderboard(screen)
            self.draw_question(screen)
            self.draw_lane(screen)
        elif self.current_state == InGameState.SHOW_RESULT:
            self.draw_skeleton(screen)
            self.draw_countdown(screen)
            self.draw_leaderboard(screen)
            self.draw_show_results(screen)
            self.draw_lane(screen)
        elif self.current_state == InGameState.GAME_OVER:
            screen.fill((25, 25, 25))
            self.draw_game_over(screen)
        # elif self.current_state == InGameState.ROAD_MAP:
        #    self.draw_road_map(screen)

        self.just_changed_state = False
        self.manager.draw_ui(screen)

    def draw_question(self, screen: pygame.Surface) -> None:
        screen_width, screen_height = pygame.display.get_surface().get_size()
        if self.announcement_text:
            # TODO: adjust the position of the announcement
            announcement_ui_element = self.disqualified_font.render(
                self.announcement_text,
                True,
                (255, 0, 0),
            )
            screen.blit(
                announcement_ui_element,
                announcement_ui_element.get_rect(left=320, top=screen_height / 2 - 60),
            )
        question_number_ui_element = self.label_font.render(
            self.question_number_text,
            True,
            (255, 255, 255),
        )
        screen.blit(
            question_number_ui_element,
            question_number_ui_element.get_rect(left=320, top=120),
        )
        question_ui_element = self.announcement_font.render(
            self.question_text,
            True,
            (255, 255, 255),
        )
        screen.blit(
            question_ui_element,
            question_ui_element.get_rect(left=320, top=screen_height / 2 + 40),
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
                    answer_error_ui_element.get_rect(left=350, top=485),
                )

            if self.answer_success:
                answer_success_ui_element = self.body_font.render(
                    self.answer_success,
                    True,
                    (0, 200, 0),
                )
                screen.blit(
                    answer_success_ui_element,
                    answer_success_ui_element.get_rect(left=350, top=485),
                )

        elif self.just_changed_state:
            self.answer_input.disable()
            self.button_submit.disable()

    def draw_show_results(self, screen: pygame.Surface) -> None:
        screen_width, screen_height = pygame.display.get_surface().get_size()
        if self.just_changed_state:
            self.answer_input.disable()
            self.button_submit.disable()

        if self.announcement_text:
            # TODO: adjust the position of the announcement
            announcement_ui_element = self.disqualified_font.render(
                self.announcement_text,
                True,
                (255, 0, 0),
            )
            screen.blit(
                announcement_ui_element,
                announcement_ui_element.get_rect(left=320, top=screen_height / 2 - 60),
            )

        result_number_ui_element = self.label_font.render(
            self.result_number_text,
            True,
            (255, 255, 255),
        )
        screen.blit(
            result_number_ui_element,
            result_number_ui_element.get_rect(left=320, top=120),
        )
        result_ui_element = self.label_font.render(
            self.result_text,
            True,
            (255, 255, 255),
        )
        screen.blit(
            result_ui_element,
            result_ui_element.get_rect(left=320, top=screen_height / 2 + 40),
        )

    def draw_game_over(self, screen: pygame.Surface) -> None:
        screen_width, screen_height = pygame.display.get_surface().get_size()
        if self.just_changed_state:
            self.answer_input.kill()
            self.button_submit.kill()
            self.button_map.kill()
            self.button_submit = pygame_gui.elements.UIButton(
                relative_rect=pygame.Rect((screen_width / 2 - 75, 515), (150, 50)),
                text="PLAY AGAIN?",
                manager=self.manager,
            )
            self.button_submit.enable()
            self.answer_error = None

        announcement_ui_element = self.announcement_font.render(
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
        
    def draw_road_map(self, screen: pygame.Surface) -> None:
        # Draw the road map
        lane = pygame.image.load("client/assets/lane.jpg")
        lane = pygame.transform.scale(lane, (601, 72))
        for i in (0, 10):
            screen.blit(lane, lane.get_rect(top = 75 + i * 72, left = 100, width = 601, height = 72))


def limit_text_width(text, max_width, font):
    width, _ = font.size(text)
    if width > max_width:
        while width > max_width:
            text = text[:-1]
            width, _ = font.size(text + "...")
        text += "..."
    return text
