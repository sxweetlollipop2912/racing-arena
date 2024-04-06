import re
from typing import Optional, Dict, List


class RegistrationError(Exception):
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
