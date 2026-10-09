from datetime import date
from decimal import Decimal
from enum import StrEnum
from inspect import signature
from typing import Annotated, Any

import pytest
from pyspecification import (
    InvalidParserError,
    InvalidRuleError,
    MissingArgumentError,
    Parse,
    ParseArgumentError,
    object_rule,
    subscriptable_rule,
)
from pyspecification.annotations import annotated_metadata, resolved_annotations
from pyspecification.parsers import find_parsers, input_annotation, parse_arguments


class Milk(StrEnum):
    OAT = "oat"
    SOY = "soy"


def normalize(text: str) -> str:
    return text.strip().lower()


def load_rows(path: str) -> list[str]:
    return [f"row from {path}"]


type Text = Annotated[str, Parse(normalize)]
type Rows = Annotated[list[str], Parse(load_rows)]


@object_rule()
def order(log: list[Any], name: Text, amount: Annotated[int, Parse(int)] = 1) -> bool:
    return (name, amount) in log


class TestParse:
    def test_holds_the_function(self) -> None:
        assert Parse(int).fn is int

    def test_is_immutable_and_comparable(self) -> None:
        assert Parse(int) == Parse(int)
        assert Parse(int) != Parse(float)
        with pytest.raises(AttributeError):
            Parse(int).fn = float  # type: ignore[misc]

    @pytest.mark.parametrize("fn", [None, 5, "int"])
    def test_needs_a_callable(self, fn: Any) -> None:
        with pytest.raises(InvalidParserError, match="Parse needs a callable"):
            Parse(fn)

    def test_invalid_parser_error_is_a_type_error(self) -> None:
        assert issubclass(InvalidParserError, TypeError)


class TestParsingArguments:
    def test_positional_and_keyword(self) -> None:
        assert order(" Tea ", "2")([("tea", 2)]) is True
        assert order(name=" Tea ", amount="2")([("tea", 2)]) is True

    def test_defaults_are_not_parsed(self) -> None:
        @object_rule()
        def pour(log: list[Any], ml: Annotated[int, Parse(int)] = "a lot") -> bool:  # type: ignore[assignment]
            return ml in log

        assert pour()(["a lot"]) is True

    def test_unmarked_arguments_are_untouched(self) -> None:
        marker = object()

        @object_rule()
        def keep(log: list[Any], value: object, amount: Annotated[int, Parse(int)]) -> bool:
            return log == [value, amount]

        assert keep(marker, "3")([marker, 3]) is True

    def test_alias_is_reused_across_rules(self) -> None:
        @object_rule()
        def first(log: list[Any], rows: Rows) -> bool:
            return rows == log

        @object_rule()
        def second(log: list[Any], label: Text, rows: Rows) -> bool:
            return [label, *rows] == log

        assert (first("a.csv") & ~second(" B ", "b.csv"))(["row from a.csv"]) is True
        assert second(" B ", "b.csv")(["b", "row from b.csv"]) is True

    def test_chained_parsers_run_left_to_right(self) -> None:
        @object_rule()
        def tag(
            log: list[Any], value: Annotated[str, Parse(str.strip), Parse(str.upper), Parse(list)]
        ) -> bool:
            return value == log

        assert tag(" ab ")(["A", "B"]) is True

    def test_var_positional_parses_each_item(self) -> None:
        @object_rule()
        def top(log: list[Any], *toppings: Text) -> bool:
            return list(toppings) == log

        assert top(" Foam", "COCOA ")(["foam", "cocoa"]) is True
        assert top()([]) is True

    def test_var_keyword_parses_each_value(self) -> None:
        @object_rule()
        def where(
            log: list[Any], *, strict: Annotated[bool, Parse(bool)] = False, **fields: Text
        ) -> bool:
            return log == [strict, fields]

        assert where(strict=1, brand=" SONIC ", color="Red")([True, {"brand": "sonic", "color": "red"}])

    def test_other_annotated_metadata_is_ignored(self) -> None:
        @object_rule()
        def add(total: int, amount: Annotated[int, "documentation", Parse(int), 42]) -> bool:
            return total + amount == 3

        assert add("2")(1) is True

    def test_string_annotations(self) -> None:
        @object_rule()
        def later(log: list[Any], name: "Text") -> bool:
            return log == [name]

        assert later(" X ")(["x"]) is True

    @pytest.mark.parametrize(
        ("parser", "raw", "expected"),
        [
            (Decimal, "2.50", Decimal("2.50")),
            (date.fromisoformat, "2026-10-09", date(2026, 10, 9)),
            (Milk, "oat", Milk.OAT),
            (lambda value: value * 2, 21, 42),
        ],
    )
    def test_any_callable_can_parse(self, parser: Any, raw: Any, expected: Any) -> None:
        @object_rule()
        def keep(log: list[Any], value: Annotated[Any, Parse(parser)]) -> bool:
            return log == [value]

        assert keep(raw)([expected]) is True

    def test_subscriptable_rule_parses_arguments_but_not_the_key(self) -> None:
        @subscriptable_rule()
        def number__gt(
            obj: dict[str, int], key: str, limit: Annotated[int, Parse(int)]
        ) -> bool:
            return obj[key] > limit

        assert number__gt("age", "18")({"age": 20}) is True
        assert number__gt("age", limit="30")({"age": 20}) is False

    def test_factory_signature_keeps_the_parameters_without_the_object(self) -> None:
        assert list(signature(order).parameters) == ["name", "amount"]

    def test_parsed_value_is_the_one_the_rule_sees(self) -> None:
        seen: list[Any] = []

        @object_rule()
        def remember(_: object, value: Text) -> bool:
            seen.append(value)
            return True

        remember("  V ")(None)
        assert seen == ["v"]


