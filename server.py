from typing import List, Dict, Tuple
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
ANSWER_TIME_LIMIT = 3

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(message)s",
    datefmt="%m/%d/%Y %H:%M:%S",
)
LOGGER = logging.getLogger(__name__)


class RegistrationError(Exception):
    pass


class WrongStateError(Exception):
    pass


class Player:
    def __init__(self, nickname: str):
        self.nickname: str = nickname
        self.answer: Optional[str] = None
        self.answer_time: Optional[float] = None
        self.diff_points: int = 0
        self.position: int = 1
        self.wa_streak: int = 0
        self.is_ready: bool = False
        self.is_disqualified: bool = False

    def ready(self) -> None:
        self.is_ready = True

    def unready(self) -> None:
        self.is_ready = False

    def disqualify(self) -> None:
        self.is_disqualified = True

    def reset_new_round(self) -> None:
        self.answer = None
        self.answer_time = None
        self.diff_points = 0

    def update_state(self, received_points: int) -> None:
        tmp: int = self.position
        self.position += received_points
        self.position = max(1, self.position)
        self.diff_points = self.position - tmp


class Question:
    def __init__(
        self, first_number: int, second_number: int, operator: str, answer: int
    ):
        self.first_number: int = first_number
        self.second_number: int = second_number
        self.operator: str = operator
        self.answer: int = answer

    def __str__(self) -> str:
        return f"{self.first_number};{self.operator};{self.second_number}"


class QuestionManager:
    def __init__(self):
        self.operators: List[str] = ["+", "-", "*", "/", "%"]

    def generate_question(self) -> Question:
        first_number: int = random.randint(-10000, 10000)
        second_number: int = random.randint(-10000, 10000)
        operator: str = random.choice(self.operators)

        answer: int = 0
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
        else:
            raise ValueError("Invalid operator.")

        return Question(first_number, second_number, operator, answer)

    def check_player_answer(self, question: Question, player_answer: int) -> bool:
        return question.answer == player_answer


class PlayerManager:
    def __init__(self, max_players: int):
        self.max_players: int = max_players
        self.players: Dict[str, Player] = {}

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

    def remove_player(self, nickname: str) -> None:
        del self.players[nickname]

    def disqualify_players(self) -> List[Player]:
        disqualified_players: List[Player] = []
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
        self.race_length: int = race_length
        self.max_players: int = max_players
        self.reset_game()

    def reset_game(self) -> None:
        self.player_manager: PlayerManager = PlayerManager(self.max_players)
        self.question_manager: QuestionManager = QuestionManager()
        self.state: GameState = GameState.LOBBY

    def handle_registration(self, nickname: str) -> Player:
        if self.state != GameState.LOBBY:
            raise WrongStateError("Cannot register. Game has already started.")
        return self.player_manager.register_player(nickname)

    async def handle_ready(self, nickname: str) -> None:
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

    def handle_unready(self, nickname: str) -> None:
        if self.state != GameState.LOBBY:
            raise WrongStateError("Cannot unready. Game has already started.")

        self.player_manager.players[nickname].unready()

    def handle_answer(self, nickname: str, answer: int) -> None:
        if self.state != GameState.WAITING_FOR_ANSWERS:
            raise WrongStateError("Not in answering phase.")
        LOGGER.info(f"[Game Thread] {nickname} answered: {answer}.")

        player: Player = self.player_manager.players[nickname]
        player.answer = answer
        player.answer_time = time.time()

    async def handle_disconnection(self, nickname: str) -> None:
        if self.state == GameState.LOBBY:
            self.player_manager.remove_player(nickname)
        else:
            player: Player = self.player_manager.players[nickname]
            player.disqualify()
        await client.broadcast(f"PLAYER_LEFT;{nickname}")

    def is_over(self) -> Tuple[bool, Optional[Player]]:
        is_over: bool = False
        qualified_players: List[Player] = self.player_manager.get_qualified_players()
        if len(qualified_players) <= 1:
            is_over = True
        else:
            for player in qualified_players:
                if player.position >= self.race_length:
                    is_over = True
                    break

        if is_over:
            winner: Optional[Player] = None
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
        round_index: int = 0
        while self.state != GameState.LOBBY:
            round_index += 1
            LOGGER.info(f"[Game Thread] Starting round {round_index}.")

            # Generate a new question
            for player in self.player_manager.get_qualified_players():
                player.reset_new_round()

            question: Question = self.question_manager.generate_question()
            LOGGER.info(
                f"[Game Thread] Question #{round_index}: {question.first_number} {question.operator} {question.second_number} = {question.answer}."
            )

            # Send the question to all clients
            await client.broadcast(f"QUESTION;{round_index};{question}")

            self.state = GameState.WAITING_FOR_ANSWERS
            LOGGER.info("[Game Thread] State changed: WAITING_FOR_ANSWERS.")
            # Wait for the clients to answer
            # TODO: What if all players answered before the time limit?
            await asyncio.sleep(ANSWER_TIME_LIMIT)

            self.state = GameState.PROCESSING
            LOGGER.info("[Game Thread] State changed: PROCESSING.")
            # Process the answers and update the scores
            fastest_player: Optional[Player] = None
            fastest_bonus: int = 0
            for player in self.player_manager.get_qualified_players():
                nickname: str = player.nickname
                answer: Optional[int] = player.answer

                if self.question_manager.check_player_answer(question, answer):
                    # Correct answer
                    player.update_state(1)
                    player.wa_streak = 0

                    await client.write_to_player(
                        nickname, f"ANSWER_CORRECT;{question.answer}"
                    )
                    if (
                        fastest_player is None
                        or player.answer_time < fastest_player.answer_time
                    ):
                        fastest_player = player
                    LOGGER.info(
                        f"[Game Thread] {nickname} answered correctly, position: {player.position}."
                    )
                else:
                    # Incorrect answer
                    player.update_state(-1)
                    player.wa_streak += 1

                    fastest_bonus += 1
                    await client.write_to_player(
                        nickname, f"ANSWER_INCORRECT;{question.answer}"
                    )
                    LOGGER.info(
                        f"[Game Thread] {nickname} answered incorrectly, position: {player.position}."
                    )

            # Add bonus score for the fastest player
            if fastest_player is not None:
                fastest_player.update_state(fastest_bonus)
                LOGGER.info(
                    f"[Game Thread] Fastest player: {fastest_player.nickname}, bonus: {fastest_bonus}."
                )

            # Disqualify players with consecutive wrong answers
            disqualified_players: List[Player] = (
                self.player_manager.disqualify_players()
            )
            if disqualified_players:
                disqualified_players = ";".join(
                    player.nickname for player in disqualified_players
                )
                await client.broadcast(f"DISQUALIFICATION;{disqualified_players}")
                LOGGER.info(
                    f"[Game Thread] Disqualified players: {disqualified_players}."
                )

            # Send the updated scores to all clients
            scores: str = self.player_manager.pack_players_round_info()
            await client.broadcast(f"SCORES;{fastest_player or ''};{scores}")
            # TODO: Wait for a few seconds before starting the next round

            # Check if the game is over
            is_over: bool
            winner: Optional[Player]
            is_over, winner = self.is_over()
            if is_over:
                await client.broadcast(f"GAME_OVER;{winner or ''}")
                LOGGER.info(
                    f"[Game Thread] Game over. Winner is {winner.nickname or ''}."
                )
                self.reset_game()
                client.reset_clients()


