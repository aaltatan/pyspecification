from typing import Any

from .schemas import ConditionExpressionSchema, Expression, PredicateSchema, SimplePredicateSchema


def read_expression(rule_dict: dict[str, Any]) -> Expression:
    if "expressions" in rule_dict:
        return ConditionExpressionSchema(**rule_dict)

    if "name" in rule_dict:
        return PredicateSchema(**rule_dict)

    return SimplePredicateSchema(root=rule_dict)
