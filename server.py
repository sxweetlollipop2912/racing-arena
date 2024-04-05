from typing import List
import random
import time
import re
import asyncio
from enum import Enum
from typing import Optional
import logging

MAX_PLAYERS = 10
MIN_PLAYERS = 2
MAX_RACE_LENGTH = 25
MIN_RACE_LENGTH = 4
ANSWER_TIME_LIMIT = 10

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%m/%d/%Y %I:%M:%S %p",
)
LOGGER = logging.getLogger(__name__)


class RegistrationError(Exception):
    pass


class WrongStateError(Exception):
    pass


class Player:
    def __init__(self, nickname):
        self.nickname = nickname
        self.answer = None
        self.answer_time = None
        self.diff_points = 0
        self.position = 1
        self.wa_streak = 0
        self.is_ready = False
        self.is_disqualified = False

    def ready(self):
        self.is_ready = True

    def unready(self):
        self.is_ready = False

    def disqualify(self):
        self.is_disqualified = True

    def reset_new_round(self):
        self.answer = None
        self.answer_time = None
        self.diff_points = 0

    def update_state(self, received_points):
        tmp = self.position
        self.position += received_points
        self.position = max(1, self.position)
        self.diff_points = self.position - tmp


class Question:
    def __init__(
        self, first_number: int, second_number: int, operator: str, answer: int
    ):
        self.first_number = first_number
        self.second_number = second_number
        self.operator = operator
        self.answer = answer

    def __str__(self):
        return f"{self.first_number};{self.operator};{self.second_number}"


class QuestionManager:
    def __init__(self):
        self.questions = []
        # TODO
        # self.operators = ["+", "-", "*", "/", "%"]
        self.operators = ["+", "-", "*", "%"]

    def generate_question(self):
        # TODO
        # first_number = random.randint(-10000, 10000)
        # second_number = random.randint(-10000, 10000)
        first_number = random.randint(1, 10)
        second_number = random.randint(1, 10)
        operator = random.choice(self.operators)

        if operator == "+":
            answer = first_number + second_number
        elif operator == "-":
            answer = first_number - second_number
        elif operator == "*":
            answer = first_number * second_number
        elif operator == "/":
            # TODO: What if the second number is 0?
            answer = first_number // second_number
        elif operator == "%":
            answer = first_number % second_number

        question = Question(first_number, second_number, operator, answer)

        return question

    def check_player_answer(self, question: Question, player_answer: int):
        return question.answer == player_answer


class PlayerManager:
    def __init__(self, max_players: int):
        self.max_players = max_players
        self.players = {}

    def check_valid_nickname(self, nickname: str) -> bool:
        return bool(re.match(r"^[a-zA-Z0-9_]{1,10}$", nickname))

    def check_existed_nickname(self, nickname: str) -> bool:
        return nickname in self.players

    def register_player(self, nickname: str) -> Player:
        if len(self.players) >= self.max_players:
            raise RegistrationError("Lobby is full.")
        if not self.check_valid_nickname(nickname):
            raise RegistrationError("Invalid nickname.")
        if self.check_existed_nickname(nickname):
            raise RegistrationError("Nickname already exists.")
        player = Player(nickname)
        self.players[player.nickname] = player
        return player

    def remove_player(self, nickname: str) -> bool:
        del self.players[nickname]

    def disqualify_players(self) -> List[Player]:
        disqualified_players = []
        for player in self.players.values():
            if player.wa_streak >= 3:
                player.disqualify()
                disqualified_players.append(player)
        return disqualified_players

    def get_all_players(self) -> List[Player]:  # all registered players
        return list(self.players.values())

    def get_readied_players(self) -> List[Player]:
        return [player for player in self.players.values() if player.is_ready]

    def pack_players_lobby_info(self) -> str:
        return ";".join(
            [f"{player.nickname},{player.is_ready}" for player in self.players.values()]
        )

    def pack_players_round_info(self) -> str:
        return ";".join(
            [
                f"{player.nickname},{player.diff_points},{player.position}"
                for player in self.players.values()
            ]
        )

    def get_qualified_players(self) -> List[Player]:  # players who are not disqualified
        return [
            player for player in self.players.values() if not player.is_disqualified
        ]

    def can_start_game(self) -> bool:
        return len(self.get_all_players()) <= self.max_players and all(
            player.is_ready for player in self.get_all_players()
        )


class GameState(Enum):
    # LOBBY: accept REGISTER, READY, UNREADY
    LOBBY = 1
    # PROCESSING: will not accept any command
    PROCESSING = 2
    # WAITING_FOR_ANSWERS: accept ANSWER
    WAITING_FOR_ANSWERS = 3


