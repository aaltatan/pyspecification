# CLAUDE.md

## Project Philosophy

This project follows these principles:

* **Functional-first design**
* **Strong static typing**
* **Simple abstractions**
* **Composable behavior**
* **Explicit over implicit**
* **Minimal classes**
* **Pure functions whenever possible**
* **High test coverage**
* **Readable code over clever code**

The codebase should favor small, composable functions and lightweight objects instead of deep inheritance hierarchies.

---

# Python Version

Target Python version:

```text
Python 3.13+
```

Use modern Python features:

* PEP 695 type aliases
* Generic classes and functions
* ParamSpec (`**P`)
* TypeVar constraints
* `Concatenate`
* `Self`
* `match`
* `slots=True`
* `kw_only=True`
* `frozen=True` where appropriate

Avoid compatibility code for old Python versions.

---

# Typing Rules

Typing is mandatory.

Always use:

```python
type ProcessFn = Callable[[Any], Any]
```

Prefer:

```python
from collections.abc import Callable, Sequence, Iterable
```

instead of:

```python
from typing import Callable
```

Use:

```python
type UserId = UUID
```

instead of:

```python
UserId = UUID
```

Prefer:

```python
dict[str, int]
list[str]
tuple[int, ...]
```

instead of:

```python
Dict
List
Tuple
```

Use generics whenever useful:

```python
class Registry[T]:
    ...
```

Prefer precise typing:

```python
Callable[[str], int]
```

instead of:

```python
Callable
```

Avoid:

```python
Any
```

unless absolutely necessary.

---

# Functional Programming Guidelines

Prefer pure functions:

```python
def normalize(value: str) -> str:
    return value.strip().lower()
```

Avoid hidden state:

```python
BAD:

cache = {}

def fn():
    ...
```

Prefer composition:

```python
processed = validate(normalize(value))
```

instead of:

```python
class Processor:
    def process(self):
        ...
```

Use classes only when:

* state exists
* identity matters
* lifecycle management is required

Registries are acceptable because they maintain state.

---

# Registry Pattern

Registries are preferred over large if/else chains.

Example:

```python
registry.register_rule(...)
registry["equal"](...)
```

Rules should:

* be small
* be pure
* have explicit inputs
* avoid side effects

Example:

```python
@registry.rule()
def greater_than(
    obj: User,
    value: Decimal,
) -> bool:
    return obj.salary > value
```

---

# Predicate Pattern

Predicates are core building blocks.

Predicates should:

* be immutable
* be composable
* support:

```python
&
|
~
```

Example:

```python
is_admin & is_active
is_paid | is_trial
~is_deleted
```

Avoid mutable predicates.

---

# Processor Pattern

Argument processors should remain simple.

Preferred:

```python
type Processors = tuple[
    ProcessFn,
    dict[str, ProcessFn],
]
```

Meaning:

```text
(default_processor, named_processors)
```

Example:

```python
processors=(
    Decimal,
    {
        "date": parse_date,
    },
)
```

Avoid introducing classes unless complexity increases significantly.

---

# Clean Code Rules

Functions:

* should do one thing
* should remain short
* should have descriptive names

Preferred:

```python
process_arguments()
register_rule()
validate_name()
```

Avoid:

```python
do_stuff()
handle()
manager()
helper()
utils()
misc()
```

Avoid comments that explain obvious code.

Prefer expressive names.

Bad:

```python
x
d
tmp
```

Good:

```python
rule_name
processed_args
named_processors
```

---

# Naming Rules

Use:

```text
snake_case
```

for:

* variables
* functions
* modules

Use:

```text
PascalCase
```

for:

* classes
* exceptions

Exceptions:

```python
RuleNotRegisteredError
RuleAlreadyRegisteredError
```

Boolean names:

```python
is_valid
has_items
can_execute
```

Avoid abbreviations.

---

# Imports

Import order:

```python
# standard library

# third-party

# local imports
```

Prefer explicit imports:

```python
from collections.abc import Callable
```

Avoid:

```python
from module import *
```

---

# Data Models

Prefer:

* dataclasses
* Pydantic
* frozen objects

Example:

```python
@dataclass(frozen=True, slots=True)
class Rule:
    name: str
```

Use Pydantic for:

* external input
* serialization
* validation

Avoid using Pydantic as a general-purpose domain model.

---

# Error Handling

Raise domain-specific exceptions:

```python
RuleNotRegisteredError
```

Avoid:

```python
raise Exception()
```

Error messages should be explicit:

```python
Rule 'equal' is not registered
```

---

# Testing

Testing framework:

```text
pytest
```

Use:

```python
def test_register_rule() -> None:
    ...
```

Prefer:

```python
@pytest.fixture
```

for setup.

Example:

```python
@pytest.fixture
def registry() -> ObjectPredicateRegistry:
    return ObjectPredicateRegistry()
```

---

# Test Structure

Arrange:

```python
# Arrange
```

Act:

```python
# Act
```

Assert:

```python
# Assert
```

Example:

```python
def test_register_rule() -> None:
    registry = ObjectPredicateRegistry()

    @registry.rule()
    def equal(obj: int, value: int) -> bool:
        return obj == value

    predicate = registry["equal"](10)

    assert predicate(10) is True
    assert predicate(20) is False
```

---

# Parametrized Tests

Prefer:

```python
@pytest.mark.parametrize
```

Example:

```python
@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (1, True),
        (2, False),
    ],
)
def test_rule(
    value: int,
    expected: bool,
) -> None:
    ...
```

---

# Coverage

Target:

```text
100% coverage for:
- registries
- predicates
- processors
- validators
```

Test:

* happy paths
* edge cases
* invalid inputs
* exceptions

---

# What Claude Should Do

When generating code:

* Prefer functions over classes.
* Prefer composition over inheritance.
* Preserve strong typing.
* Use modern Python syntax.
* Keep abstractions minimal.
* Avoid unnecessary patterns.
* Use registries instead of condition chains.
* Write pure functions when possible.
* Use pytest for all tests.
* Generate complete type annotations.
* Follow existing naming conventions.
* Keep code small and readable.
* Do not introduce frameworks without clear value.
* Do not create "manager", "service", or "helper" classes without necessity.
* Avoid over-engineering.
* Preserve functional programming style.

The primary goal is:

```text
Simple + Typed + Functional + Composable + Readable
```
