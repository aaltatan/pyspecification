from typing import Any

from .schemas import ConditionExpressionSchema, Expression, PredicateSchema, SimplePredicateSchema


def read_expression(rule_dict: dict[str, Any]) -> Expression:
    if hasattr(rule_dict, "expressions"):
        return ConditionExpressionSchema(**rule_dict)

    if hasattr(rule_dict, "name"):
        return PredicateSchema(**rule_dict)

    return SimplePredicateSchema(root=rule_dict)
