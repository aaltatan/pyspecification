from collections.abc import Callable
from typing import Any

from .predicate import Predicate
from .schemas import ConditionExpressionSchema, Expression, PredicateSchema, SimplePredicateSchema


class ExpressionDoesNotMatchError(Exception):
    def __init__(self, expression: str) -> None:
        super().__init__(f"Expression '{expression}' does not match")


class PredicateCompiler:
    def __init__(
        self,
        rules: dict[str, Callable[..., Predicate[Any, Any]]],
        initial_predicate_factory: Callable[[ConditionExpressionSchema], Predicate[Any, Any]],
    ) -> None:
        self._rules = rules
        self._initial_predicate_factory = initial_predicate_factory

    def compile(self, expression: Expression) -> Predicate[Any, Any]:
        if isinstance(expression, ConditionExpressionSchema):
            return self._compile_condition(expression)

        return self._compile_single(expression)

    def _compile_single(
        self, schema: SimplePredicateSchema | PredicateSchema
    ) -> Predicate[Any, Any]:
        predicate = self._rules[schema.name](*schema.args, **schema.kwargs)

        if schema.inverse:
            predicate = ~predicate

        return predicate

    def _compile_condition(self, schema: ConditionExpressionSchema) -> Predicate[Any, Any]:
        predicate = self._initial_predicate_factory(schema)

        if schema.inverse:
            predicate = ~predicate

        for condition in schema.expressions:
            compiled_predicate = self.compile(condition)

            if schema.operator == "and":
                predicate &= compiled_predicate
            else:
                predicate |= compiled_predicate

        return predicate
