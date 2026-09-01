class RuleNotRegisteredError(Exception):
    """Exception raised when a rule is not registered in registry class."""

    def __init__(self, name: str) -> None:
        super().__init__(f"Rule '{name}' is not registered")


class RuleAlreadyRegisteredError(Exception):
    """Exception raised when a rule is already registered in registry class."""

    def __init__(self, name: str) -> None:
        super().__init__(f"Rule '{name}' is already registered")


class RuleKeyDoesNotExistError(Exception):
    """Exception raised when a key does not exist in the object of rule."""

    def __init__(self, key: str, rule_name: str) -> None:
        super().__init__(f"Key '{key}' does not exist in the object of rule '{rule_name}'")


class CompilationError(Exception):
    """Exception raised when a rule compilation fails."""


class ProcessArgumentError(Exception):
    """Exception raised when a process argument fails in registry class."""