class Game:
    def __init__(self, max_players: int, race_length: int):
        self.race_length = race_length
        self.max_players = max_players
        self.reset_game()

    def reset_game(self):
        self.player_manager = PlayerManager(max_players=self.max_players)
        self.question_manager = QuestionManager()
        self.state = GameState.LOBBY

    def handle_registration(self, nickname: str) -> Player:
        if self.state != GameState.LOBBY:
            raise WrongStateError("Cannot register. Game has already started.")
        return self.player_manager.register_player(nickname)

    async def handle_ready(self, nickname: str):
        if self.state != GameState.LOBBY:
            raise WrongStateError("Cannot ready up. Game has already started.")

        self.player_manager.players[nickname].ready()
        if self.player_manager.can_start_game():
            # Start the game
            self.state = GameState.PROCESSING
            await client.broadcast(
                f"GAME_STARTING;{self.race_length};{ANSWER_TIME_LIMIT}"
            )
            asyncio.create_task(game.game_loop())

    def handle_unready(self, nickname: str):
        if self.state != GameState.LOBBY:
            raise WrongStateError("Cannot unready. Game has already started.")

        self.player_manager.players[nickname].unready()

    def handle_answer(self, nickname: str, answer: int):
        if self.state != GameState.WAITING_FOR_ANSWERS:
            raise WrongStateError("Not in answering phase.")
        LOGGER.info(f"[Game] {nickname} answered: {answer}.")

        player = self.player_manager.players[nickname]
        player.answer = answer
        player.answer_time = time.time()

    async def handle_disconnection(self, nickname: str):
        if self.state == GameState.LOBBY:
            self.player_manager.remove_player(nickname)
            await client.broadcast(f"PLAYER_LEFT;{nickname}")
        else:
            player = self.player_manager.players[nickname]
            player.disqualify()
            await client.broadcast(f"PLAYER_LEFT;{nickname}")

    def is_over(self) -> tuple[bool, Optional[Player]]:
        is_over = False
        qualified_players = self.player_manager.get_qualified_players()
        if len(qualified_players) <= 1:
            is_over = True
        else:
            for player in qualified_players:
                if player.position >= self.race_length:
                    is_over = True
                    break

        if is_over:
            winner = None
            for player in qualified_players:
                if winner is None:
                    winner = player
                elif player.position > winner.position:
                    winner = player
                elif (
                    player.position == winner.position
                    and player.answer_time < winner.answer_time
                ):
                    winner = player
            return is_over, winner

        return is_over, None

    async def game_loop(self):
        round_index = 0
        while self.state != GameState.LOBBY:
            round_index += 1
            LOGGER.info(f"[Game] Starting round {self.round_index}.")

            # Generate a new question
            for player in self.player_manager.get_qualified_players():
                player.reset_new_round()

            question = self.question_manager.generate_question()
            LOGGER.info(
                f"[Game] question #{self.round_index}: {question}, answer: {question.answer}."
            )

            # Send the question to all clients
            await client.broadcast(f"QUESTION;{self.round_index};{question}")

            self.state = GameState.WAITING_FOR_ANSWERS
            LOGGER.info("[Game] State changed: WAITING_FOR_ANSWERS.")
            # Wait for the clients to answer
            await asyncio.sleep(ANSWER_TIME_LIMIT)

            self.state = GameState.PROCESSING
            LOGGER.info("[Game] State changed: PROCESSING.")
            # Process the answers and update the scores
            fastest_player = None
            fastest_bonus = 0
            for player in self.player_manager.get_qualified_players():
                nickname = player.nickname
                answer = player.answer

                if self.question_manager.check_player_answer(question, answer):
                    # Correct answer
                    player.update_state(1)
                    player.wa_streak = 0

                    await client.write_to_player(nickname, "ANSWER_CORRECT")
                    if (
                        fastest_player is None
                        or player.answer_time < fastest_player.answer_time
                    ):
                        fastest_player = player
                    LOGGER.info(
                        f"[Game] {nickname} answered correctly, position: {player.position}."
                    )
                else:
                    # Incorrect answer
                    player.update_state(-1)
                    player.wa_streak += 1

                    fastest_bonus += 1
                    await client.write_to_player(nickname, "ANSWER_INCORRECT")
                    LOGGER.info(
                        f"[Game] {nickname} answered incorrectly, position: {player.position}."
                    )

            # Add bonus score for the fastest player
            if fastest_player is not None:
                fastest_player.update_state(fastest_bonus)
                LOGGER.info(
                    f"[Game] Fastest player: {fastest_player.nickname}, bonus: {fastest_bonus}."
                )

            # Disqualify players with consecutive wrong answers
            disqualified_players = self.player_manager.disqualify_players()
            if disqualified_players:
                disqualified_players = ";".join(
                    str(player) for player in disqualified_players
                )
                await client.broadcast(f"NOTIFICATION;{disqualified_players}")
                LOGGER.info(f"[Game] Disqualified players: {disqualified_players}.")

            # Send the updated scores to all clients
            scores = self.player_manager.pack_players_round_info()
            await client.broadcast(f"SCORES;{scores}")

            # Check if the game is over
            is_over, winner = self.is_over()
            if is_over:
                await client.broadcast("GAME_OVER")
                if winner is not None:
                    await client.broadcast(f"WINNER;{winner.nickname}")
                    LOGGER.info(f"[Game] Game over. Winner is {winner.nickname}.")
                else:
                    await client.broadcast("WINNER;")
                    LOGGER.info("[Game] Game over. No winner.")
                self.reset_game()
                client.reset_clients()


