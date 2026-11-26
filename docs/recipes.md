# Recipes

Complete, runnable programs for common jobs. Each one is self-contained.

## Access control for documents

A document system decides who may edit a document. The rule needs **two** things, the
user and the document, so the object under test is a small context object.

```python
from dataclasses import dataclass, field

from pyspecification import ObjectRulesRegistry


@dataclass(frozen=True)
class User:
    id: int
    department: str
    roles: frozenset[str] = field(default_factory=frozenset)


@dataclass(frozen=True)
class Document:
    owner_id: int
    department: str
    archived: bool = False
    classification: str = "internal"


@dataclass(frozen=True)
class Access:
    user: User
    document: Document


policy = ObjectRulesRegistry[Access, bool](operator="logical")


@policy.rule(message="Only the owner can do this")
def is_owner(access: Access) -> bool:
    return access.user.id == access.document.owner_id


@policy.rule(message="You need a role for this")
def has_role(access: Access, role: str) -> bool:
    return role in access.user.roles


@policy.rule(message="The document belongs to another department")
def same_department(access: Access) -> bool:
    return access.user.department == access.document.department


@policy.rule(message="Archived documents are read-only")
def is_archived(access: Access) -> bool:
    return access.document.archived


@policy.rule(message="Confidential documents need clearance")
def classification__eq(access: Access, level: str) -> bool:
    return access.document.classification == level


can_edit = (
    ~is_archived()
    & (is_owner() | (has_role("manager") & same_department()) | has_role("admin"))
    & (~classification__eq("confidential") | has_role("cleared"))
)

alice = User(1, "finance")
bob = User(2, "finance", frozenset({"manager"}))
carol = User(3, "sales", frozenset({"manager"}))

budget = Document(owner_id=1, department="finance")
payroll = Document(owner_id=1, department="finance", classification="confidential")

assert can_edit(Access(alice, budget))
assert can_edit(Access(bob, budget))
assert not can_edit(Access(carol, budget))
assert not can_edit(Access(bob, payroll))

why = [f.message for f in can_edit.failures(Access(bob, payroll))]

assert why == ["Confidential documents need clearance", "You need a role for this"]
```

The policy reads like the business sentence: *not archived, and (owner, or a manager in
the same department, or an admin), and (not confidential, or cleared)*.

## Validating an import file row by row

An HR team uploads a CSV of new employees. Every row is checked and the upload screen
shows all problems at once, by line number.

```python
import csv
import io
import re
from datetime import date

from pyspecification import SubscriptableRulesRegistry

checks = SubscriptableRulesRegistry[dict[str, str], str, bool](operator="logical", check_key_existence=True)


@checks.rule()
def required(row: dict[str, str], key: str) -> bool:
    return bool(row[key].strip())


@checks.rule()
def matches(row: dict[str, str], key: str, pattern: str) -> bool:
    return re.fullmatch(pattern, row[key]) is not None


@checks.rule()
def date__before(row: dict[str, str], key: str, limit: str) -> bool:
    try:
        return date.fromisoformat(row[key]) < date.fromisoformat(limit)
    except ValueError:
        return False


@checks.rule()
def one_of(row: dict[str, str], key: str, values: list[str]) -> bool:
    return row[key] in values


valid_employee = (
    checks["required"]("name")
    & checks["matches"]("email", r"[^@\s]+@company\.com")
    & checks["date__before"]("birth_date", "2008-11-26")
    & checks["one_of"]("contract", ["permanent", "fixed_term", "intern"])
)

MESSAGES = {
    "required": "{0} is required",
    "matches": "{0} has the wrong format",
    "date__before": "{0} must be a date before {1}",
    "one_of": "{0} must be one of {1}",
}

UPLOAD = """\
name,email,birth_date,contract
Ahmad Ali,ahmad@company.com,1990-04-12,permanent
,lina@gmail.com,1995-01-01,permanent
Sami Haddad,sami@company.com,2010-02-02,freelance
"""

report = {}

for line, row in enumerate(csv.DictReader(io.StringIO(UPLOAD)), start=2):
    if problems := valid_employee.failures(row):
        report[line] = [MESSAGES[p.rule].format(*p.args) for p in problems]

assert report == {
    3: ["name is required", "email has the wrong format"],
    4: ["birth_date must be a date before 2008-11-26", "contract must be one of ['permanent', 'fixed_term', 'intern']"],
}
```

