import json
from collections.abc import Callable
from pprint import pformat
from typing import Any, Literal, TypedDict, TypeGuard

from pydantic import TypeAdapter

from .exceptions import MissingArgumentError, RuleDoesNotExistError, is_missing_argument_exception
from .predicate import Predicate, ReturnType

type ExpressionDict = ExpressionWrapperDict | PredicateDict


PREDICATE_DICT_KEYS = {"name", "args", "kwargs", "inverse"}
EXPRESSION_WRAPPER_DICT_KEYS = {"operator", "expressions", "inverse"}


class PredicateDict(TypedDict):
    """A dictionary representation of a predicate."""

    name: str
    args: list[Any]
    kwargs: dict[str, Any]
    inverse: bool


class ExpressionWrapperDict(TypedDict):
    """A dictionary representation of an expression."""

    operator: Literal["all", "any"]
    expressions: list["ExpressionWrapperDict | PredicateDict"]
    inverse: bool


def is_predicate_dict(d: Any) -> TypeGuard[PredicateDict]:
    return (
        isinstance(d, dict)
        and all(key in d for key in PREDICATE_DICT_KEYS)
        and len(d) == len(PREDICATE_DICT_KEYS)
    )


def is_expression_wrapper_dict(
    d: Any,
) -> TypeGuard[ExpressionWrapperDict]:
    return (
        isinstance(d, dict)
        and all(key in d for key in EXPRESSION_WRAPPER_DICT_KEYS)
        and len(d) == len(EXPRESSION_WRAPPER_DICT_KEYS)
    )


class PredicateCompiler[T, R: ReturnType]:
    """A compiler for predicates.

    Args:
        rules (dict[str, Callable[..., Predicate[T, R]]]): The rules to use for compiling.
        initial_predicate_factory (Callable[[ExpressionWrapperDict], Predicate[T, R]]): The factory to use for creating initial predicates.

    Example:
    ```python
    from pyspecification import Predicate, PredicateCompiler, object_rule


    @object_rule()
    def is_admin(user: User) -> bool:
        return user.is_admin


    @object_rule()
    def name__istartswith(user: User, value: str) -> bool:
        return user.name.lower().startswith(value.lower())


    @object_rule()
    def age__between(user: User, min_age: int, max_age: int) -> bool:
        return user.age >= min_age and user.age <= max_age


    def main() -> None:
        compiler = PredicateCompiler[User, bool](
            {
                "is_admin": is_admin,
                "name__istartswith": name__istartswith,
                "age__between": age__between,
            },
            lambda schema: Predicate(lambda _: schema["operator"] == "all", operator="logical"),
        )

        rule_data = {
            "operator": "any",
            "inverse": False,
            "expressions": [
                {
                    "name": "is_admin",
                    "inverse": False,
                    "args": [],
                    "kwargs": {},
                },
                {
                    "operator": "all",
                    "inverse": False,
                    "expressions": [
                        {
                            "name": "name__istartswith",
                            "inverse": False,
                            "args": ["admin"],
                            "kwargs": {},
                        },
                        {
                            "name": "age__between",
                            "inverse": False,
                            "args": [18, 30],
                            "kwargs": {},
                        },
                    ],
                },
            ],
        }

        rule = compiler.compile(rule_data)

        assert all(rule(user) for user in users)


    if __name__ == "__main__":
        main()
    ```

    """  # noqa: E501

    def __init__(
        self,
        rules: dict[str, Callable[..., Predicate[T, R]]],
        initial_predicate_factory: Callable[[ExpressionWrapperDict], Predicate[T, R]],
    ) -> None:
        self._rules = rules
        self._initial_predicate_factory = initial_predicate_factory

    def compile(self, expression: ExpressionDict) -> Predicate[T, R]:
        """Compiles an expression into a predicate."""
        return self._compile(expression, path="$")

    def _compile(self, expression: ExpressionDict, path: str) -> Predicate[T, R]:
        if is_expression_wrapper_dict(expression):
            return self._compile_wrapper(expression, path)

        if is_predicate_dict(expression):
            return self._compile_single(expression)

        raise TypeError(_invalid_expression_message(expression, path))

    def _compile_single(self, single: PredicateDict) -> Predicate[T, R]:
        if single["name"] not in self._rules:
            raise RuleDoesNotExistError(single["name"], self._rules.keys())

        try:
            predicate = self._rules[single["name"]](*single["args"], **single["kwargs"])
        except TypeError as e:
            if is_missing_argument_exception(e):
                raise MissingArgumentError(str(e)) from e
            raise

        if single["inverse"]:
            predicate = ~predicate

        return predicate

    def _compile_wrapper(self, wrapper: ExpressionWrapperDict, path: str) -> Predicate[T, R]:
        predicate = self._initial_predicate_factory(wrapper)

        for index, expression in enumerate(wrapper["expressions"]):
            compiled_predicate = self._compile(expression, f"{path}.expressions[{index}]")

            if wrapper["operator"] == "all":
                predicate &= compiled_predicate
            else:
                predicate |= compiled_predicate

        if wrapper["inverse"]:
            predicate = ~predicate

        return predicate


def _invalid_expression_message(expression: Any, path: str) -> str:
    return "\n".join(
        [
            f"Invalid expression at {path}.",
            "Expected an expression matching one of these schemas:",
            "",
            "Predicate:",
            json.dumps(TypeAdapter(PredicateDict).json_schema(), indent=2),
            "",
            "Expression wrapper:",
            json.dumps(TypeAdapter(ExpressionWrapperDict).json_schema(), indent=2),
            "",
            "Received:",
            pformat(expression, sort_dicts=False, width=88),
        ],
    )
