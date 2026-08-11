class RuleAlreadyRegisteredError(Exception):
    def __init__(self, name: str) -> None:
        super().__init__(f"Rule '{name}' is already registered")


class RuleNotRegisteredError(Exception):
    def __init__(self, name: str) -> None:
        super().__init__(f"Rule '{name}' is not registered")
