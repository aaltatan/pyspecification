# Subscriptable rules

`@subscriptable_rule()` is for data you read with `obj[key]`: dictionaries, JSON records,
CSV rows, lists. The rule function takes **the object, then the key**, then its own
arguments. One rule then works for every field:

```py
@subscriptable_rule(
    *,
    operator="logical",
    predicate_name=None,
    message=None,
    check_key_existence=False,
    forbidden_keys=(),
)
```

| Option | Default | What it does |
| --- | --- | --- |
| `operator`, `predicate_name`, `message` | | as for [object rules](object-rules.md) |
| `check_key_existence` | `False` | raise `RuleKeyDoesNotExistError` when the key is missing from a dict, or out of range for a list |
| `forbidden_keys` | `()` | keys this rule may never read; using one raises `RuleKeyDoesNotExistError` |

## Example: filtering a product catalogue from CSV

A shop imports its catalogue as CSV. Every value arrives as a string, so the rules
convert what they read.

```python
import csv
import io
from decimal import Decimal

from pyspecification import subscriptable_rule

CATALOGUE = """\
sku,name,category,price,stock
A-100,Desk lamp,lighting,24.50,12
A-101,Floor lamp,lighting,89.00,0
B-200,Office chair,furniture,149.99,4
B-201,Standing desk,furniture,420.00,2
C-300,LED strip,lighting,9.99,140
"""

products = list(csv.DictReader(io.StringIO(CATALOGUE)))


@subscriptable_rule()
def text__eq(row: dict[str, str], key: str, value: str) -> bool:
    return row[key].casefold() == value.casefold()


@subscriptable_rule()
def number__between(row: dict[str, str], key: str, low: float, high: float) -> bool:
    return low <= Decimal(row[key]) <= high


@subscriptable_rule()
def number__gt(row: dict[str, str], key: str, value: float) -> bool:
    return Decimal(row[key]) > value


affordable_lighting_in_stock = (
    text__eq("category", "Lighting")
    & number__between("price", 5, 50)
    & number__gt("stock", 0)
)

assert [p["sku"] for p in products if affordable_lighting_in_stock(p)] == ["A-100", "C-300"]
```

Note how `number__gt` serves both `stock` and, with another key, any other numeric column.
With object rules you would need one rule per attribute.

The key is the **first argument of the factory**, and it shows up in failures:

```python
floor_lamp = products[1]

assert [str(f) for f in affordable_lighting_in_stock.failures(floor_lamp)] == [
    "number__between('price', 5, 50)",
    "number__gt('stock', 0)",
]
```

## Lists and integer keys

Keys can be integers too, for rows read with `csv.reader` or JSON arrays. Negative
indices work as in Python:

```python
@subscriptable_rule()
def cell__eq(row: list[str], index: int, value: str) -> bool:
    return row[index] == value


rows = list(csv.reader(io.StringIO(CATALOGUE)))[1:]

assert [row[0] for row in rows if cell__eq(2, "furniture")(row)] == ["B-200", "B-201"]
assert [row[0] for row in rows if cell__eq(-1, "0")(row)] == ["A-101"]
```

## Missing keys

By default a missing key is your rule's business: `row[key]` raises a plain `KeyError`.
With `check_key_existence=True`, pyspecification checks first and raises
`RuleKeyDoesNotExistError`, which names the key and the rule. This happens when the
predicate **runs**, because only then is the object known.

```python
from pyspecification import RuleKeyDoesNotExistError


@subscriptable_rule(check_key_existence=True)
def strict__eq(row: dict[str, str], key: str, value: str) -> bool:
    return row[key] == value


try:
    strict__eq("colour", "red")(products[0])
except RuleKeyDoesNotExistError as error:
    assert str(error) == "Key 'colour' does not exist in the object of rule 'strict__eq'"
```

For lists, an index outside `-len(row) <= index < len(row)` counts as missing.

!!! tip
    Turn this on when rules come from users ([compiled from JSON](compiling.md)): a
    misspelt field then fails with a clear message instead of a bare `KeyError`.

## Forbidden keys

Some fields must never be filterable, even if they are in the data: purchase cost, salary,
password hashes. `forbidden_keys` blocks them for that rule:

```python
@subscriptable_rule(forbidden_keys=("cost", "supplier_id"))
def public__eq(row: dict[str, str], key: str, value: str) -> bool:
    return row[key] == value


row = {"sku": "A-100", "cost": "11.20"}

assert public__eq("sku", "A-100")(row)

try:
    public__eq("cost", "11.20")(row)
except RuleKeyDoesNotExistError as error:
    assert "Key 'cost'" in str(error)
```

The forbidden key is reported as "does not exist" on purpose: the error does not confirm
to a curious user that the field is there.

## The key is never processed

The key is a plain argument: a [`Process`](arguments.md) marker on it raises
`InvalidProcessorError` when the rule is defined. Process the value arguments instead.
