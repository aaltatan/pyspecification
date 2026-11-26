# Object rules

`@object_rule()` turns a function whose **first parameter is the object under test** into
a rule factory. Every other parameter becomes an argument of the factory.

```py
@object_rule(*, operator="logical", predicate_name=None, message=None)
```

| Option | Default | What it does |
| --- | --- | --- |
| `operator` | `"logical"` | the [operator mode](predicates.md#logical-or-bitwise) of the predicates it makes |
| `predicate_name` | the function name | the name the predicates print with and report in [failures](failures.md) |
| `message` | the docstring | the user-facing [failure message](failures.md#messages) |

Use object rules for dataclasses, domain models, ORM classes: anything whose data you read
as attributes.

## Example: loan pre-approval

A lender pre-approves applicants who earn enough, are not over-indebted and ask for an
allowed purpose.

```python
from dataclasses import dataclass, field
from inspect import signature

from pyspecification import object_rule


@dataclass
class Applicant:
    name: str
    age: int
    monthly_income: float
    monthly_debt: float
    purpose: str
    flags: set[str] = field(default_factory=set)


@object_rule()
def age__between(applicant: Applicant, minimum: int, maximum: int = 65) -> bool:
    """Applicants must be within the allowed age range."""
    return minimum <= applicant.age <= maximum


@object_rule()
def income__ge(applicant: Applicant, *, monthly: float) -> bool:
    return applicant.monthly_income >= monthly


@object_rule()
def debt_ratio__le(applicant: Applicant, ratio: float) -> bool:
    return applicant.monthly_debt / applicant.monthly_income <= ratio


@object_rule()
def purpose__in(applicant: Applicant, *purposes: str) -> bool:
    return applicant.purpose in purposes


@object_rule()
def has_flag(applicant: Applicant, flag: str) -> bool:
    return flag in applicant.flags


pre_approved = (
    age__between(21)
    & income__ge(monthly=800)
    & debt_ratio__le(0.4)
    & purpose__in("car", "home", "education")
    & ~has_flag("fraud_watch")
)

applicants = [
    Applicant("Huda", 34, monthly_income=1_500, monthly_debt=300, purpose="home"),
    Applicant("Sami", 19, monthly_income=2_000, monthly_debt=0, purpose="car"),
    Applicant("Nour", 40, monthly_income=1_000, monthly_debt=600, purpose="car"),
    Applicant("Karim", 45, monthly_income=3_000, monthly_debt=0, purpose="travel"),
    Applicant("Maya", 29, monthly_income=2_500, monthly_debt=0, purpose="home", flags={"fraud_watch"}),
]

assert [a.name for a in applicants if pre_approved(a)] == ["Huda"]
```

Everything Python allows in a signature works: defaults (`maximum: int = 65`),
keyword-only parameters (`*, monthly`), `*args` (`*purposes`) and `**kwargs`.

## The factory signature

The factory has the rule function's signature **minus the object under test**, so IDEs,
`help()` and the [JSON Schema](json-schema.md) all see the real arguments:

```python
assert str(signature(age__between)) == "(minimum: int, maximum: int = 65)"
assert age__between.__name__ == "age__between"
assert age__between.__doc__ == "Applicants must be within the allowed age range."
```

## Arguments are checked when the rule is built

Calling the factory binds the arguments to the signature immediately. A mistake raises
an [`ArgumentError`](arguments.md#argument-errors) subclass right there, not when the
predicate later runs over your data:

```python
from pyspecification import MissingArgumentError, UnexpectedKeywordArgumentError

try:
    age__between()  # forgot the minimum
except MissingArgumentError as error:
    assert str(error) == "missing a required argument: 'minimum' for rule 'age__between'"

try:
    income__ge(monthy=800)  # typo
except UnexpectedKeywordArgumentError as error:
    assert "monthy" in str(error)
```

## Renaming the predicate

`predicate_name` changes how the predicate prints and reports failures, without renaming
your Python function. Useful when the function name is not what your users or logs should
see:

```python
@object_rule(predicate_name="minimum_income")
def _income_at_least(applicant: Applicant, amount: float) -> bool:
    return applicant.monthly_income >= amount


rule = _income_at_least(1_200)

assert str(rule) == "minimum_income"
assert [str(f) for f in rule.failures(applicants[2])] == ["minimum_income(1200)"]
```

## Rules that build queries

With `operator="bitwise"` the same idea builds query expressions. Here the "object under
test" is the model class, and the rule returns a SQLAlchemy condition:

```python
from sqlalchemy import ColumnElement
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Loan(Base):
    __tablename__ = "loans"

    id: Mapped[int] = mapped_column(primary_key=True)
    amount: Mapped[float]
    status: Mapped[str]


@object_rule(operator="bitwise")
def amount__gt(model: type[Loan], value: float) -> ColumnElement[bool]:
    return model.amount > value


@object_rule(operator="bitwise")
def status__eq(model: type[Loan], value: str) -> ColumnElement[bool]:
    return model.status == value


condition = (amount__gt(10_000) & ~status__eq("closed"))(Loan)

assert str(condition) == "loans.amount > :amount_1 AND loans.status != :status_1"
```

More in [SQLAlchemy](../integrations/sqlalchemy.md).

## Invalid rule functions

The object under test must be accepted **positionally**. A function that cannot take it
raises `InvalidRuleError` (a `TypeError`) as soon as it is decorated:

```python
from pyspecification import InvalidRuleError

try:

    @object_rule()
    def broken(*, applicant: Applicant) -> bool:
        return True

except InvalidRuleError as error:
    assert "must accept the object under test" in str(error)
```

## Without a registry

Decorated functions are ordinary module-level names you can import anywhere. When you have
many rules, want to look them up by name, or want to compile them from JSON, collect them
in a [registry](registries.md) instead.
