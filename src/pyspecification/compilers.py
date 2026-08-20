from collections.abc import Callable
from typing import Any

from .core import Predicate
from .schemas import (
    ExpressionSchema,
    ExpressionsWrapperSchema,
    PredicateSchema,
    SimplePredicateSchema,
)


class PredicateCompiler:
    def __init__(
        self,
        rules: dict[str, Callable[..., Predicate[Any, Any]]],
        initial_predicate_factory: Callable[[ExpressionsWrapperSchema], Predicate[Any, Any]],
    ) -> None:
        self._rules = rules
        self._initial_predicate_factory = initial_predicate_factory

    def compile(self, expression: ExpressionSchema) -> Predicate[Any, Any]:
        if expression.root.type == "wrapper":
            return self._compile_wrapper(expression.root)

        return self._compile_single(expression.root)

    def _compile_single(
        self, schema: PredicateSchema | SimplePredicateSchema
    ) -> Predicate[Any, Any]:
        predicate = self._rules[schema.name](*schema.args, **schema.kwargs)

        if schema.inverse:
            predicate = ~predicate

        return predicate

    def _compile_wrapper(self, schema: ExpressionsWrapperSchema) -> Predicate[Any, Any]:
        predicate = self._initial_predicate_factory(schema)

        for expression in schema.expressions:
            compiled_predicate = self.compile(ExpressionSchema(expression))

            if schema.operator == "and":
                predicate &= compiled_predicate
            else:
                predicate |= compiled_predicate

        if schema.inverse:
            predicate = ~predicate

        return predicate
