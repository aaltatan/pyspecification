# SQLAlchemy

Rules receive the **model class** and return a SQLAlchemy condition. Composed with `&`,
`|` and `~`, they build one `WHERE` clause that you pass to `select().where(...)` or
`query.filter(...)`.

## Example: an order search screen

A back office lets staff search orders by status, total, date and customer country,
and saves searches as JSON.

### Models and data

```python
from datetime import date

from sqlalchemy import ForeignKey, create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Customer(Base):
    __tablename__ = "customers"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    country: Mapped[str]


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True)
    status: Mapped[str]
    total: Mapped[float]
    placed_on: Mapped[date]
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"))
    customer: Mapped[Customer] = relationship()


engine = create_engine("sqlite:///:memory:")
Base.metadata.create_all(engine)

with Session(engine) as session:
    rana = Customer(name="Rana", country="SY")
    omar = Customer(name="Omar", country="LB")
    jana = Customer(name="Jana", country="DE")

    session.add_all(
        [
            Order(id=1, status="paid", total=120.0, placed_on=date(2026, 11, 2), customer=rana),
            Order(id=2, status="paid", total=35.5, placed_on=date(2026, 11, 20), customer=omar),
            Order(id=3, status="refunded", total=300.0, placed_on=date(2026, 10, 9), customer=rana),
            Order(id=4, status="pending", total=980.0, placed_on=date(2026, 11, 25), customer=jana),
            Order(id=5, status="paid", total=640.0, placed_on=date(2026, 9, 30), customer=omar),
        ]
    )
    session.commit()
```

### Rules

```python
from typing import Annotated

from sqlalchemy import ColumnElement

from pyspecification import ObjectRulesRegistry, Process

order_rules = ObjectRulesRegistry[type[Order], ColumnElement[bool]](operator="bitwise")


@order_rules.rule()
def status__in(model: type[Order], statuses: list[str]) -> ColumnElement[bool]:
    """The order status is one of the values."""
    return model.status.in_(statuses)


@order_rules.rule()
def total__ge(model: type[Order], amount: float) -> ColumnElement[bool]:
    """The order total is at least the amount."""
    return model.total >= amount


@order_rules.rule()
def placed_on__between(
    model: type[Order],
    start: Annotated[date, Process(date.fromisoformat)],
    end: Annotated[date, Process(date.fromisoformat)],
) -> ColumnElement[bool]:
    """The order was placed between two dates, both included."""
    return model.placed_on.between(start, end)


@order_rules.rule()
def customer_country__eq(model: type[Order], country: str) -> ColumnElement[bool]:
    """The customer lives in the country."""
    return model.customer.has(Customer.country == country)
```

`customer_country__eq` filters through a relationship with `has()`: a rule can return
any SQLAlchemy condition, including subqueries, `EXISTS`, functions and JSON operators.

### Composing in code

```python
big_paid_orders = order_rules["status__in"](["paid"]) & order_rules["total__ge"](100)

with Session(engine) as session:
    found = session.scalars(select(Order).where(big_paid_orders(Order)).order_by(Order.id)).all()

assert [o.id for o in found] == [1, 5]
```

`big_paid_orders(Order)` returns a plain SQLAlchemy expression:

```python
assert str(big_paid_orders(Order)) == (
    "orders.status IN (__[POSTCOMPILE_status_1]) AND orders.total >= :total_1"
)
```

### Compiling saved searches

The compiler needs a starting predicate for each `all`/`any` group. In SQL the neutral
elements are `TRUE` and `FALSE`; SQLAlchemy removes them from the final clause:

```python
from sqlalchemy import false, true

from pyspecification import Predicate, PredicateCompiler


def neutral(wrapper: dict) -> Predicate[type[Order], ColumnElement[bool]]:
    value = true() if wrapper["operator"] == "all" else false()
    return Predicate(lambda _: value, operator="bitwise")


compiler = PredicateCompiler(order_rules.rules, neutral)

saved_search = {
    "operator": "all",
    "expressions": [
        {"name": "placed_on__between", "args": ["2026-11-01", "2026-11-30"], "kwargs": {}, "inverse": False},
        {"name": "status__in", "args": [["refunded"]], "kwargs": {}, "inverse": True},
        {
            "operator": "any",
            "expressions": [
                {"name": "total__ge", "args": [500], "kwargs": {}, "inverse": False},
                {"name": "customer_country__eq", "args": ["SY"], "kwargs": {}, "inverse": False},
            ],
        },
    ],
}

where = compiler.compile(saved_search)

with Session(engine) as session:
    found = session.scalars(select(Order).where(where(Order)).order_by(Order.id)).all()

assert [o.id for o in found] == [1, 4]
```

Order 2 is in November and not refunded, but it is neither large nor Syrian. Order 5 is
large but from September.

### Paginating and counting

The predicate is evaluated once to build the clause; reuse it for as many statements as
you like:

```python
from sqlalchemy import func

clause = where(Order)

with Session(engine) as session:
    total = session.scalar(select(func.count()).select_from(Order).where(clause))
    first_page = session.scalars(select(Order).where(clause).order_by(Order.id).limit(1)).all()

assert total == 2
assert [o.id for o in first_page] == [1]
```

## Things to know

- Use `operator="bitwise"`. Python's `and`/`or` on SQLAlchemy expressions raise
  `TypeError: Boolean value of this clause is not defined`.
- For a boolean column write `model.is_active.is_(True)` or `model.is_active == True`
  (with `# noqa: E712`); `not model.is_active` does not build SQL.
- `failures()` is not available on bitwise predicates. Keep a logical twin of the rules
  to explain a single row: see the
  [recipe](../recipes.md#same-rules-in-memory-and-in-the-database).
- The repository has a complete end-to-end test in
  [`tests/e2e/test_sqlalchemy_filtering_system.py`](https://github.com/aaltatan/pyspecification/blob/main/tests/e2e/test_sqlalchemy_filtering_system.py).
