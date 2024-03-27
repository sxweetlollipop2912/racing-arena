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
        self.score = 0
        self.position = 0
        self.consecutive_wa = 0
        self.is_ready = False
        self.is_disqualified = False
        self.last_position = -1

    def disqualify(self):
        self.is_disqualified = True

    def reset(self):
        self.score = 0
        self.position = 0
        self.consecutive_wa = 0
        self.is_ready = False
        self.is_disqualified = False
        self.last_position = -1

    def __str__(self):
        return f"Player {self.nickname} - {self.score} points"

    def __repr__(self):
        return f"Player {self.nickname} - {self.score} points"

    def update_position(self, value):
        self.position += value
        self.position = max(0, self.position)

    def update_score(self, value):
        self.score += value


class Question:
    def __init__(
        self, first_number: int, second_number: int, operator: str, answer: int
    ):
        self.first_number = first_number
        self.second_number = second_number
        self.operator = operator
        self.answer = answer

    def __str__(self):
        return f"Question: {self.first_number} {self.operator} {self.second_number} = {self.answer}"

    def __repr__(self):
        return f"Question: {self.first_number} {self.operator} {self.second_number} = {self.answer}"


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
            answer = first_number // second_number
        elif operator == "%":
            answer = first_number % second_number

        question = Question(first_number, second_number, operator, answer)
        self.questions.append(question)

        return question

    def check_answer(self, question: Question, answer: int):
        return question.answer == answer


class Timer:
    def __init__(self):
        self.start_time = None
        self.end_time = None

    def start(self):
        self.start_time = time.time()

    def stop(self):
        self.end_time = time.time()

    def get_elapsed_time(self):
        return self.end_time - self.start_time

    def reset(self):
        self.start_time = None
        self.end_time = None


class PlayerManager:
    def __init__(self, min_players: int, max_players: int):
        self.min_players = min_players
        self.max_players = max_players
        self.players = []

    def check_valid_nickname(self, nickname: str) -> bool:
        return bool(re.match(r"^[a-zA-Z0-9_]{1,10}$", nickname))

    def check_existed_nickname(self, nickname: str) -> bool:
        return nickname in [player.nickname for player in self.players]

    def register_player(self, nickname: str) -> Player:
        if self.check_valid_nickname(nickname):
            player = Player(nickname)
            self.players.append(player)
            return player
        return None

    def add_player(self, player: Player) -> bool:
        if len(self.players) < self.max_players:
            self.players.append(player)
            return True
        return False

    def remove_player(self, player: Player) -> bool:
        self.players.remove(player)

    def disqualify_player(self, player: Player):
        player.disqualify()
        broadcast(f"{player.nickname} has been disqualified.")

    def get_all_players(self) -> List[Player]:  # all players in the room
        return self.players

    def get_readied_players(
        self,
    ) -> List[Player]:  # players who pressed the ready button
        return [player for player in self.players if player.is_ready]

    def get_eligible_players(self) -> List[Player]:  # players who are not disqualified
        return [player for player in self.players if not player.is_disqualified]

    def can_start_game(self) -> bool:
        return len(self.get_all_players()) >= self.min_players

    def check_all_ready(self) -> bool:
        return all([player.is_ready for player in self.get_all_players()])


class Server:
    def __init__(self, host: str, port: int):
        self.connection = None
        self.max_players = MAX_PLAYERS
        self.min_players = MIN_PLAYERS
        self.max_race_length = MAX_RACE_LENGTH
        self.min_race_length = MIN_RACE_LENGTH

        self.player_manager = PlayerManager(
            min_players=self.min_players, max_players=self.max_players
        )
        self.question_manager = QuestionManager()
        self.timer = Timer()
        self.setup(host, port)

    def setup(self, host: str, port: int):
        # setup a non-blocking TCP socket
        self.connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # self.connection.setblocking(0)
        self.connection.bind((host, port))

    def create_game(self, num_players: int, race_length: int):
        pass

    def run_game(self):
        pass

    def receive_message(self):
        pass

    def severe_all_connections(self):
        pass

    def broadcast(self, message: str):
        pass

    def run(self):
        print(f"Server is running on localhost:12345")
        self.connection.listen(1)
        while True:
            # Use select to wait for a connection
            readable, _, _ = select.select([self.connection], [], [], 1)
            if readable:
                conn, addr = self.connection.accept()
                print(f"Connection from {addr}")
                self.handle_registration(conn)

    def handle_registration(self, conn):
        # Receive the registration request
        print(f"HERE")
        data = conn.recv(1024)
        print(f"Received data: {data}")
        if data:
            import json

            # Decode the data from bytes to a string
            data_str = data.decode("utf-8")

            # Parse the string as JSON
            data_json = json.loads(data_str)

            # Extract the "name" field from the JSON object
            nickname = data_json["name"]
            player = self.player_manager.register_player(nickname)
            if player:
                print(f"Player {nickname} registered successfully.")
                conn.sendall(b"Registration successful.")
            else:
                print(f"Registration failed for nickname: {nickname}")
                conn.sendall(b"Registration failed.")
        conn.close()


if __name__ == "__main__":
    server = Server("localhost", 12345)
    server.run()
