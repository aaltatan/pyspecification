# Exceptions

```text
Exception
├── PySpecificationError
│   ├── RuleDoesNotExistError
│   ├── RuleAlreadyRegisteredError
│   ├── RuleKeyDoesNotExistError
│   ├── InvalidRuleError                      (also a TypeError)
│   └── ArgumentError                         (also a TypeError)
│       ├── MissingArgumentError
│       ├── TooManyArgumentsError
│       ├── UnexpectedKeywordArgumentError
│       ├── MultipleValuesArgumentError
│       └── PositionalOnlyArgumentError
└── PyargprocessorsError                      (from pyargprocessors)
    ├── ProcessArgumentError                  (also a TypeError)
    └── InvalidProcessorError                 (also a TypeError)
```

`ProcessArgumentError` and `InvalidProcessorError` come from pyargprocessors and are
re-exported by pyspecification. To catch everything a user-written rule can cause, catch
both bases:

```python
from pyargprocessors import PyargprocessorsError

from pyspecification import (
    ArgumentError,
    InvalidRuleError,
    ProcessArgumentError,
    PySpecificationError,
    RuleDoesNotExistError,
)

assert issubclass(RuleDoesNotExistError, PySpecificationError)
assert issubclass(ArgumentError, PySpecificationError) and issubclass(ArgumentError, TypeError)
assert issubclass(InvalidRuleError, TypeError)
assert issubclass(ProcessArgumentError, PyargprocessorsError)
assert not issubclass(ProcessArgumentError, PySpecificationError)
```

## When each one is raised

| Exception | Raised | Example message |
| --- | --- | --- |
| `RuleDoesNotExistError` | `registry[name]` or `compile` with an unknown (or hidden) name | `Rule 'agee__ge' does not exist. Available rules: age__ge, is_admin` |
| `RuleAlreadyRegisteredError` | registering a taken name | `Rule 'age__ge' is already registered` |
| `RuleKeyDoesNotExistError` | evaluating a subscriptable predicate on a forbidden key, or a missing one with `check_key_existence` | `Key 'colour' does not exist in the object of rule 'eq'` |
| `InvalidRuleError` | decorating a function that does not take the object (and key) positionally | `Rule 'x' must accept the object under test as its leading positional parameters` |
| `MissingArgumentError` | building a rule without a required argument | `missing a required argument: 'minimum' for rule 'age__ge'` |
| `TooManyArgumentsError` | too many positional arguments | `too many positional arguments for rule 'age__ge'` |
| `UnexpectedKeywordArgumentError` | an undeclared keyword | `got an unexpected keyword argument 'min' for rule 'age__ge'` |
| `MultipleValuesArgumentError` | the same argument positionally and by keyword | `multiple values for argument 'minimum' for rule 'age__ge'` |
| `PositionalOnlyArgumentError` | a positional-only parameter by keyword | `got some positional-only arguments passed as keyword arguments: value for rule 'price__lt'` |
| `ProcessArgumentError` | a `Process` function raised | `Argument 'value' with value 'x' failed to process, ...` |
| `InvalidProcessorError` | a misplaced or non-callable `Process` at decoration | |
| `ValueError` | invalid rule name, unnamed lambda, mixing operator modes, labels for unknown rules | |
| `TypeError` | `compile` got a dict that is neither a predicate nor a wrapper; `failures()` on a bitwise predicate | |

## JSON-path notes

Every `PySpecificationError` and `PyargprocessorsError` raised while compiling gets an
[exception note](https://docs.python.org/3/library/exceptions.html#BaseException.add_note)
with the path of the expression that caused it, e.g. `at $.expressions[2].expressions[0]`.
Read it from `error.__notes__`. The error type itself is unchanged, so `except` clauses
work the same with or without the compiler.

## Programming errors vs user errors

When rules come from users (JSON, forms), the errors above are **their** mistakes: catch
them and show the message. Two situations are **your** mistakes and should crash loudly
in development instead:

- `InvalidRuleError` and `InvalidProcessorError`, raised when your module is imported;
- a `TypeError`, `KeyError` or anything else raised from **inside** a rule function while it
  runs. pyspecification never reclassifies those.
