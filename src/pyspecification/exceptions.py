import re
from collections.abc import Iterable


class PySpecificationError(Exception):
    """Base class for all PySpecification exceptions."""


class RuleDoesNotExistError(PySpecificationError):
    """Exception raised when a rule does not exist."""

    def __init__(self, name: str, available_rules: Iterable[str] | None = None) -> None:
        msg = f"Rule '{name}' does not exist."

        if available_rules is not None:
            msg += f" Available rules: {', '.join(available_rules)}"

        super().__init__(msg)


class RuleAlreadyRegisteredError(PySpecificationError):
    """Exception raised when a rule is already registered in registry class."""

    def __init__(self, name: str) -> None:
        super().__init__(f"Rule '{name}' is already registered")


class RuleKeyDoesNotExistError(PySpecificationError):
    """Exception raised when a key does not exist in the object of rule."""

    def __init__(self, key: str, rule_name: str) -> None:
        super().__init__(f"Key '{key}' does not exist in the object of rule '{rule_name}'")


class InvalidRuleError(PySpecificationError, TypeError):
    """Exception raised when a function cannot be turned into a rule.

    A rule function must accept the object under test as its first positional
    parameter and, for subscriptable rules, the key as its second one.
    """


class InvalidParserError(PySpecificationError, TypeError):
    """Exception raised when a `Parse(...)` marker cannot work.

    For example a parser that is not callable, a marker on the object under test
    or on the key, or a marker used as a default value instead of inside `Annotated`.
    """


class ArgumentError(PySpecificationError, TypeError):
    """Base class for errors caused by the arguments given to a rule."""


class MissingArgumentError(ArgumentError):
    """Exception raised when a required argument is missing."""


class UnexpectedKeywordArgumentError(ArgumentError):
    """Exception raised when an unexpected keyword argument is passed."""


class TooManyArgumentsError(ArgumentError):
    """Exception raised when too many arguments are passed."""


class MultipleValuesArgumentError(ArgumentError):
    """Exception raised when an argument is given both positionally and by keyword."""


class PositionalOnlyArgumentError(ArgumentError):
    """Exception raised when positional-only argument is passed as keyword argument."""


class ParseArgumentError(ArgumentError):
    """Exception raised when a `Parse` function fails on the value given for an argument."""


_ARGUMENT_ERROR_PATTERNS: tuple[tuple[str, type[ArgumentError]], ...] = (
    (r"positional.only.*passed as (a )?keyword", PositionalOnlyArgumentError),
    (r"missing a required", MissingArgumentError),
    (r"too many positional arguments", TooManyArgumentsError),
    (r"got an unexpected keyword argument", UnexpectedKeywordArgumentError),
    (r"multiple values for argument", MultipleValuesArgumentError),
)


def to_argument_error(error: TypeError, rule_name: str) -> ArgumentError:
    """Translate a `Signature.bind` `TypeError` into the matching `ArgumentError`.

    Example:
    ```python
    >>> error = to_argument_error(TypeError("too many positional arguments"), "age__gt")
    >>> type(error).__name__
    'TooManyArgumentsError'
    >>> str(error)
    "too many positional arguments for rule 'age__gt'"

    ```

    """
    message = str(error)
    error_type = next(
        (error for pattern, error in _ARGUMENT_ERROR_PATTERNS if re.search(pattern, message)),
        ArgumentError,
    )
    return error_type(f"{message} for rule '{rule_name}'")
