class RuleNotFoundError(Exception):
    def __init__(self, name: str) -> None:
        super().__init__(f"Rule '{name}' is not found")


class RuleNotRegisteredError(Exception):
    def __init__(self, name: str) -> None:
        super().__init__(f"Rule '{name}' is not registered")


class RuleAlreadyRegisteredError(Exception):
    def __init__(self, name: str) -> None:
        super().__init__(f"Rule '{name}' is already registered")


class RuleKeyDoesNotExistError(Exception):
    def __init__(self, key: str, rule_name: str) -> None:
        super().__init__(f"Key '{key}' does not exist in the object of rule '{rule_name}'")
