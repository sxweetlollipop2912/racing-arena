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
