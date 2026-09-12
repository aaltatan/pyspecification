# pyspecification

A lightweight, typed Python library for composing business rules as reusable, executable predicates.

This project was inspired by the work and ideas shared by [ArjanCodes](https://github.com/arjancodes), especially the concepts demonstrated in his video: ["The Most Overengineered Python Pattern I've Ever Built"](https://youtu.be/KqfMiuL3cx4?si=WAn01N2I0OO3KOgc).

`pyspecification` focuses on a functional style:

- rules are first-class callables
- predicates compose with `&`, `|`, and `~`
- registry-based registration keeps rules organized
- structured rule definitions can be compiled from dictionaries or JSON-like payloads
- structured rule definitions make rule metadata portable and machine-readable

It is especially useful for filtering, validation, authorization checks, and declarative rule engines without introducing a heavy framework.

---

## Why use pyspecification?

This package helps you turn complex condition logic into small, readable, testable rule fragments.

Instead of writing nested `if` logic like this:

```python
if user.is_admin or (user.name.lower().startswith("admin") and 18 <= user.age <= 30):
    allow_access = True
else:
    allow_access = False
```

you can define rules as composable predicates:

```python
rule = is_admin() | (name__istartswith("admin") & age__between(18, 30))
```

This keeps your logic:

- declarative
- reusable
- easy to combine
- friendly to validation and filtering pipelines
- easy to inspect and serialize

---

## Features

- Object-based predicate rules for dataclasses and domain models
- Subscriptable rules for dictionaries, lists, and generic lookup-based data
- `Predicate` objects that support logical composition
- Registry pattern for rule registration and lookup
- Custom argument processors for coercion and normalization
- `PredicateCompiler` for compiling structured rule dictionaries into executable predicates
- JSON schema generation for rule arguments and return types
- Support for both logical and bitwise operator modes
- Hidden rules and custom naming for internal/private rule registration

---

## Installation

```bash
pip install pyspecification
```

```bash
uv add pyspecification
```

---

## Core concepts

### 1. Predicate

A `Predicate[T, R]` wraps a function `fn: T -> R` and adds composition behavior.

```python
from pyspecification import Predicate


def is_adult(user: object) -> bool:
    return user.age >= 18


def is_admin_predicate(user: object) -> bool:
    return user.is_admin


adult_predicate: Predicate[User, bool] = Predicate(is_adult, operator="logical")
is_admin_predicate: Predicate[User, bool] = Predicate(is_admin_predicate, operator="logical")
```

You can combine predicates using:

```python
rule = adult_predicate & is_admin_predicate
rule = adult_predicate | is_admin_predicate
rule = ~adult_predicate
```

`operator` can be either:

- `"logical"` for `and` / `or` / `not`
- `"bitwise"` for `&` / `|` / `~`

When combining predicates, both sides must use the same operator mode.

---

### 2. Object rules

Use `@object_rule` to create reusable predicates from object-based functions.

```python
from dataclasses import dataclass

from pyspecification import object_rule


@dataclass
class User:
    name: str
    age: int
    is_admin: bool = False


@object_rule()
def name__istartswith(user: User, value: str) -> bool:
    return user.name.lower().startswith(value.lower())


@object_rule()
def age__between(user: User, min_age: int, max_age: int) -> bool:
    return user.age >= min_age and user.age <= max_age


@object_rule()
def is_admin(user: User) -> bool:
    return user.is_admin


rule = is_admin() | (name__istartswith("admin") & age__between(18, 30))
```

This yields a predicate that can be evaluated against a model instance:

```python
user = User(name="Abdullah", age=25, is_admin=True)
print(rule(user))  # True
```

The rule function itself is a factory that returns a `Predicate`.

---

### 3. Subscriptable rules

Use `@subscriptable_rule` for dictionary or list-like lookup data.

```python
from typing import Any

from pyspecification import subscriptable_rule


@subscriptable_rule()
def string__ieq(obj: dict[str, Any], key: str, value: str) -> bool:
    return obj[key].lower() == value.lower()


@subscriptable_rule()
def number__le(obj: dict[str, Any], key: str, value: int) -> bool:
    return obj[key] <= value


rule = string__ieq("gender", "male") & number__le("rank", 10)

person = {"gender": "Male", "rank": 9}
print(rule(person))  # True
```

This pattern is ideal for filtering dictionaries and JSON-like records.

---

### 4. Registry metadata

Registries expose `name` and `description` overrides on both `rule()` and
`register_rule()`. The name becomes the lookup key and the predicate name;
the description becomes the registered function's docstring.

```python
from pyspecification import ObjectRulesRegistry


rules = ObjectRulesRegistry[User, bool](operator="logical")


@rules.rule(
    name="adult_user",
    description="Whether the user is at least 18 years old.",
)
def is_adult(user: User) -> bool:
    return user.age >= 18


def is_admin(user: User) -> bool:
    return user.is_admin


rules.register_rule(
    is_admin,
    name="administrator",
    description="Whether the user has administrator access.",
)

rule = rules["adult_user"]()
print(rule(User(name="Abdullah", age=25, is_admin=True)))  # True
print(rule)  # adult_user
print(rules["administrator"].__doc__)  # The overridden description
```

When an override is omitted, the function name and docstring are retained.
The same options are available on `SubscriptableRulesRegistry`.

---

### 5. SQLAlchemy integration example

One of the strongest real-world use cases is turning rule definitions into SQLAlchemy filter expressions for database queries.

```python
from typing import Any

from pyspecification import ObjectRulesRegistry, Predicate, PredicateCompiler
from sqlalchemy import ColumnElement, and_, create_engine, or_
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    age: Mapped[int]
    is_admin: Mapped[bool] = mapped_column(default=False)


engine = create_engine("sqlite:///:memory:")
SessionLocal = sessionmaker(bind=engine)

# create database and seed data
Base.metadata.create_all(engine)
with SessionLocal() as session:
    session.add_all(
        [
            User(name="Abdullah", age=18, is_admin=True),
            User(name="Bob", age=16, is_admin=True),
            User(name="Charlie", age=20, is_admin=False),
            User(name="David", age=12, is_admin=False),
            User(name="Eve", age=8, is_admin=True),
        ]
    )
    session.commit()


rules = ObjectRulesRegistry[type[User], ColumnElement[bool]](operator="bitwise")


@rules.rule()
def is_admin(model: type[User]) -> ColumnElement[bool]:
    return model.is_admin == True  # noqa: E712


@rules.rule()
def name__iendswith(model: type[User], value: str) -> ColumnElement[bool]:
    return model.name.iendswith(value)


@rules.rule()
def age__ge(model: type[User], value: int) -> ColumnElement[bool]:
    return model.age >= value


@rules.rule()
def age__le(model: type[User], value: int) -> ColumnElement[bool]:
    return model.age <= value


compiler = PredicateCompiler(
    rules.rules,
    lambda schema: Predicate(
        lambda _: and_(True) if schema["operator"] == "all" else or_(False),
        operator="bitwise",
    ),
)

filter_rule_data = {
    "operator": "any",
    "expressions": [
        {
            "name": "is_admin",
            "args": [],
            "kwargs": {},
            "inverse": False,
        },
        {
            "name": "age__ge",
            "args": [18],
            "kwargs": {},
            "inverse": False,
        }
    ],
}

predicate = compiler.compile(filter_rule_data)
# is_admin() | age__ge(18)
# User.is_admin | User.age >= 18

with SessionLocal() as session:
    users = session.query(User).filter(predicate(User)).all()
    print([user.name for user in users])  # ['Abdullah', 'Bob', 'Charlie', 'Eve']
```

This pattern is especially useful when you want:

- declarative backend filters
- admin dashboards with rule-driven queries
- object-level permission evaluation
- SQLAlchemy-friendly business logic without hard-coded SQL fragments

> The project includes a full end-to-end SQLAlchemy example in the test suite under [tests/e2e/test_sqlalchemy_filtering_system.py](tests/e2e/test_sqlalchemy_filtering_system.py).

---

### 6. Django ORM integration example

This example demonstrates how to use `pyspecification` with Django models.
`pyspecification` does not import Django or provide a Django-specific adapter;
the rules return Django `Q` objects, while the existing bitwise predicate
composition supplies `&`, `|`, and `~` support.

```python
# models.py
from typing import Any, Self

from django.db import models
from pyspecification import Predicate


class EmployeeQuerySet(models.QuerySet):
    def filter_by_rule(self, rule: Predicate[Any, models.Q]) -> Self:
        return self.filter(rule(Employee))


class EmployeeManager(models.Manager):
    def get_queryset(self) -> EmployeeQuerySet:
        return EmployeeQuerySet(self.model, using=self._db)

    def filter_by_rule(self, rule: Predicate[Any, models.Q]) -> EmployeeQuerySet:
        return self.get_queryset().filter_by_rule(rule)


class Employee(models.Model):
    name = models.CharField(max_length=100)
    age = models.IntegerField()
    is_admin = models.BooleanField(default=False)

    objects = EmployeeManager()

    def __str__(self) -> str:
        return self.name
```

```python
# rules.py
from typing import Any

from pyspecification import ObjectRulesRegistry
from django.db.models import Q


registry = ObjectRulesRegistry[Any, Q](operator="bitwise")


@registry.rule()
def is_admin(_: Any) -> Q:
    return Q(is_admin=True)


@registry.rule()
def name__eq(_: Any, value: str) -> Q:
    return Q(name=value)


@registry.rule()
def age__gte(_: Any, value: int) -> Q:
    return Q(age__gte=value)


@registry.rule()
def age__lte(_: Any, value: int) -> Q:
    return Q(age__lte=value)
```

```python
# views.py
from typing import Any

from django.db.models import Q
from django.http import HttpRequest, HttpResponse
from pyspecification import Predicate, PredicateCompiler

from .rules import registry
from .models import Employee


FILTER_RULE = {
    "operator": "any",
    "expressions": [
        {
            "name": "is_admin",
            "args": [],
            "kwargs": {},
            "inverse": False,
        },
        {
            "operator": "all",
            "expressions": [
                {
                    "name": "name__eq",
                    "args": ["admin"],
                    "kwargs": {},
                    "inverse": False,
                },
                {
                    "name": "age__gte",
                    "args": [18],
                    "kwargs": {},
                    "inverse": False,
                },
            ]
        }
    ]
}

compiler = PredicateCompiler[Any, Q](
    registry.rules,
    lambda _: Predicate(lambda _: Q(), operator="bitwise"),
)

def filter_employees(request: HttpRequest) -> HttpResponse:
    predicate = compiler.compile(FILTER_RULE)
    employees = Employee.objects.filter_by_rule(predicate)
    return HttpResponse(f"Employees: {employees}")
```

The model, rule, and view snippets can live in their normal Django app
modules. No Django settings or model changes are required beyond the standard
Django project setup.

This pattern is especially useful when you want:

- declarative Django queryset filters
- reusable admin and dashboard filter rules
- object-level permissions backed by Django `Q` expressions

---

## Custom processors

Rules can apply argument processors to coerce values before evaluation.

```python
from datetime import datetime

from pyspecification import SubscriptableRulesRegistry


rules = SubscriptableRulesRegistry[dict[str, object], str, bool](operator="logical")


@rules.rule(processors=(lambda value: datetime.strptime(value, "%Y-%m-%d"), {}))
def datetime__gt(obj: dict[str, object], key: str, value: datetime) -> bool:
    return obj[key] > value


predicate = rules["datetime__gt"]("birthdate", "2001-06-01")
print(predicate({"birthdate": datetime(2005, 1, 1)}))  # True
```

The processor tuple format is:

```python
(default_processor, named_processors_map)
```

For example:

```python
processors = (
    int,
    {"value": str},
)
```

This means:

- positional args are passed through `int`
- keyword args with name `"value"` are passed through `str`

If conversion fails, the library raises `ProcessArgumentError`.

---

## Compiling structured rule definitions

`PredicateCompiler` turns declarative rule dictionaries into executable predicates.

```python
from dataclasses import dataclass

from pyspecification import Predicate, PredicateCompiler, object_rule


@dataclass
class User:
    name: str
    age: int
    is_admin: bool = False


@object_rule()
def is_admin(user: User) -> bool:
    return user.is_admin


@object_rule()
def name__istartswith(user: User, value: str) -> bool:
    return user.name.lower().startswith(value.lower())


@object_rule()
def age__between(user: User, min_age: int, max_age: int) -> bool:
    return user.age >= min_age and user.age <= max_age


rules = {
    "is_admin": is_admin,
    "name__istartswith": name__istartswith,
    "age__between": age__between,
}

compiler = PredicateCompiler(
    rules,
    lambda schema: Predicate(lambda _: schema["operator"] == "all", operator="logical"),
)

rule_data = {
    "operator": "any",
    "expressions": [
        {
            "name": "is_admin",
            "args": [],
            "kwargs": {},
            "inverse": False,
        },
        {
            "operator": "all",
            "expressions": [
                {
                    "name": "name__istartswith", 
                    "args": ["admin"], 
                    "kwargs": {}, 
                    "inverse": False,
                },
                {
                    "name": "age__between", 
                    "args": [18, 30], 
                    "kwargs": {}, 
                    "inverse": False,
                },
            ],
        },
    ],
}

predicate = compiler.compile(rule_data)
# is_admin() | (name__istartswith("admin") & age__between(18, 30))

print(predicate(User("admin", 25, True)))  # True
```

`PredicateCompiler.compile()` consumes a normalized dictionary. The `name`
must be present in the dictionary of rules passed to the compiler. Use `args`
for positional arguments, `kwargs` for keyword arguments, and `inverse` to
negate one predicate:

```python
import json

rule_json = '{"name": "age__between", "args": [18, 30], "kwargs": {}, "inverse": false}'
rule_data = json.loads(rule_json)
predicate = compiler.compile(rule_data)

print(repr(predicate))  # Predicate(age__between)
```

Use a wrapper to combine predicates. A wrapper has an `operator` and an
`expressions` list:

```json
{
    "operator": "all",
    "expressions": [
        {
            "name": "is_admin",
            "args": [],
            "kwargs": {},
            "inverse": false
        },
        {
            "name": "age__between",
            "args": [18, 30],
            "kwargs": {},
            "inverse": false
        }
    ]
} // is_admin() & age__between(18, 30)
```

`operator` must be either `"all"` or `"any"`. Expressions can be nested to
represent more complex logic:

```json
{
    "operator": "any",
    "expressions": [
        {
            "name": "is_admin",
            "args": [],
            "kwargs": {},
            "inverse": false
        },
        {
            "operator": "all",
            "expressions": [
                {
                    "name": "name__istartswith",
                    "args": ["admin"],
                    "kwargs": {},
                    "inverse": false
                },
                {
                    "name": "age__between",
                    "args": [],
                    "kwargs": {"min_age": 18, "max_age": 30},
                    "inverse": false
                }
            ]
        }
    ]
} // is_admin() | (name__istartswith("admin") & age__between(min_age=18, max_age=30))
```

The compiler raises `RuleDoesNotExistError` when a predicate name is not in the
compiler's rule mapping. If the dictionary passed directly to `compile()` does
not match a predicate or wrapper shape, it raises `TypeError`.

---
---

## JSON schema generation

`get_rule_json_schema` inspects a rule function and returns JSON-schema-like metadata for parameters and return value.

```python
from dataclasses import dataclass

from pyspecification import get_rule_json_schema, object_rule


@dataclass
class User:
    name: str
    age: int
    is_admin: bool = True


@object_rule()
def name__istartswith(user: User, value: str) -> bool:
    return user.name.lower().startswith(value.lower())


print(get_rule_json_schema(name__istartswith))
# {'value': {'type': 'string'}, 'return': {'type': 'boolean'}}
```

This is useful for:

- generating UIs for rule configuration
- building admin tools and dashboards
- describing rule inputs to other systems
- documenting business rules programmatically

---

## Use cases

### 1. Filtering datasets

This library is excellent for building dynamic dataset filters during API requests or internal analytics queries.

```python
from dataclasses import dataclass

from pyspecification import ObjectRulesRegistry


@dataclass
class User:
    name: str
    age: int
    is_admin: bool


registry = ObjectRulesRegistry[User, bool](operator="logical")


@registry.rule()
def is_admin(user: User) -> bool:
    return user.is_admin


@registry.rule()
def age__gte(user: User, value: int) -> bool:
    return user.age >= value


users = [
    User("Alice", 27, True),
    User("Bob", 19, False),
    User("Charlie", 31, True),
]

predicate = registry["is_admin"]() & registry["age__gte"](20)
filtered = [user for user in users if predicate(user)]
```

### 2. SQLAlchemy-backed filtering and query composition

This is one of the most useful real-world patterns for the package. You can define a reusable rule set and compile it into SQLAlchemy boolean expressions for database queries.

```python
from pyspecification import ObjectRulesRegistry, Predicate, PredicateCompiler
from sqlalchemy import ColumnElement, and_, or_
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    age: Mapped[int]
    is_admin: Mapped[bool]


rules = ObjectRulesRegistry[type[User], ColumnElement[bool]](operator="bitwise")


@rules.rule()
def is_admin(model: type[User]) -> ColumnElement[bool]:
    return model.is_admin == True  # noqa: E712


@rules.rule()
def age__ge(model: type[User], value: int) -> ColumnElement[bool]:
    return model.age >= value


compiler = PredicateCompiler(
    rules.rules,
    lambda schema: Predicate(
        lambda _: and_(True) if schema["operator"] == "all" else or_(False),
        operator="bitwise",
    ),
)

filter_rule = {
    "operator": "any",
    "expressions": [
        {
            "name": "is_admin",
            "args": [],
            "kwargs": {},
            "inverse": False,
        },
        {
            "name": "age__ge",
            "args": [18],
            "kwargs": {},
            "inverse": False,
        },
    ],
}

query_predicate = compiler.compile(filter_rule)
# is_admin() | age__ge(18)
# User.is_admin | User.age >= 18
```

This makes it easy to expose admin filters, user search rules, and role-based queries without manually stitching SQL conditions together.

### 3. Authorization and access rules

You can model business policies as rules and compose them into policy expressions.

```python
rule = is_admin() | (is_manager() & is_active())
```

This allows readable authorization checks without large condition trees.

### 3. Dynamic rule engines

The compiler makes it easy to store or receive rules as structured data.

Examples:

- frontend sends a filter model to backend
- admin system stores JSON rules in a database
- rules are reloaded at runtime based on configuration

### 4. Validation pipelines

Rules can be assembled from reusable predicate pieces and evaluated against model instances or dictionary records.

This is ideal for:

- data validation
- compliance checks
- workflow gating
- feature flags and user segmentation

---

## Recommended patterns

### Prefer named rule functions

```python
@object_rule()
def age__between(user: User, min_age: int, max_age: int) -> bool:
    return user.age >= min_age and user.age <= max_age
```

This gives you readable names and predictable rule lookup keys.

### Keep rules small and pure

Rules should do one thing and avoid hidden side effects.

### Use registries for larger systems

If your project has many rules, registries provide structure and reduce duplication.

---

## Exceptions

The library raises explicit exceptions for rule issues:

- `RuleDoesNotExistError`
- `RuleAlreadyRegisteredError`
- `RuleKeyDoesNotExistError`
- `ArgumentError`
- `MissingArgumentError`
- `UnexpectedKeywordArgumentError`
- `TooManyArgumentsError`
- `ProcessArgumentError`

`ArgumentError` is the base class for failures involving arguments passed to a
rule. Its specialized exceptions describe the problem:

- `MissingArgumentError` means a required positional or keyword-only argument
    was not provided.
- `UnexpectedKeywordArgumentError` means a keyword does not belong to the
    rule's signature.
- `TooManyArgumentsError` means more positional arguments were provided than
    the rule accepts.
- `ProcessArgumentError` means an argument processor could not convert or
    otherwise process a value.

`RuleDoesNotExistError` includes the missing name and the available rule names,
which is useful when rules are dynamically loaded. Malformed normalized
compiler payloads raise `TypeError`; its message identifies the JSON-like path
of the invalid expression and shows the expected shapes.

---

## Example scripts in this repository

This project includes runnable examples under the `scripts/` directory:

- `scripts/rules_example.py` — basic object-based rule composition
- `scripts/reg_example.py` — registry usage and compiled rule predicate patterns

The test suite under `tests/` also demonstrates behavior for:

- registry registration
- predicate composition
- compiler validation
- structured rule compilation
- filtering workflows

---

## Example complete workflow

```python
from dataclasses import dataclass

from pyspecification import ObjectRulesRegistry, Predicate, PredicateCompiler


@dataclass
class User:
    name: str
    age: int
    is_admin: bool = False


registry = ObjectRulesRegistry[User, bool](operator="logical")


@registry.rule()
def is_admin(user: User) -> bool:
    return user.is_admin


@registry.rule()
def name__istartswith(user: User, value: str) -> bool:
    return user.name.lower().startswith(value.lower())


@registry.rule()
def age__between(user: User, min_age: int, max_age: int) -> bool:
    return user.age >= min_age and user.age <= max_age


rule_definition = {
    "operator": "any",
    "expressions": [
        {
            "name": "is_admin",
            "args": [],
            "kwargs": {},
            "inverse": False,
        },
        {
            "operator": "all",
            "expressions": [
                {
                    "name": "name__istartswith",
                    "args": ["admin"],
                    "kwargs": {},
                    "inverse": False,
                },
                {
                    "name": "age__between",
                    "args": [18, 30],
                    "kwargs": {},
                    "inverse": False,
                },
            ]
        },
    ],
}

compiler = PredicateCompiler(registry.rules, lambda spec: Predicate(lambda _: True, operator="logical"))
predicate = compiler.compile(rule_definition)
# is_admin() | (name__istartswith("admin") & age__between(18, 30))

users = [
    User("Abdullah", 18, True),
    User("admin", 20, False),
    User("Charlie", 12, False),
]

print([predicate(user) for user in users])  # [True, True, False]
```

---

## Summary

`pyspecification` brings together rule registration, predicate composition, and runtime compilation in a compact library designed around functional and declarative rule authoring.

It is a practical fit for projects that need to:

- express business rules clearly
- compose conditions without nested `if` chains
- compile dynamic rule payloads
- support filtering and policy evaluation
- keep rule logic easy to test and maintain

If you want a rule system that feels Pythonic, composable, and lightweight, `pyspecification` is built for that workflow.

---

## License

This project is licensed under the GNU General Public License v3.0 or later.

See the full text in [LICENSE](LICENSE).

The project is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU GPL v3 for more details.
