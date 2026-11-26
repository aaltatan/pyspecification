# Predicates

A `Predicate[T, R]` wraps a function `T -> R` and gives it three operators:

| Operator | Meaning | `"logical"` mode | `"bitwise"` mode |
| --- | --- | --- | --- |
| `a & b` | both | `a(obj) and b(obj)` | `a(obj) & b(obj)` |
| `a \| b` | either | `a(obj) or b(obj)` | `a(obj) \| b(obj)` |
| `~a` | not | `not a(obj)` | `~a(obj)` |

Every operator returns a **new** predicate; the originals never change, so you can reuse
a predicate in as many combinations as you like.

Most of the time you will not create `Predicate` objects yourself: [rules](object-rules.md)
create them for you. Knowing how they behave helps anyway.

## Creating one directly

```py
Predicate(fn, /, *, operator, name=None)
```

- `fn`: the function to wrap, called with the object under test.
- `operator`: `"logical"` or `"bitwise"` (required, see below).
- `name`: how the predicate prints. Defaults to the function's name.

### Example: flag card transactions for manual review

A payments team reviews transactions that are large **and** either paid with a foreign
card or made in the middle of the night.

```python
from dataclasses import dataclass

from pyspecification import Predicate


@dataclass(frozen=True)
class Transaction:
    amount: float
    country: str
    card_country: str
    hour: int


def is_foreign_card(transaction: Transaction) -> bool:
    return transaction.country != transaction.card_country


is_large = Predicate(lambda t: t.amount >= 5_000, operator="logical", name="is_large")
is_night = Predicate(lambda t: t.hour < 6, operator="logical", name="is_night")
foreign = Predicate(is_foreign_card, operator="logical")

needs_review = is_large & (foreign | is_night)

transactions = [
    Transaction(amount=9_000, country="SY", card_country="DE", hour=14),  # large, foreign
    Transaction(amount=9_000, country="SY", card_country="SY", hour=3),   # large, at night
    Transaction(amount=9_000, country="SY", card_country="SY", hour=14),  # large only
    Transaction(amount=50, country="SY", card_country="DE", hour=3),      # small
]

assert [needs_review(t) for t in transactions] == [True, True, False, False]
```

## How predicates print

`str()` gives the name; `repr()` wraps it in `Predicate(...)`. Composed predicates show
their structure, which is handy in logs:

```python
assert str(foreign) == "is_foreign_card"  # taken from the function name
assert str(needs_review) == "(is_large AND (is_foreign_card OR is_night))"
assert repr(~is_night) == "Predicate(NOT is_night)"
```

A lambda without `name=` prints as `anonymous`:

```python
assert str(Predicate(lambda t: True, operator="logical")) == "anonymous"
```

!!! note
    The printed form shows rule names, not their arguments. To see the arguments of the
    rules that made an object fail, use [`failures()`](failures.md).

## Logical or bitwise?

The operator mode decides how `&`, `|` and `~` combine the **results**.

**`"logical"`** uses Python's `and`, `or` and `not`. Use it whenever a predicate returns a
plain `bool`: in-memory filtering, validation, authorization. It short-circuits, so in
`is_large & foreign` the second check does not run when the first is false.

**`"bitwise"`** uses `&`, `|` and `~` on the results themselves. Use it when a predicate
returns an **expression object** that overloads those operators, such as a SQLAlchemy
column expression or a Django `Q` object. The predicate then *builds a query* instead of
answering yes or no:

```python
from sqlalchemy import column

big = Predicate(lambda _: column("amount") >= 5_000, operator="bitwise", name="big")
night = Predicate(lambda _: column("hour") < 6, operator="bitwise", name="night")

where_clause = (big & ~night)(None)

assert str(where_clause) == "amount >= :amount_1 AND hour >= :hour_1"
assert str(big & ~night) == "(big & ~night)"
```

See [SQLAlchemy](../integrations/sqlalchemy.md) and [Django](../integrations/django.md) for
complete examples.

!!! warning "Do not use bitwise mode for plain booleans"
    In Python `~True == -2` and `~False == -1`, both truthy. A bitwise predicate that
    returns `bool` gives wrong answers as soon as you negate it. Pick `"logical"` for
    `bool` results.

### Modes cannot be mixed

Both sides of `&` and `|` must use the same mode, otherwise you get a `ValueError` at the
moment you combine them:

```python
try:
    is_large & big
except ValueError as error:
    assert str(error) == "Cannot combine predicates with different operators: logical != bitwise"
```

## Return types

`R` can be any type that supports `&`, `|` and `~` (`bool`, SQLAlchemy's
`ColumnElement[bool]`, Django's `Q`, or your own class). That is what the `ReturnType`
protocol in the type hints means; type checkers will tell you if a rule returns something
that cannot be combined.
