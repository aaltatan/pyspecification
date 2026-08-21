from collections.abc import Callable
from typing import Any, Literal, TypedDict

from .predicate import Predicate

type ExpressionDict = ExpressionWrapperDict | PredicateDict


class PredicateDict(TypedDict):
    name: str
    args: list[Any]
    kwargs: dict[str, Any]
    inverse: bool


class ExpressionWrapperDict(TypedDict):
    operator: Literal["and", "or"]
    expressions: list["ExpressionWrapperDict | PredicateDict"]
    inverse: bool


class PredicateCompiler:
    def __init__(
        self,
        rules: dict[str, Callable[..., Predicate[Any, Any]]],
        initial_predicate_factory: Callable[[ExpressionWrapperDict], Predicate[Any, Any]],
    ) -> None:
        self._rules = rules
        self._initial_predicate_factory = initial_predicate_factory

    def compile(self, expression: ExpressionDict) -> Predicate[Any, Any]:
        if "expressions" in expression:
            return self._compile_wrapper(expression)

        return self._compile_single(expression)

    def _compile_single(self, single: PredicateDict) -> Predicate[Any, Any]:
        predicate = self._rules[single["name"]](*single["args"], **single["kwargs"])

        if single["inverse"]:
            predicate = ~predicate

        return predicate

    def _compile_wrapper(self, wrapper: ExpressionWrapperDict) -> Predicate[Any, Any]:
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
