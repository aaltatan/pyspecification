from typing import Literal


class RuleNotFoundError(Exception):
    def __init__(self, name: str, kind: Literal["registered", "found"]) -> None:
        super().__init__(f"Rule '{name}' is not {kind}")