class TestWhenParsingHappens:
    def test_once_when_the_rule_is_built(self) -> None:
        calls: list[str] = []

        def load(path: str) -> str:
            calls.append(path)
            return path.upper()

        @object_rule()
        def use(log: list[Any], data: Annotated[str, Parse(load)]) -> bool:
            return data in log

        predicate = use("a.csv")
        assert calls == ["a.csv"]

        assert predicate(["A.CSV"]) is True
        assert predicate(["A.CSV"]) is True
        assert calls == ["a.csv"]

    def test_bad_arguments_fail_before_parsing(self) -> None:
        calls: list[Any] = []

        @object_rule()
        def use(log: list[Any], data: Annotated[str, Parse(calls.append)], other: str) -> bool:
            return bool(log)

        with pytest.raises(MissingArgumentError, match="'other'"):
            use("x")
        assert calls == []


class TestFailures:
    def test_failure_names_the_argument_and_value(self) -> None:
        with pytest.raises(
            ParseArgumentError, match="Argument 'amount' with value 'two' failed to parse"
        ) as info:
            order("tea", "two")

        assert isinstance(info.value.__cause__, ValueError)

    def test_failure_is_a_type_error(self) -> None:
        with pytest.raises(TypeError):
            order("tea", "two")

    def test_failure_inside_var_positional(self) -> None:
        @object_rule()
        def total(log: list[Any], *amounts: Annotated[int, Parse(int)]) -> bool:
            return sum(amounts) == len(log)

        with pytest.raises(ParseArgumentError, match="Argument 'amounts' with value 'x'"):
            total("1", "x")

    def test_failure_inside_var_keyword_names_the_key(self) -> None:
        @object_rule()
        def where(log: list[Any], **fields: Text) -> bool:
            return bool(log)

        with pytest.raises(ParseArgumentError, match="Argument 'brand' with value 5"):
            where(brand=5)

    def test_failure_in_the_second_parser_reports_the_original_value(self) -> None:
        @object_rule()
        def count(log: list[Any], n: Annotated[int, Parse(str.strip), Parse(int)]) -> bool:
            return bool(log)

        with pytest.raises(ParseArgumentError, match="Argument 'n' with value ' x '"):
            count(" x ")