`Failure.args` holds the key and the arguments, which is enough to build a precise
message per rule.

## A promotions engine

A shop runs several promotions at once. Marketing writes each condition as JSON; the
checkout picks the best promotion the basket qualifies for.

```python
import json
from dataclasses import dataclass
from decimal import Decimal
from typing import Annotated

from pyspecification import ObjectRulesRegistry, Predicate, PredicateCompiler, Process


@dataclass
class Basket:
    subtotal: Decimal
    categories: set[str]
    customer_orders: int
    coupon: str | None = None


promo_rules = ObjectRulesRegistry[Basket, bool](operator="logical")

type Money = Annotated[Decimal, Process(lambda value: Decimal(str(value)))]


@promo_rules.rule()
def subtotal__ge(basket: Basket, amount: Money) -> bool:
    return basket.subtotal >= amount


@promo_rules.rule()
def has_category(basket: Basket, category: str) -> bool:
    return category in basket.categories


@promo_rules.rule()
def first_order(basket: Basket) -> bool:
    return basket.customer_orders == 0


@promo_rules.rule()
def coupon__eq(basket: Basket, code: Annotated[str, Process(str.upper)]) -> bool:
    return basket.coupon == code


compiler = PredicateCompiler(
    promo_rules.rules,
    lambda wrapper: Predicate(lambda _: wrapper["operator"] == "all", operator="logical"),
)

PROMOTIONS_JSON = """
[
  {"name": "Welcome 15%", "percent": 15,
   "when": {"name": "first_order", "args": [], "kwargs": {}, "inverse": false}},
  {"name": "Books 10%", "percent": 10,
   "when": {"operator": "all", "expressions": [
     {"name": "has_category", "args": ["books"], "kwargs": {}, "inverse": false},
     {"name": "subtotal__ge", "args": [30], "kwargs": {}, "inverse": false}]}},
  {"name": "Black Friday 25%", "percent": 25,
   "when": {"name": "coupon__eq", "args": ["bf2026"], "kwargs": {}, "inverse": false}}
]
"""

# compile once at start-up: a broken promotion fails here, not at checkout
promotions = [
    {**promotion, "when": compiler.compile(promotion["when"])}
    for promotion in json.loads(PROMOTIONS_JSON)
]


def best_promotion(basket: Basket) -> str | None:
    eligible = [p for p in promotions if p["when"](basket)]

    if not eligible:
        return None

    return max(eligible, key=lambda p: p["percent"])["name"]


assert best_promotion(Basket(Decimal("45.00"), {"books"}, customer_orders=3)) == "Books 10%"
assert best_promotion(Basket(Decimal("45.00"), {"books"}, customer_orders=0)) == "Welcome 15%"
assert best_promotion(Basket(Decimal("12.00"), {"toys"}, customer_orders=3, coupon="BF2026")) == "Black Friday 25%"
assert best_promotion(Basket(Decimal("12.00"), {"books"}, customer_orders=3)) is None
```

## Feature flags and gradual rollouts

A mobile app turns features on for groups of users. Flags live in a config file and are
reloaded without a deploy.

