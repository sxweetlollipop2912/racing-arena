class Player:
    def __init__(self, nickname: str, is_ready: bool = False):
        self.nickname: str = nickname
        self.diff_points: int = 0
        self.position: int = 1
        self.is_ready: bool = is_ready
        self.is_disqualified: bool = False
