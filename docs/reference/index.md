# Reference

- [API](api.md): every public name of `pyspecification`, with its signature.
- [Exceptions](exceptions.md): the exception hierarchy and when each one is raised.
- [Upgrading](upgrading.md): breaking changes between major versions.

Everything listed here is importable from the package root:

```python
import pyspecification

assert sorted(pyspecification.__all__) == [
    "ArgumentError",
    "ExpressionWrapperDict",
    "Failure",
    "InvalidProcessorError",
    "InvalidRuleError",
    "MissingArgumentError",
    "MultipleValuesArgumentError",
    "ObjectRulesRegistry",
    "OperatorType",
    "PositionalOnlyArgumentError",
    "Predicate",
    "PredicateCompiler",
    "PredicateDict",
    "Process",
    "ProcessArgumentError",
    "PySpecificationError",
    "RuleAlreadyRegisteredError",
    "RuleDoesNotExistError",
    "RuleKeyDoesNotExistError",
    "SubscriptableRulesRegistry",
    "TooManyArgumentsError",
    "UnexpectedKeywordArgumentError",
    "get_expression_json_schema",
    "get_json_schema",
    "get_rule_json_schema",
    "object_rule",
    "subscriptable_rule",
]
```