```python
import hashlib
import json
from dataclasses import dataclass

from pyspecification import ObjectRulesRegistry, Predicate, PredicateCompiler


@dataclass(frozen=True)
class Context:
    user_id: str
    country: str
    app_version: tuple[int, int, int]
    is_staff: bool = False


flag_rules = ObjectRulesRegistry[Context, bool](operator="logical")


@flag_rules.rule()
def is_staff(context: Context) -> bool:
    return context.is_staff


@flag_rules.rule()
def country__in(context: Context, countries: list[str]) -> bool:
    return context.country in countries


@flag_rules.rule()
def app_version__ge(context: Context, version: str) -> bool:
    return context.app_version >= tuple(int(part) for part in version.split("."))


@flag_rules.rule()
def rollout_percent(context: Context, percent: int, *, salt: str) -> bool:
    """Stable bucketing: the same user always lands in the same bucket for a flag."""
    bucket = int(hashlib.sha256(f"{salt}:{context.user_id}".encode()).hexdigest(), 16) % 100
    return bucket < percent


compiler = PredicateCompiler(
    flag_rules.rules,
    lambda wrapper: Predicate(lambda _: wrapper["operator"] == "all", operator="logical"),
)

FLAGS = json.loads("""
{
  "new_checkout": {
    "operator": "any",
    "expressions": [
      {"name": "is_staff", "args": [], "kwargs": {}, "inverse": false},
      {"operator": "all", "expressions": [
        {"name": "country__in", "args": [["SY", "JO"]], "kwargs": {}, "inverse": false},
        {"name": "app_version__ge", "args": ["4.2.0"], "kwargs": {}, "inverse": false},
        {"name": "rollout_percent", "args": [100], "kwargs": {"salt": "new_checkout"}, "inverse": false}
      ]}
    ]
  }
}
""")

flags = {name: compiler.compile(definition) for name, definition in FLAGS.items()}


def is_enabled(flag: str, context: Context) -> bool:
    return flag in flags and flags[flag](context)


assert is_enabled("new_checkout", Context("u1", "DE", (3, 0, 0), is_staff=True))
assert is_enabled("new_checkout", Context("u2", "SY", (4, 3, 1)))
assert not is_enabled("new_checkout", Context("u3", "SY", (4, 1, 9)))
assert not is_enabled("unknown_flag", Context("u4", "SY", (9, 9, 9)))
```

Lower `100` to `10` to give the feature to a stable 10% of eligible users.

## Filtering an API from a query string

A JSON API accepts a rule in a `filter` query parameter. Bad filters must become a
`400` with a useful message, never a `500`.

```python
import json
from dataclasses import asdict, dataclass

from pyargprocessors import PyargprocessorsError

from pyspecification import ObjectRulesRegistry, Predicate, PredicateCompiler, PySpecificationError


@dataclass
class Book:
    title: str
    author: str
    year: int
    price: float


book_rules = ObjectRulesRegistry[Book, bool](operator="logical")


@book_rules.rule()
def author__eq(book: Book, name: str) -> bool:
    return book.author.casefold() == name.casefold()


@book_rules.rule()
def year__ge(book: Book, year: int) -> bool:
    return book.year >= year


@book_rules.rule()
def price__le(book: Book, amount: float) -> bool:
    return book.price <= amount


compiler = PredicateCompiler(
    book_rules.rules,
    lambda wrapper: Predicate(lambda _: wrapper["operator"] == "all", operator="logical"),
)

BOOKS = [
    Book("Season of Migration to the North", "Tayeb Salih", 1966, 14.0),
    Book("The Dove's Necklace", "Raja Alem", 2010, 18.5),
    Book("Minaret", "Leila Aboulela", 2005, 11.0),
]


def list_books(query: dict[str, str]) -> tuple[int, dict]:
    if "filter" not in query:
        return 200, {"books": [asdict(b) for b in BOOKS]}

    try:
        rule = compiler.compile(json.loads(query["filter"]))
    except json.JSONDecodeError as error:
        return 400, {"error": f"filter is not valid JSON: {error}"}
    except (PySpecificationError, PyargprocessorsError) as error:
        return 400, {"error": str(error), "at": getattr(error, "__notes__", [])}
    except TypeError as error:
        return 400, {"error": str(error).splitlines()[0]}

    return 200, {"books": [asdict(b) for b in BOOKS if rule(b)]}


recent_cheap = json.dumps(
    {
        "operator": "all",
        "expressions": [
            {"name": "year__ge", "args": [2000], "kwargs": {}, "inverse": False},
            {"name": "price__le", "args": [15], "kwargs": {}, "inverse": False},
        ],
    }
)

status, body = list_books({"filter": recent_cheap})

assert status == 200
assert [b["title"] for b in body["books"]] == ["Minaret"]

status, body = list_books({"filter": '{"name": "genre__eq", "args": ["novel"], "kwargs": {}, "inverse": false}'})

assert status == 400
assert body["error"].startswith("Rule 'genre__eq' does not exist. Available rules: author__eq")
assert body["at"] == ["at $"]

status, body = list_books({"filter": '{"name": "year__ge"}'})

assert (status, body["error"]) == (400, "Invalid expression at $.")
```

