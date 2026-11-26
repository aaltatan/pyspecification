# Compiling rules from JSON

Rules written in code are great for developers. When the rule itself is **data** (a
customer segment built in an admin screen, a discount policy stored in a database, a
filter sent by a front end) you describe it as JSON and compile it.

```py
PredicateCompiler(rules, initial_predicate_factory)
compiler.compile(expression) -> Predicate
```

- `rules`: a mapping of names to rule factories, usually `registry.rules`.
- `initial_predicate_factory`: builds the starting predicate of each `all`/`any` group
  (see [below](#the-initial-predicate)).

## The JSON shape

An expression is either a **predicate** or a **wrapper**.

A predicate calls one rule:

```json
{"name": "age__between", "args": [18], "kwargs": {"maximum": 30}, "inverse": false}
```

| Key | Meaning |
| --- | --- |
| `name` | a rule name present in `rules` |
| `args` | positional arguments, a list |
| `kwargs` | keyword arguments, an object |
| `inverse` | `true` to negate the rule, like `~` |

A wrapper combines expressions, and wrappers nest:

```json
{
  "operator": "any",
  "expressions": [
    {"name": "is_admin", "args": [], "kwargs": {}, "inverse": false},
    {
      "operator": "all",
      "expressions": [
        {"name": "name__istartswith", "args": ["admin"], "kwargs": {}, "inverse": false},
        {"name": "age__between", "args": [18, 30], "kwargs": {}, "inverse": false}
      ]
    }
  ]
}
```

`"all"` joins with `&`, `"any"` with `|`. The example reads
`is_admin() | (name__istartswith("admin") & age__between(18, 30))`.

All four predicate keys, and both wrapper keys, are **required**, and no other keys are
allowed. The `TypedDict`s `PredicateDict` and `ExpressionWrapperDict` describe them for
type checkers.

## Example: marketing segments saved in a database

A marketing team builds customer segments in a back office. Each segment is saved as
JSON in a table and compiled when a campaign is sent.

```python
import json
import sqlite3
from dataclasses import dataclass

from pyspecification import ObjectRulesRegistry, Predicate, PredicateCompiler


@dataclass
class Customer:
    email: str
    city: str
    orders: int
    newsletter: bool
    last_order_days_ago: int


segments = ObjectRulesRegistry[Customer, bool](operator="logical")


@segments.rule()
def city__in(customer: Customer, cities: list[str]) -> bool:
    return customer.city in cities


@segments.rule()
def orders__ge(customer: Customer, count: int) -> bool:
    return customer.orders >= count


@segments.rule()
def inactive_days__ge(customer: Customer, days: int) -> bool:
    return customer.last_order_days_ago >= days


@segments.rule()
def subscribed(customer: Customer) -> bool:
    return customer.newsletter


def initial(wrapper: dict) -> Predicate[Customer, bool]:
    return Predicate(lambda _: wrapper["operator"] == "all", operator="logical")


compiler = PredicateCompiler(segments.rules, initial)

database = sqlite3.connect(":memory:")
database.execute("CREATE TABLE segment (name TEXT PRIMARY KEY, definition TEXT)")
database.execute(
    "INSERT INTO segment VALUES (?, ?)",
    (
        "win_back_damascus",
        json.dumps(
            {
                "operator": "all",
                "expressions": [
                    {"name": "subscribed", "args": [], "kwargs": {}, "inverse": False},
                    {"name": "city__in", "args": [["Damascus", "Rif Dimashq"]], "kwargs": {}, "inverse": False},
                    {
                        "operator": "any",
                        "expressions": [
                            {"name": "inactive_days__ge", "args": [90], "kwargs": {}, "inverse": False},
                            {"name": "orders__ge", "args": [], "kwargs": {"count": 20}, "inverse": False},
                        ],
                    },
                ],
            }
        ),
    ),
)

(definition,) = database.execute(
    "SELECT definition FROM segment WHERE name = ?", ("win_back_damascus",)
).fetchone()

in_segment = compiler.compile(json.loads(definition))

customers = [
    Customer("a@x.sy", "Damascus", orders=3, newsletter=True, last_order_days_ago=120),
    Customer("b@x.sy", "Damascus", orders=25, newsletter=True, last_order_days_ago=5),
    Customer("c@x.sy", "Aleppo", orders=40, newsletter=True, last_order_days_ago=200),
    Customer("d@x.sy", "Rif Dimashq", orders=1, newsletter=False, last_order_days_ago=300),
    Customer("e@x.sy", "Damascus", orders=2, newsletter=True, last_order_days_ago=10),
]

assert [c.email for c in customers if in_segment(c)] == ["a@x.sy", "b@x.sy"]
```

The compiled predicate is an ordinary predicate: combine it with code-defined rules,
call `failures()` on it, reuse it across many objects.

## The initial predicate

Every wrapper starts from a predicate made by `initial_predicate_factory(wrapper)` and
then folds its expressions in with `&` (for `all`) or `|` (for `any`). The factory
receives the wrapper dictionary, so it can return the **neutral element** of the
operator:

- for `"all"`, a predicate that is always true (`True & x == x`),
- for `"any"`, a predicate that is always false (`False | x == x`).

That is what the `initial` function above does. It also decides what an **empty** group
means: with it, `{"operator": "all", "expressions": []}` matches everything and an empty
`any` matches nothing.

```python
match_all = compiler.compile({"operator": "all", "expressions": []})
match_none = compiler.compile({"operator": "any", "expressions": []})

assert match_all(customers[0]) and not match_none(customers[0])
```

Use a lambda, not a named function, for the inner predicate: unnamed predicates are left
out of [`failures()`](failures.md), so the neutral element never shows up as a reason.

For bitwise rules the neutral elements are expressions too, e.g.
`and_(true())`/`or_(false())` in SQLAlchemy or `Q()` in Django. See the
[integrations](../integrations/index.md).

## Errors point at the bad expression

Everything is checked while compiling, before any object is evaluated: unknown rule
names, bad arguments, failing [processors](arguments.md). Each error raised by
pyspecification or pyargprocessors gets a **note with the JSON path** of the expression
that caused it:

```python
from pyspecification import MissingArgumentError, RuleDoesNotExistError

broken = {
    "operator": "all",
    "expressions": [
        {"name": "subscribed", "args": [], "kwargs": {}, "inverse": False},
        {"name": "orders__gte", "args": [5], "kwargs": {}, "inverse": False},
    ],
}

try:
    compiler.compile(broken)
except RuleDoesNotExistError as error:
    assert str(error) == (
        "Rule 'orders__gte' does not exist. "
        "Available rules: city__in, orders__ge, inactive_days__ge, subscribed"
    )
    assert error.__notes__ == ["at $.expressions[1]"]

try:
    compiler.compile({"name": "city__in", "args": [], "kwargs": {}, "inverse": False})
except MissingArgumentError as error:
    assert error.__notes__ == ["at $"]
```

Python prints notes under the traceback, so the path appears in logs for free. To send it
to a front end, read `error.__notes__`.

A dictionary that is neither a predicate nor a wrapper (missing or extra keys) raises
`TypeError` with the path, both expected shapes as JSON Schema, and what was received:

```python
try:
    compiler.compile({"name": "subscribed"})
except TypeError as error:
    assert str(error).startswith("Invalid expression at $.")
    assert "Received:" in str(error)
```

!!! tip "Validate before you store"
    Validate incoming JSON against the [expression schema](json-schema.md#a-whole-expression)
    with a JSON Schema validator, then **compile it once before saving**. The schema
    catches shape and type errors; compiling also runs your processors.

## Security

The compiler can only call rules that are in the mapping you give it. Rules registered
with `hidden=True` are not in `registry.rules`, so user-supplied JSON cannot reach them.
The JSON never contains code: only names you chose and argument values.