class ClientManager:
    def __init__(self):
        self.clients: Dict[asyncio.StreamWriter, str] = {}

    def reset_clients(self) -> None:
        self.clients = {}

    async def broadcast(self, message: str, except_nicknames: List[str] = []) -> None:
        byte_message: bytes = (message + "\n").encode()
        for client in self.clients:
            if self.clients[client] not in except_nicknames:
                client.write(byte_message)
                await client.drain()  # Ensure the message is sent before continuing

    async def write_to_player(self, nickname: str, message: str) -> None:
        if nickname not in game.player_manager.players:
            return
        byte_message: bytes = (message + "\n").encode()
        writer: asyncio.StreamWriter = game.player_manager.players[nickname].writer
        writer.write(byte_message)
        await writer.drain()

    async def handle_conversation(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        try:
            address: Tuple[str, int] = writer.get_extra_info("peername")
            LOGGER.info(f"[Client Thread] Accepted connection from {address}.")
            while True:
                data: bytes = await reader.readline()
                if not data:
                    break
                message: str = data.decode().strip()
                command: str
                args: List[str]
                command, *args = message.split(";")
                command = command.upper()

                LOGGER.info(
                    f"[Client Thread] Received message from {address}: {message}"
                )

                if command == "REGISTER":
                    # Parse message data
                    nickname: str = args[0].strip()

                    # Handle command
                    try:
                        if writer in self.clients:
                            raise RegistrationError("You have already registered.")

                        player: Player = game.handle_registration(nickname)
                        player.writer: asyncio.StreamWriter = writer
                        self.clients[writer] = nickname

                        writer.write(
                            f"REGISTRATION_SUCCESS;{game.player_manager.pack_players_lobby_info()}\n".encode()
                        )
                        await client.broadcast(f"PLAYER_JOINED;{nickname}")
                        LOGGER.info(f"[Client Thread] Registered as {nickname}")

                    except RegistrationError as e:
                        writer.write(f"REGISTRATION_FAILURE;{str(e)}\n".encode())
                    except WrongStateError as e:
                        writer.write(f"REGISTRATION_FAILURE;{str(e)}\n".encode())

                elif command == "READY":
                    try:
                        # Handle command
                        nickname: str = self.clients[writer]
                        await game.handle_ready(nickname)

                        await client.broadcast(f"PLAYER_READY;{nickname}")
                        LOGGER.info(f"[Client Thread] {nickname} is ready.")

                    except WrongStateError as e:
                        writer.write(f"READY_FAILURE;{str(e)}\n".encode())

                elif command == "UNREADY":
                    try:
                        # Handle command
                        nickname: str = self.clients[writer]
                        game.handle_unready(nickname)

                        await client.broadcast(f"PLAYER_UNREADY:{nickname}")
                        LOGGER.info(f"[Client Thread] {nickname} is unready.")

                    except WrongStateError as e:
                        writer.write(f"UNREADY_FAILURE;{str(e)}\n".encode())

                elif command == "ANSWER":
                    try:
                        player_answer: int = int(args[0].strip())

                        # Handle command
                        nickname: str = self.clients[writer]
                        game.handle_answer(nickname, player_answer)
                        LOGGER.info(
                            f"[Client Thread] {nickname} answered: {player_answer}."
                        )

                    except WrongStateError as e:
                        writer.write(f"ANSWER_FAILURE;{str(e)}\n".encode())

                await writer.drain()
        except ConnectionResetError as e:
            LOGGER.info(f"[Client Thread] Connection reset by peer, address {address}.")
        finally:
            nickname: str = self.clients[writer]
            del self.clients[writer]
            await game.handle_disconnection(nickname)
            writer.close()


game: Game = Game(10, 3)
client: ClientManager = ClientManager()


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