## Same rules in memory and in the database

A loyalty program stores who qualifies for "Gold" as one JSON rule. The nightly job finds
Gold members **in the database**; the member's app explains **in Python** why a member is
not Gold yet. Both use the same rule names and the same JSON.

```python
from sqlalchemy import ColumnElement, create_engine, false, select, true
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

from pyspecification import ObjectRulesRegistry, Predicate, PredicateCompiler


class Base(DeclarativeBase):
    pass


class Member(Base):
    __tablename__ = "members"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    points: Mapped[int]
    years: Mapped[int]
    suspended: Mapped[bool] = mapped_column(default=False)


# the same three rules, twice
sql = ObjectRulesRegistry[type[Member], ColumnElement[bool]](operator="bitwise")
python = ObjectRulesRegistry[Member, bool](operator="logical")


@sql.rule()
def points__ge(model: type[Member], points: int) -> ColumnElement[bool]:
    return model.points >= points


@python.rule(message="Collect more points")
def points__ge(member: Member, points: int) -> bool:  # noqa: F811
    return member.points >= points


@sql.rule()
def years__ge(model: type[Member], years: int) -> ColumnElement[bool]:
    return model.years >= years


@python.rule(message="Stay a member a little longer")
def years__ge(member: Member, years: int) -> bool:  # noqa: F811
    return member.years >= years


@sql.rule()
def suspended(model: type[Member]) -> ColumnElement[bool]:
    return model.suspended.is_(True)


@python.rule(message="Your account is suspended")
def suspended(member: Member) -> bool:  # noqa: F811
    return member.suspended


def sql_neutral(wrapper: dict) -> Predicate[type[Member], ColumnElement[bool]]:
    value = true() if wrapper["operator"] == "all" else false()
    return Predicate(lambda _: value, operator="bitwise")


def python_neutral(wrapper: dict) -> Predicate[Member, bool]:
    return Predicate(lambda _: wrapper["operator"] == "all", operator="logical")


GOLD = {
    "operator": "all",
    "expressions": [
        {"name": "suspended", "args": [], "kwargs": {}, "inverse": True},
        {
            "operator": "any",
            "expressions": [
                {"name": "points__ge", "args": [10_000], "kwargs": {}, "inverse": False},
                {"name": "years__ge", "args": [5], "kwargs": {}, "inverse": False},
            ],
        },
    ],
}

gold_in_sql = PredicateCompiler(sql.rules, sql_neutral).compile(GOLD)
gold_in_python = PredicateCompiler(python.rules, python_neutral).compile(GOLD)

engine = create_engine("sqlite:///:memory:")
Base.metadata.create_all(engine)

with Session(engine) as session:
    session.add_all(
        [
            Member(name="Rana", points=12_000, years=1),
            Member(name="Omar", points=800, years=7),
            Member(name="Lina", points=50_000, years=9, suspended=True),
            Member(name="Sami", points=3_000, years=2),
        ]
    )
    session.commit()

    gold = session.scalars(select(Member).where(gold_in_sql(Member)).order_by(Member.id)).all()

    assert [m.name for m in gold] == ["Rana", "Omar"]

    sami = session.scalars(select(Member).where(Member.name == "Sami")).one()

    assert [f.message for f in gold_in_python.failures(sami)] == [
        "Collect more points",
        "Stay a member a little longer",
    ]
```

Keep the two implementations next to each other and test them against the same rows,
so they never drift apart.
