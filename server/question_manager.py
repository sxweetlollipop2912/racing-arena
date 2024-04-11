import random
from typing import List


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
        # TODO
        # lrange = -10000
        # rrange = 10000
        lrange = 1
        rrange = 8
        operator: str = random.choice(self.operators)
        if operator == "/":
            second_number = 0
            while second_number == 0:
                second_number = random.randint(lrange, rrange)
            first_number = second_number * random.randint(lrange, rrange)
        elif operator == "%":
            second_number = 0
            while second_number == 0:
                second_number = random.randint(lrange, rrange)
            first_number = random.randint(lrange, rrange)
        else:
            first_number = random.randint(lrange, rrange)
            second_number = random.randint(lrange, rrange)

        answer: int = 0
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
        else:
            raise ValueError("Invalid operator.")

        return Question(first_number, second_number, operator, answer)

    def check_player_answer(self, question: Question, player_answer: int) -> bool:
        return question.answer == player_answer
