# pyspecification

**Business rules as small, typed, composable predicates.**

Write each condition once as a plain Python function, combine them with `&`, `|` and `~`,
store them as JSON, explain to users why a rule failed, and turn the very same rules into
SQLAlchemy or Django query filters.

```py
vip = total_spent__ge(1_000) & ~is_blocked() & (country__in(["SY", "LB"]) | orders__ge(10))
```

## A first taste

An online store wants to know which customers get free shipping.

```python
from dataclasses import dataclass

from pyspecification import ObjectRulesRegistry


@dataclass
class Customer:
    name: str
    country: str
    orders: int
    total_spent: float
    is_blocked: bool = False


rules = ObjectRulesRegistry[Customer, bool](operator="logical")


@rules.rule(message="Your account is blocked")
def is_blocked(customer: Customer) -> bool:
    return customer.is_blocked


@rules.rule(message="Free shipping starts at 500 spent")
def total_spent__ge(customer: Customer, amount: float) -> bool:
    return customer.total_spent >= amount


@rules.rule()
def country__in(customer: Customer, countries: list[str]) -> bool:
    """We only ship for free to these countries."""
    return customer.country in countries


free_shipping = total_spent__ge(500) & country__in(["SY", "LB"]) & ~is_blocked()

customers = [
    Customer("Rana", "SY", orders=12, total_spent=820.0),
    Customer("Omar", "LB", orders=2, total_spent=120.0),
    Customer("Lina", "SY", orders=30, total_spent=2_400.0, is_blocked=True),
]

assert [c.name for c in customers if free_shipping(c)] == ["Rana"]
```

Each decorated function became a **rule factory**: call it with its arguments and you get a
`Predicate`, a callable you can combine with other predicates.

### Tell the customer why

```python
omar = customers[1]

assert [str(f) for f in free_shipping.failures(omar)] == ["total_spent__ge(500)"]
assert [f.message for f in free_shipping.failures(omar)] == ["Free shipping starts at 500 spent"]
```

### Let an admin write the rule as JSON

```python
from pyspecification import Predicate, PredicateCompiler

compiler = PredicateCompiler(
    rules.rules,
    lambda wrapper: Predicate(lambda _: wrapper["operator"] == "all", operator="logical"),
)

saved_in_database = {
    "operator": "all",
    "expressions": [
        {"name": "total_spent__ge", "args": [500], "kwargs": {}, "inverse": False},
        {"name": "is_blocked", "args": [], "kwargs": {}, "inverse": True},
    ],
}

rule = compiler.compile(saved_in_database)

assert [c.name for c in customers if rule(c)] == ["Rana"]
```

### Describe the rules to a form builder or an LLM

```python
from pyspecification import get_expression_json_schema

schema = get_expression_json_schema(rules.rules)

assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
```

## Where it fits

- **Filtering**: lists of objects, rows from CSV or JSON, database queries.
- **Validation**: checkout, onboarding and import checks with user-facing messages.
- **Authorization**: readable access policies instead of nested `if` trees.
- **Rule engines**: rules stored in a database, edited in an admin screen, reloaded at runtime.
- **Segmentation and feature flags**: "customers in Syria who ordered more than 5 times".

## Where to next

<div class="grid cards" markdown>

- [**Installation**](install.md): one command.
- [**User guide**](guide/index.md): every feature, one page each.
- [**Recipes**](recipes.md): complete real-world programs.
- [**API reference**](reference/api.md): every public name.

</div>

## Inspiration

pyspecification was inspired by the work and ideas shared by
[ArjanCodes](https://www.youtube.com/@ArjanCodes) ([GitHub](https://github.com/arjancodes)),
especially the concepts demonstrated in his video
["The Most Overengineered Python Pattern I've Ever Built"](https://youtu.be/KqfMiuL3cx4?si=WAn01N2I0OO3KOgc).
The video builds business rules as composable predicates; this package takes that idea
further with registries, JSON compilation, failure explanations and JSON Schema. Thank
you, Arjan.
