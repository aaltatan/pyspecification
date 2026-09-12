"""
A lightweight, typed Python library for composing business rules as reusable, executable predicates.

This project was inspired by the work and ideas shared by [ArjanCodes](https://github.com/arjancodes), especially the concepts demonstrated in his video: ["The Most Overengineered Python Pattern I've Ever Built"](https://youtu.be/KqfMiuL3cx4?si=WAn01N2I0OO3KOgc).
"""  # noqa: E501

from .compilers import ExpressionWrapperDict, PredicateCompiler, PredicateDict
from .exceptions import (
    ArgumentError,
    MissingArgumentError,
    PositionalOnlyArgumentError,
    ProcessArgumentError,
    RuleAlreadyRegisteredError,
    RuleDoesNotExistError,
    RuleKeyDoesNotExistError,
    TooManyArgumentsError,
    UnexpectedKeywordArgumentError,
)
from .json_schema import get_json_schema
from .predicate import OperatorType, Predicate
from .registry import ObjectRulesRegistry, SubscriptableRulesRegistry
from .rules import object_rule, subscriptable_rule
from .schemas import RuleSchema

__all__ = [
    "ArgumentError",
    "ExpressionWrapperDict",
    "MissingArgumentError",
    "ObjectRulesRegistry",
    "OperatorType",
    "PositionalOnlyArgumentError",
    "Predicate",
    "PredicateCompiler",
    "PredicateDict",
    "ProcessArgumentError",
    "RuleAlreadyRegisteredError",
    "RuleDoesNotExistError",
    "RuleKeyDoesNotExistError",
    "RuleSchema",
    "SubscriptableRulesRegistry",
    "TooManyArgumentsError",
    "UnexpectedKeywordArgumentError",
    "get_json_schema",
    "object_rule",
    "subscriptable_rule",
]
