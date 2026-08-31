from collections.abc import Callable
from typing import Any, Literal, TypedDict, TypeGuard

from .exceptions import CompilationError
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

    operator: Literal["and", "or"]
    expressions: list["ExpressionWrapperDict | PredicateDict"]
    inverse: bool


def is_predicate_dict(d: ExpressionDict | dict[str, Any]) -> TypeGuard[PredicateDict]:
    return all(key in d for key in PREDICATE_DICT_KEYS) and len(d) == len(PREDICATE_DICT_KEYS)


def is_expression_wrapper_dict(
    d: ExpressionDict | dict[str, Any],
) -> TypeGuard[ExpressionWrapperDict]:
    return all(key in d for key in EXPRESSION_WRAPPER_DICT_KEYS) and len(d) == len(
        EXPRESSION_WRAPPER_DICT_KEYS
    )


class PredicateCompiler[T, R: ReturnType]:
    """A compiler for predicates.

    Args:
        rules (dict[str, Callable[..., Predicate[Any, Any]]]): The rules to use for compiling.
        initial_predicate_factory (Callable[[ExpressionWrapperDict], Predicate[Any, Any]]): The factory to use for creating initial predicates.

    Example:
    ```python
    from pyspecification import Predicate, PredicateCompiler, object_rule


    @object_rule
    def is_admin(user: User) -> bool:
        return user.is_admin


    @object_rule
    def name__istartswith(user: User, value: str) -> bool:
        return user.name.lower().startswith(value.lower())


    @object_rule
    def age__between(user: User, min_age: int, max_age: int) -> bool:
        return user.age >= min_age and user.age <= max_age


    def main() -> None:
        rules = {
            "is_admin": is_admin,
            "name__istartswith": name__istartswith,
            "age__between": age__between,
        }

        compiler = PredicateCompiler(
            rules,
            lambda schema: Predicate(lambda _: schema["operator"] == "and"),
        )

        rule_data = {
            "operator": "or",
            "inverse": False,
            "expressions": [
                {
                    "name": "is_admin",
                    "inverse": False,
                    "args": [],
                    "kwargs": {},
                },
                {
                    "operator": "and",
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

        predicate = compiler.compile(rule_data)

        assert all(predicate(user) for user in users)


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
        if is_expression_wrapper_dict(expression):
            return self._compile_wrapper(expression)

        if is_predicate_dict(expression):
            return self._compile_single(expression)

        msg = (
            f"Invalid expression type: {expression}\n"
            f"Expected one of\n"
            "{'expressions': list[ExpressionDict], 'inverse': bool, 'operator': Literal['and', 'or']}\n"  # noqa: E501
            "or \n{'name': str, 'inverse': bool, 'args': list, 'kwargs': dict}"
        )
        raise CompilationError(msg)

    def _compile_single(self, single: PredicateDict) -> Predicate[T, R]:
        if single["name"] not in self._rules:
            msg = (
                f"Rule '{single['name']}' is not found\n"
                f"Available rules: {', '.join(self._rules.keys())}"
            )
            raise CompilationError(msg)

        predicate = self._rules[single["name"]](*single["args"], **single["kwargs"])

        if single["inverse"]:
            predicate = ~predicate

        return predicate

    def _compile_wrapper(self, wrapper: ExpressionWrapperDict) -> Predicate[T, R]:
        predicate = self._initial_predicate_factory(wrapper)

        for expression in wrapper["expressions"]:
            compiled_predicate = self.compile(expression)

            if wrapper["operator"] == "and":
                predicate &= compiled_predicate
            else:
                predicate |= compiled_predicate

        if wrapper["inverse"]:
            predicate = ~predicate

        return predicate
