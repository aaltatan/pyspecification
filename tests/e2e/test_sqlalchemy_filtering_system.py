from collections.abc import Generator
from typing import Any

import pytest
from pyspecification import ObjectRulesRegistry, Predicate, PredicateCompiler, RuleSchema
from sqlalchemy import ColumnElement, and_, create_engine, or_
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    age: Mapped[int] = mapped_column(default=0)
    is_admin: Mapped[bool] = mapped_column(default=False)


engine = create_engine("sqlite:///:memory:")
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="session")
def session() -> Generator[Session, None, None]:
    db_session = SessionLocal()
    try:
        yield db_session
    finally:
        db_session.close()


@pytest.fixture(scope="session", autouse=True)
def create_db_and_add_users(session: Session) -> Generator[None, None, None]:
    Base.metadata.create_all(engine)

    for user in [
        User(name="Abdullah", age=18, is_admin=True),
        User(name="Bob", age=16, is_admin=True),
        User(name="Charlie", age=20, is_admin=False),
        User(name="David", age=12, is_admin=False),
        User(name="Eve", age=8, is_admin=True),
        User(name="Rama", age=3, is_admin=False),
    ]:
        session.add(user)

    session.commit()

    yield

    session.query(User).delete()
    Base.metadata.drop_all(engine)


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


@pytest.fixture
def sqlalchemy_compiler() -> PredicateCompiler[type[User], ColumnElement[bool]]:
    return PredicateCompiler(
        rules.rules,
        lambda schema: Predicate(
            lambda _: and_(True) if schema["operator"] == "and" else or_(False),  # noqa: FBT003
            operator="bitwise",
        ),
    )


def test_query(session: Session) -> None:
    users = session.query(User).all()
    assert len(users) == 6


@pytest.mark.parametrize(
    "filter_rule_data, expected_names",
    [
        (
            {
                "is_admin": [],
            },
            ("Abdullah", "Bob", "Eve"),
        ),
        (
            {
                "age__ge": [18],
            },
            ("Abdullah", "Charlie"),
        ),
        (
            {
                "name__iendswith": ["e"],
            },
            ("Charlie", "Eve"),
        ),
        (
            {
                "age__ge": [18],
                "age__le": [30],
                "-is_admin": [],
            },
            ("Charlie",),
        ),
        (
            {
                "operator": "or",
                "expressions": [
                    {"-is_admin": []},
                    {"age__ge": [18]},
                ],
            },
            ("Abdullah", "Charlie", "David", "Rama"),
        ),
    ],
)
def test_filtering_system(
    session: Session,
    sqlalchemy_compiler: PredicateCompiler[type[User], ColumnElement[bool]],
    filter_rule_data: dict[str, Any],
    expected_names: tuple[str, ...],
) -> None:
    # Arrange
    filter_expression = sqlalchemy_compiler.compile(RuleSchema(**filter_rule_data).model_dump())
    filtered_data = session.query(User).filter(filter_expression(User)).all()

    # Act & Assert
    assert tuple([user.name for user in filtered_data]) == expected_names
    assert len(filtered_data) == len(expected_names)
