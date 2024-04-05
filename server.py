from typing import List
import socket
import select
import random
import time
import re

MAX_PLAYERS = 10
MIN_PLAYERS = 2
MAX_RACE_LENGTH = 25
MIN_RACE_LENGTH = 4


class Player:
    def __init__(self, nickname):
        self.nickname = nickname
        self.answer = None
        self.answer_time = None
        self.diff_points = 0
        self.position = 0
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
        self.position = max(0, self.position)
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
        self.operators = ["+", "-", "*", "/", "%"]

    def generate_question(self):
        first_number = random.randint(-10000, 10000)
        second_number = random.randint(-10000, 10000)
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


class RegistrationError(Exception):
    pass


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

    def pack_players_info(self) -> str:
        return ";".join(
            [
                f"{player.nickname},{player.score},{player.position}"
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
        self.max_players = max_players
        self.race_length = race_length

        self.player_manager = PlayerManager(max_players=self.max_players)
        self.question_manager = QuestionManager()
        self.timer = Timer()
        self.setup(host, port)
        self.state = GameState.LOBBY

    def create_game(self, num_players: int, race_length: int):
        pass

    def run_game(self):
        pass

    def broadcast(self, message: str):
        pass

    def handle_registration(self, nickname) -> Player:
        self.player_manager.register_player(nickname)


clients = {}
game = Game()


async def game_loop():
    while game.state != GameState.GAME_OVER:
        # Generate a new question
        question = game.question_manager.generate_question()

        # Send the question to all clients
        await broadcast(f"QUESTION;{question}\n".encode())

        game.state = GameState.WAITING_FOR_ANSWERS
        # Wait for 5 seconds for the clients to answer
        await asyncio.sleep(5)
        game.state = GameState.FINISHED

        # Process the answers and update the scores
        for client, player in clients.items():
            answer = player.answer  # assuming you have a way to get the player's answer
            if game.question_manager.check_answer(question, answer):
                player.update_score(1)  # assuming correct answers are worth 1 point
                await client.write(b"ANSWER_CORRECT\n")
            else:
                await client.write(b"ANSWER_INCORRECT\n")

        # Send the updated scores to all clients
        scores = game.player_manager.create_players_info_message()
        await broadcast(f"SCORES;{scores}\n".encode())

        # Check if the game is over
        if game.is_over():  # assuming you have a way to check if the game is over
            game.state = GameState.GAME_OVER
            await broadcast(b"GAME_OVER\n")


async def handle_conversation(reader, writer):
    try:
        address = writer.get_extra_info("peername")
        print("Accepted connection from {}".format(address))
        while True:
            data = await reader.readline()
            message = data.decode().strip()
            command, *args = message.split(";")

            if command == "REGISTER":
                # Register can only be called in the LOBBY state
                if game.state != GameState.LOBBY:
                    await writer.write(
                        b"REGISTRATION_FAILURE;A game has already started\n"
                    )
                    continue

                # Parse message data
                nickname = args[0]

                # Handle command
                try:
                    player = game.player_manager.register_player(nickname)
                    clients[writer] = player
                    await writer.write(b"REGISTRATION_SUCCESS\n")
                except RegistrationError as e:
                    await writer.write(f"REGISTRATION_FAILURE;{str(e)}\n".encode())

            elif command == "READY":
                # Ready can only be called in the LOBBY state
                if game.state != GameState.LOBBY:
                    await writer.write(b"READY_FAILURE;A game has already started\n")
                    continue

                # Parse message data
                # Handle command
                player = game.clients[writer]
                player.is_ready = True
                broadcast(f"PLAYER_JOINED:{player.nickname}".encode())
                if game.check_all_ready():
                    game.state = GameState.STARTING
                    broadcast(
                        f"GAME_STARTING:{game.get_race_length()}:{game.wait_time}".encode()
                    )
                    asyncio.create_task(game_loop())

            elif command == "UNREADY":
                # Unready can only be called in the LOBBY state
                if game.state != GameState.LOBBY:
                    await writer.write(b"UNREADY_FAILURE;A game has already started\n")
                    continue
                # Parse message data
                # Handle command
                player = game.clients[writer]
                player.is_ready = True
                broadcast(f"PLAYER_LEFT:{player.nickname}".encode())
                pass

            elif command == "ANSWER":
                # Answer can only be called in the IN_PROGRESS state
                if game.state != GameState.IN_PROGRESS:
                    await writer.write(b"ANSWER_FAILURE;No game is in progress\n")
                    continue

                # Parse message data
                if len(args) != 1:
                    await writer.write(b"ANSWER_FAILURE;Invalid number of arguments\n")
                    continue
                player_answer = args[0]

                # Handle command
                player = game.clients[writer]
                question = game.current_question
                if game.question_manager.check_answer(question, player_answer):
                    player.update_score(1)
                    player.consecutive_wa = 0
                    player.update_position(1)

                pass

            await writer.drain()
    finally:
        del clients[writer]
        # TODO
        # game.player_manager.remove_player(player)
        writer.close()
        await writer.wait_closed()


async def broadcast(message):
    for client in clients:
        client.write(message)
        await client.drain()  # Ensure the message is sent before continuing


if __name__ == "__main__":
    address = ("127.0.0.1", 54321)
    loop = asyncio.get_event_loop()
    coro = asyncio.start_server(handle_conversation, *address)
    server = loop.run_until_complete(coro)
    print("Listening at {}".format(address))
    try:
        loop.run_forever()
    finally:
        server.close()
        loop.close()