class ClientManager:
    def __init__(self):
        self.clients = {}

    def reset_clients(self):
        self.clients = {}

    async def broadcast(self, message, except_nicknames=[]):
        byte_message = (message + "\n").encode()
        for client in self.clients:
            if self.clients[client] not in except_nicknames:
                client.write(byte_message)
                await client.drain()  # Ensure the message is sent before continuing

    async def write_to_player(self, nickname, message):
        if nickname not in game.player_manager.players:
            return
        byte_message = (message + "\n").encode()
        writer = game.player_manager.players[nickname].writer
        writer.write(byte_message)
        await writer.drain()

    async def handle_conversation(self, reader, writer):
        try:
            address = writer.get_extra_info("peername")
            LOGGER.info(f"[Client] Accepted connection from {address}.")
            while True:
                data = await reader.readline()
                if not data:
                    break
                message = data.decode().strip()
                command, *args = message.split(";")
                command = command.upper()

                LOGGER.info(f"[Client] Received message from {address}: {message}")

                if command == "REGISTER":
                    # Parse message data
                    nickname = args[0].strip()

                    # Handle command
                    try:
                        if writer in self.clients:
                            raise RegistrationError("You have already registered.")

                        player = game.handle_registration(nickname)
                        player.writer = writer
                        self.clients[writer] = nickname

                        writer.write(
                            f"REGISTRATION_SUCCESS;{game.player_manager.pack_players_lobby_info()}\n".encode()
                        )
                        await client.broadcast(f"PLAYER_JOINED;{nickname}")
                        LOGGER.info(f"[Client] Registered as {nickname}")

                    except RegistrationError as e:
                        writer.write(f"REGISTRATION_FAILURE;{str(e)}\n".encode())
                    except WrongStateError as e:
                        writer.write(f"REGISTRATION_FAILURE;{str(e)}\n".encode())

                elif command == "READY":
                    try:
                        # Handle command
                        nickname = self.clients[writer]
                        await game.handle_ready(nickname)

                        await client.broadcast(f"PLAYER_READY;{nickname}")
                        LOGGER.info(f"[Client] {nickname} is ready.")

                    except WrongStateError as e:
                        writer.write(f"READY_FAILURE;{str(e)}\n".encode())

                elif command == "UNREADY":
                    try:
                        # Handle command
                        nickname = self.clients[writer]
                        game.handle_unready(nickname)

                        await client.broadcast(f"PLAYER_UNREADY:{nickname}")
                        LOGGER.info(f"[Client] {nickname} is unready.")

                    except WrongStateError as e:
                        writer.write(f"UNREADY_FAILURE;{str(e)}\n".encode())

                elif command == "ANSWER":
                    try:
                        player_answer = int(args[0].strip())

                        # Handle command
                        nickname = self.clients[writer]
                        game.handle_answer(nickname, player_answer)
                        LOGGER.info(f"[Client] {nickname} answered: {player_answer}.")

                    except WrongStateError as e:
                        writer.write(f"ANSWER_FAILURE;{str(e)}\n".encode())

                await writer.drain()
        except ConnectionResetError as e:
            LOGGER.info(f"[Client] Connection reset by peer, address {address}.")
        finally:
            nickname = self.clients[writer]
            del self.clients[writer]
            await game.handle_disconnection(nickname)
            writer.close()


game = Game(10, 3)
client = ClientManager()


if __name__ == "__main__":
    address = ("localhost", 54321)
    loop = asyncio.get_event_loop()
    coro = asyncio.start_server(client.handle_conversation, *address)
    server = loop.run_until_complete(coro)
    print("Listening at {}".format(address))
    try:
        loop.run_forever()
    finally:
        server.close()
        loop.close()
