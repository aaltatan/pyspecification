# Arguments and processing

Rules often get their arguments from JSON, a query string or an HTML form, where
everything is a string, number, boolean, list, dict or null. Your rule functions want
dates, decimals, enums, clean text. The `Process` marker bridges the two.

## `Process`

Write `Annotated[Type, Process(fn)]` on a parameter and `fn` runs on the value **when the
rule is built**:

```python
from datetime import date
from decimal import Decimal
from typing import Annotated

from pyspecification import Process, SubscriptableRulesRegistry

orders = SubscriptableRulesRegistry[dict[str, object], str, bool](operator="logical")


@orders.rule()
def date__after(
    order: dict[str, object],
    key: str,
    value: Annotated[date, Process(date.fromisoformat)],
) -> bool:
    return order[key] > value


rule = orders["date__after"]("placed_on", "2026-01-31")  # a string, as JSON sends it

assert rule({"placed_on": date(2026, 2, 14)})
assert not rule({"placed_on": date(2025, 12, 1)})
```

`Process` comes from [pyargprocessors](https://github.com/aaltatan/pyargprocessors) and is
re-exported by pyspecification, so `from pyspecification import Process` is enough.

### Example: a shop's search filters from a query string

`?min_price=19.90&tags=Sale, Summer &brand= ACME ` arrives as strings. Name each
processed type once with a `type` alias and reuse it in every rule:

```python
from pyargprocessors import each


def split_commas(text: str) -> list[str]:
    return [part for part in text.split(",") if part.strip()]


type Money = Annotated[Decimal, Process(Decimal)]
type Text = Annotated[str, Process(str.strip), Process(str.casefold)]
type Tags = Annotated[list[str], Process(split_commas), Process(each(str.strip)), Process(each(str.casefold))]


@orders.rule()
def money__ge(order: dict[str, object], key: str, value: Money) -> bool:
    return Decimal(str(order[key])) >= value


@orders.rule()
def text__eq(order: dict[str, object], key: str, value: Text) -> bool:
    return str(order[key]).casefold() == value


@orders.rule()
def tags__any(order: dict[str, object], key: str, value: Tags) -> bool:
    return any(tag in order[key] for tag in value)


query = {"min_price": "19.90", "tags": "Sale, Summer ", "brand": " ACME "}

search = (
    orders["money__ge"]("price", query["min_price"])
    & orders["tags__any"]("tags", query["tags"])
    & orders["text__eq"]("brand", query["brand"])
)

products = [
    {"name": "Sun hat", "price": 24.0, "tags": ["summer", "hats"], "brand": "Acme"},
    {"name": "Scarf", "price": 30.0, "tags": ["winter"], "brand": "Acme"},
    {"name": "Flip-flops", "price": 9.0, "tags": ["summer"], "brand": "Acme"},
]

assert [p["name"] for p in products if search(p)] == ["Sun hat"]
```

Markers run **left to right**: `Text` strips, then lowercases. `each(fn)` applies `fn` to
every item of a list, and `optional(fn)` (also from pyargprocessors) skips `None`.

## The rules of processing

- A marker applies whether the value is passed **positionally or by keyword**. On
  `*args` it runs on each item, on `**kwargs` on each value.
- Processing happens **once, when the rule is built**. The predicate then runs over
  thousands of objects without converting again.
- **Defaults you did not pass are not processed**, so a default must already be the
  final type.
- The processed value is what your function receives and what
  [`Failure.args`](failures.md#the-failure-object) shows.
- The object under test, and the key of a subscriptable rule, cannot be processed: a
  marker on them raises `InvalidProcessorError`.

### Processors can change the type

A processor may take something else than the rule receives. Here the JSON sends the
path of a block list and the rule receives the loaded names:

```python
import tempfile
from pathlib import Path

from pyspecification import ObjectRulesRegistry


def load_names(path: str) -> frozenset[str]:
    return frozenset(Path(path).read_text("utf-8").split())


accounts = ObjectRulesRegistry[dict[str, str], bool](operator="logical")


@accounts.rule()
def email__in_file(
    account: dict[str, str],
    names: Annotated[frozenset[str], Process(load_names)],
) -> bool:
    return account["email"] in names


with tempfile.TemporaryDirectory() as folder:
    blocklist = Path(folder) / "blocked.txt"
    blocklist.write_text("spam@example.com\nbot@example.com\n", "utf-8")

    is_blocked = accounts["email__in_file"](str(blocklist))  # the file is read here, once

assert is_blocked({"email": "bot@example.com"})
assert not is_blocked({"email": "rana@example.com"})
```

The [JSON Schema](json-schema.md#processed-arguments) of `names` says `string`: it
describes what the JSON must send (the processor's parameter), not what the rule receives.

## When a processor fails

If `fn` raises, you get `ProcessArgumentError` naming the argument and the value, with
the original exception chained as `__cause__`:

```python
from pyspecification import ProcessArgumentError

try:
    orders["date__after"]("placed_on", "31/01/2026")
except ProcessArgumentError as error:
    assert error.argument == "value"
    assert error.value == "31/01/2026"
    assert isinstance(error.cause, ValueError)
    assert str(error).startswith("Argument 'value' with value '31/01/2026' failed to process")
```

It fails while the rule is built, so an admin saving a bad date in a rule editor gets
the error immediately.

## Misplaced markers

`InvalidProcessorError` (a `TypeError`) is raised as soon as the rule is **defined** when
a `Process` marker:

- is not callable,
- sits on the object under test or on the key,
- is written as a default value (`value=Process(int)`) instead of inside `Annotated`.

```python
from pyspecification import InvalidProcessorError, subscriptable_rule

try:

    @subscriptable_rule()
    def bad(row: dict[str, str], key: Annotated[str, Process(str.lower)], value: str) -> bool:
        return row[key] == value

except InvalidProcessorError:
    pass
```

## Argument errors

Arguments are bound to the rule's signature as soon as the rule is called, including by
[`PredicateCompiler.compile`](compiling.md). Each kind of mistake has its own exception,
all subclasses of `ArgumentError` (itself a `TypeError`):

| Mistake | Exception | Example |
| --- | --- | --- |
| a required argument is missing | `MissingArgumentError` | `age__between()` |
| too many positional arguments | `TooManyArgumentsError` | `age__between(18, 30, 99)` |
| a keyword the rule does not declare | `UnexpectedKeywordArgumentError` | `age__between(min=18)` |
| a value given both positionally and by keyword | `MultipleValuesArgumentError` | `age__between(18, minimum=18)` |
| a positional-only parameter passed by keyword | `PositionalOnlyArgumentError` | `price__lt(value=5)` for `def price__lt(p, value, /)` |

```python
from pyspecification import (
    ArgumentError,
    MissingArgumentError,
    MultipleValuesArgumentError,
    PositionalOnlyArgumentError,
    TooManyArgumentsError,
    UnexpectedKeywordArgumentError,
    object_rule,
)


@object_rule()
def age__between(person: dict[str, int], minimum: int, maximum: int = 120) -> bool:
    return minimum <= person["age"] <= maximum


@object_rule()
def price__lt(product: dict[str, float], value: float, /) -> bool:
    return product["price"] < value


mistakes = [
    (lambda: age__between(), MissingArgumentError),
    (lambda: age__between(18, 30, 99), TooManyArgumentsError),
    (lambda: age__between(min=18), UnexpectedKeywordArgumentError),
    (lambda: age__between(18, minimum=18), MultipleValuesArgumentError),
    (lambda: price__lt(value=5), PositionalOnlyArgumentError),
]

for build, expected in mistakes:
    try:
        build()
    except ArgumentError as error:
        assert type(error) is expected, (error, expected)
        assert "for rule '" in str(error)
```

When several things are wrong, they are reported in the order Python reports them for a
normal call: keywords that cannot be passed by name first, then surplus or repeated
arguments, then missing ones. So `age__between(min=18)` is an unexpected `min`, not a
missing `minimum`: the typo is what needs fixing.

!!! note "Your own `TypeError`s stay yours"
    Only binding problems are translated. A `TypeError` raised from inside your rule
    function while it runs is never reclassified as an `ArgumentError`.
