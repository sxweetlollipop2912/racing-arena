import time
import asyncio
from enum import Enum
import logging
from asyncio import StreamWriter, StreamReader
from typing import Tuple, List, Dict, Optional
import argparse

from exceptions import RegistrationError, WrongStateError
from player_manager import Player, PlayerManager
from question_manager import Question, QuestionManager

ANSWER_TIME_LIMIT = 30
PREPARE_TIME_LIMIT = 10

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(message)s",
    datefmt="%m/%d/%Y %H:%M:%S",
)
LOGGER = logging.getLogger(__name__)


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
                f"GAME_STARTING;{self.race_length};{ANSWER_TIME_LIMIT};{PREPARE_TIME_LIMIT}"
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
        await client.broadcast(f"PLAYER_LEFT;{nickname}", [nickname])

    def is_over(self) -> Tuple[bool, Optional[Player]]:
        is_over: bool = False
        qualified_players: List[Player] = self.player_manager.get_qualified_players()
        if len(qualified_players) == 0:
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

            self.state = GameState.PROCESSING
            await asyncio.sleep(PREPARE_TIME_LIMIT)

            question: Question = self.question_manager.generate_question()
            LOGGER.info(
                f"[Game Thread] Question #{round_index}: {question.first_number} {question.operator} {question.second_number} = {question.answer}."
            )

            # Send the question to all clients
            await client.broadcast(f"QUESTION;{round_index};{question}")

            self.state = GameState.WAITING_FOR_ANSWERS
            LOGGER.info("[Game Thread] State changed: WAITING_FOR_ANSWERS.")
            # Wait for the clients to answer
            await asyncio.sleep(ANSWER_TIME_LIMIT)

            self.state = GameState.PROCESSING
            LOGGER.info("[Game Thread] State changed: PROCESSING.")
            # Process the answers and update the scores
            fastest_player: Optional[Player] = None
            fastest_bonus: int = 0
            for player in self.player_manager.players.values():
                if not player.is_disqualified:
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
                else:
                    nickname: str = player.nickname
                    await client.write_to_player(nickname, f"ANSWER;{question.answer}")

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
                packed_disqualified_players = ";".join(
                    player.nickname for player in disqualified_players
                )
                await client.broadcast(
                    f"DISQUALIFICATION;{packed_disqualified_players}"
                )
                LOGGER.info(
                    f"[Game Thread] Disqualified players: {packed_disqualified_players}."
                )

            # Send the updated scores to all clients
            scores: str = self.player_manager.pack_players_round_info()
            fastest_player_nickname = (
                fastest_player.nickname if fastest_player else None
            )
            await client.broadcast(f"SCORES;{fastest_player_nickname or ''};{scores}")

            # Check if the game is over
            is_over: bool
            winner: Optional[Player]
            is_over, winner = self.is_over()
            winner_nickname = winner.nickname if winner else None
            if is_over:
                await client.broadcast(f"GAME_OVER;{winner_nickname or ''}")
                LOGGER.info(
                    f"[Game Thread] Game over. Winner is {winner_nickname or ''}."
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
        player = game.player_manager.players.get(nickname)
        if player and player.writer:
            byte_message: bytes = (message + "\n").encode()
            writer: asyncio.StreamWriter = player.writer
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
                    if len(args) != 1:
                        writer.write(b"REGISTRATION_FAILURE;Invalid arguments.\n")
                        continue

                    # Parse message data
                    nickname: str = args[0].strip()

                    # Handle command
                    try:
                        if writer in self.clients:
                            raise RegistrationError("You have already registered.")

                        player: Player = game.handle_registration(nickname)
                        player.writer = writer
                        self.clients[writer] = nickname

                        writer.write(
                            f"REGISTRATION_SUCCESS;{game.player_manager.pack_players_lobby_info()}\n".encode()
                        )
                        await client.broadcast(f"PLAYER_JOINED;{nickname}", [nickname])
                        LOGGER.info(f"[Client Thread] Registered as {nickname}")

                    except RegistrationError as e:
                        writer.write(f"REGISTRATION_FAILURE;{str(e)}\n".encode())
                    except WrongStateError as e:
                        writer.write(f"REGISTRATION_FAILURE;{str(e)}\n".encode())

                elif command == "READY":
                    if len(args) != 0:
                        writer.write(b"READY_FAILURE;Invalid arguments.\n")
                        continue

                    try:
                        # Handle command
                        nickname: str = self.clients[writer]
                        await game.handle_ready(nickname)

                        await client.broadcast(f"PLAYER_READY;{nickname}", [nickname])
                        LOGGER.info(f"[Client Thread] {nickname} is ready.")

                    except WrongStateError as e:
                        writer.write(f"READY_FAILURE;{str(e)}\n".encode())

                elif command == "UNREADY":
                    if len(args) != 0:
                        writer.write(b"UNREADY_FAILURE;Invalid arguments.\n")
                        continue

                    try:
                        # Handle command
                        nickname: str = self.clients[writer]
                        game.handle_unready(nickname)

                        await client.broadcast(f"PLAYER_UNREADY;{nickname}", [nickname])
                        LOGGER.info(f"[Client Thread] {nickname} is unready.")

                    except WrongStateError as e:
                        writer.write(f"UNREADY_FAILURE;{str(e)}\n".encode())

                elif command == "ANSWER":
                    if len(args) != 1:
                        writer.write(b"ANSWER_FAILURE;Invalid arguments.\n")
                        continue

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
        except Exception as e:
            LOGGER.info(
                f"[Client Thread] Exception occurred with peer connection, address {address}: {str(e)}."
            )
        finally:
            LOGGER.info(f"[Client Thread] Closing connection with {address}.")
            if writer in self.clients:
                nickname: str = self.clients[writer]
                del self.clients[writer]
            await game.handle_disconnection(nickname)

            player = game.player_manager.players.get(nickname)
            if player:
                player.writer = None

            writer.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Server for Racing Arena")
    parser.add_argument(
        "-p",
        "--players",
        type=int,
        default=10,
        help="Set the maximum number of players Default to 10.",
    )
    parser.add_argument(
        "-r",
        "--race-length",
        type=int,
        default=10,
        help="Set the race length. Default to 10.",
    )
    parser.add_argument(
        "-t",
        "--time-answer",
        type=int,
        default=ANSWER_TIME_LIMIT,
        help=f"Set the answer time limit. Default to {ANSWER_TIME_LIMIT} (seconds).",
    )
    args = parser.parse_args()

    max_players = args.players
    race_length = args.race_length
    ANSWER_TIME_LIMIT = args.time_answer

    game: Game = Game(max_players, race_length)
    client: ClientManager = ClientManager()
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