class TestInvalidDeclarations:
    def test_marker_as_default_value(self) -> None:
        def bad(log: list[Any], amount: int = Parse(int)) -> bool:  # type: ignore[assignment]
            return bool(log)

        with pytest.raises(
            InvalidParserError, match=r"uses Parse as the default of 'amount'.*Annotated"
        ):
            object_rule()(bad)

    def test_object_under_test_cannot_be_parsed(self) -> None:
        def bad(log: Text, amount: int) -> bool:
            return bool(log)

        with pytest.raises(InvalidParserError, match="'bad' cannot parse 'log'"):
            object_rule()(bad)

    def test_key_cannot_be_parsed(self) -> None:
        def bad(obj: dict[str, Any], key: Text) -> bool:
            return bool(obj)

        with pytest.raises(InvalidParserError, match="'bad' cannot parse 'key'"):
            subscriptable_rule()(bad)

    def test_rule_without_object_parameter(self) -> None:
        def bad() -> bool:
            return True

        with pytest.raises(InvalidRuleError, match="'bad' must accept the object under test"):
            object_rule()(bad)

    def test_subscriptable_rule_without_key_parameter(self) -> None:
        def bad(obj: dict[str, Any]) -> bool:
            return bool(obj)

        with pytest.raises(InvalidRuleError, match="the object under test and the key"):
            subscriptable_rule()(bad)

    def test_object_parameter_must_be_positional(self) -> None:
        def bad(*, obj: object) -> bool:
            return bool(obj)

        with pytest.raises(InvalidRuleError):
            object_rule()(bad)  # type: ignore[arg-type]

    def test_function_without_an_introspectable_signature(self) -> None:
        with pytest.raises(InvalidRuleError, match="'max' must accept the object under test"):
            object_rule()(max)  # type: ignore[arg-type]

    def test_invalid_rule_error_is_a_type_error(self) -> None:
        assert issubclass(InvalidRuleError, TypeError)


class TestHelpers:
    def test_find_parsers(self) -> None:
        def fn(
            subject: object, a: Text, b: int, c: Annotated[int, Parse(int), Parse(abs)] = 0
        ) -> None: ...

        assert find_parsers(fn, "fn") == {
            "a": (Parse(normalize),),
            "c": (Parse(int), Parse(abs)),
        }

    def test_parse_arguments_returns_new_bound_arguments(self) -> None:
        def fn(a: str, b: str = "") -> None: ...

        bound = signature(fn).bind(" A ")
        parsed = parse_arguments({"a": (Parse(normalize),)}, bound)

        assert parsed.arguments == {"a": "a"}
        assert bound.arguments == {"a": " A "}
        assert parsed.args == ("a",)

    @pytest.mark.parametrize(
        ("parser", "expected"),
        [
            (load_rows, str),
            (normalize, str),
            (int, None),
            (str.strip, None),
            (lambda value: value, None),
            (lambda: None, None),
        ],
    )
    def test_input_annotation(self, parser: Any, expected: Any) -> None:
        assert input_annotation(Parse(parser)) is expected


class TestAnnotations:
    def test_annotated_metadata_looks_through_aliases(self) -> None:
        type Port = Annotated[int, "tcp", 8080]
        type Tagged[T] = Annotated[T, "tag"]

        assert annotated_metadata(Port) == ("tcp", 8080)
        assert annotated_metadata(int) == ()
        assert annotated_metadata(Tagged[int]) == ("tag",)
        assert annotated_metadata(Annotated[Tagged[Port], "outer"]) == (
            "tcp",
            8080,
            "tag",
            "outer",
        )

    def test_annotated_metadata_of_alias_ignoring_its_type_parameter(self) -> None:
        type Fixed[T] = Annotated[int, "fixed"]

        assert annotated_metadata(Fixed[str]) == ("fixed",)

    def test_resolved_annotations_evaluates_strings_and_falls_back(self) -> None:
        def resolvable(user: object, age: "int") -> None: ...
        def unresolvable(user: object, age: "Nope") -> None: ...  # noqa: F821

        assert resolved_annotations(resolvable) == {"user": object, "age": int, "return": None}
        assert resolved_annotations(unresolvable)["age"] == "Nope"

    def test_resolved_annotations_of_class_callable_object_and_partial(self) -> None:
        from functools import partial

        class Greeter:
            def __init__(self, name: str) -> None: ...

        class Caller:
            def __call__(self, count: int) -> None: ...

        def fn(a: int, b: str) -> None: ...

        assert resolved_annotations(Greeter) == {"name": str, "return": None}
        assert resolved_annotations(Caller()) == {"count": int, "return": None}
        assert resolved_annotations(partial(fn, 1)) == resolved_annotations(fn)
