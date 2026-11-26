# Why a rule failed

A yes/no answer is rarely enough. A customer whose order was rejected wants to know why;
a support agent wants to see which check blocked an account. `failures(obj)` answers
that for a logical predicate:

```py
predicate.failures(obj) -> tuple[Failure, ...]
```

It returns the rules that made the predicate fail for `obj`, or an empty tuple when it
passes.

## Example: checkout validation

```python
from dataclasses import dataclass, field

from pyspecification import ObjectRulesRegistry


@dataclass
class Cart:
    items: int
    total: float
    country: str
    coupons: list[str] = field(default_factory=list)
    has_alcohol: bool = False
    buyer_age: int = 30


checkout = ObjectRulesRegistry[Cart, bool](operator="logical")


@checkout.rule(message="Your cart is empty")
def items__ge(cart: Cart, count: int) -> bool:
    return cart.items >= count


@checkout.rule(message="The minimum order is 10.00")
def total__ge(cart: Cart, amount: float) -> bool:
    return cart.total >= amount


@checkout.rule(description="We do not deliver to this country yet.")
def country__in(cart: Cart, countries: list[str]) -> bool:
    return cart.country in countries


@checkout.rule()
def has_alcohol(cart: Cart) -> bool:
    """Alcohol cannot be sold to this buyer."""
    return cart.has_alcohol


@checkout.rule()
def buyer_age__ge(cart: Cart, years: int) -> bool:
    return cart.buyer_age >= years


can_check_out = (
    checkout["items__ge"](1)
    & checkout["total__ge"](10)
    & checkout["country__in"](["SY", "LB", "JO"])
    & (~checkout["has_alcohol"]() | checkout["buyer_age__ge"](18))
)

cart = Cart(items=2, total=7.5, country="TR", has_alcohol=True, buyer_age=16)

problems = can_check_out.failures(cart)

assert [str(p) for p in problems] == [
    "total__ge(10)",
    "country__in(['SY', 'LB', 'JO'])",
    "NOT has_alcohol",
    "buyer_age__ge(18)",
]
assert [p.message for p in problems] == [
    "The minimum order is 10.00",
    "We do not deliver to this country yet.",
    "Alcohol cannot be sold to this buyer.",
    None,
]

assert can_check_out.failures(Cart(items=1, total=25, country="SY")) == ()
```

Show the messages to the user, log the `str()` form for yourself.

## How each operator reports

| Predicate | Reported when it fails |
| --- | --- |
| a rule | the rule itself |
| `a & b` | every failing side, left to right |
| `a \| b` | both sides' failures, but **only when neither side passes** |
| `~a` | `a`, marked `negated=True`, when `a` passed |
| unnamed predicate (plain lambda) | nothing: it has no name worth showing |

That is why the alcohol branch above reports two failures: neither "no alcohol" nor
"buyer is 18+" held. A 20-year-old with the same cart would not see either of them.

## The `Failure` object

```py
@dataclass(frozen=True, slots=True)
class Failure:
    rule: str                    # the rule name
    args: tuple = ()             # bound positional arguments
    kwargs: Mapping = {}         # bound keyword arguments
    negated: bool = False        # True when the rule passed but `~` required it not to
    message: str | None = None   # user-facing text
```

```python
first = problems[0]

assert (first.rule, first.args, first.kwargs, first.negated) == ("total__ge", (10,), {}, False)
assert problems[2].negated
```

`str(failure)` renders a call: `rule`, `rule(arg, key=value)`, prefixed by `NOT ` when
negated. The arguments are the values **after** [processing](arguments.md), so a date
sent as text appears as a `date`.

Failures are plain frozen dataclasses, easy to turn into an API response:

```python
response = {
    "ok": not problems,
    "errors": [{"rule": p.rule, "message": p.message or str(p)} for p in problems],
}

assert response["errors"][0] == {"rule": "total__ge", "message": "The minimum order is 10.00"}
```

## Messages

The message of a rule is the first of these that is set:

1. `message=` given to `rule()`, `register_rule()`, `object_rule()` or `subscriptable_rule()`,
2. `description=` given to `rule()` or `register_rule()`,
3. the rule function's docstring (cleaned with `inspect.cleandoc`),
4. otherwise `None`.

A `message` is for users ("The minimum order is 10.00"), a description or docstring is
for developers and [schemas](json-schema.md). Give both when they differ.

## Only for logical predicates

Bitwise predicates return expressions (SQL, `Q` objects) that cannot be evaluated in
Python, so `failures()` raises `TypeError` for them:

```python
from pyspecification import Predicate

sql_rule = Predicate(lambda model: model, operator="bitwise", name="sql_rule")

try:
    sql_rule.failures(object())
except TypeError as error:
    assert "needs a logical predicate" in str(error)
```

To explain a database filter, keep a logical twin of the same rules and ask it about the
row you loaded. See the [recipe](../recipes.md#same-rules-in-memory-and-in-the-database).
