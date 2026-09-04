import re
from collections.abc import Iterable


class RuleDoesNotExistError(Exception):
    """Exception raised when a rule does not exist."""

    def __init__(self, name: str, available_rules: Iterable[str] | None = None) -> None:
        msg = f"Rule '{name}' does not exist."

        if available_rules is not None:
            msg += f" Available rules: {', '.join(available_rules)}"

        super().__init__(msg)


class RuleAlreadyRegisteredError(Exception):
    """Exception raised when a rule is already registered in registry class."""

    def __init__(self, name: str) -> None:
        super().__init__(f"Rule '{name}' is already registered")


class RuleKeyDoesNotExistError(Exception):
    """Exception raised when a key does not exist in the object of rule."""

    def __init__(self, key: str, rule_name: str) -> None:
        super().__init__(f"Key '{key}' does not exist in the object of rule '{rule_name}'")


class ArgumentError(TypeError):
    pass


class MissingArgumentError(ArgumentError):
    """Exception raised when a required argument is missing."""


def is_missing_argument_exception(e: TypeError) -> bool:
    return (
        re.search(r"missing \d+ required positional argument", e.args[0]) is not None
        or re.search(r" missing \d+ required keyword-only argument", e.args[0]) is not None
    )


class UnexpectedKeywordArgumentError(ArgumentError):
    """Exception raised when an unexpected keyword argument is passed."""


def is_unexpected_keyword_argument_exception(e: TypeError) -> bool:
    return re.search(r"got an unexpected keyword argument", e.args[0]) is not None


class TooManyArgumentsError(ArgumentError):
    """Exception raised when too many arguments are passed."""


def is_too_many_arguments_exception(e: TypeError) -> bool:
    return re.search(r"takes \d+ positional arguments? but \d+ were given", e.args[0]) is not None


class ProcessArgumentError(ArgumentError):
    """Exception raised when a process argument fails in registry class."""
