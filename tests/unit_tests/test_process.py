from datetime import date
from decimal import Decimal
from enum import StrEnum
from inspect import signature
from typing import Annotated, Any

import pytest
from pyspecification import (
    InvalidProcessorError,
    InvalidRuleError,
    MissingArgumentError,
    Process,
    ProcessArgumentError,
    object_rule,
    subscriptable_rule,
)


class Milk(StrEnum):
    OAT = "oat"
    SOY = "soy"


def normalize(text: str) -> str:
    return text.strip().lower()


def load_rows(path: str) -> list[str]:
    return [f"row from {path}"]


type Text = Annotated[str, Process(normalize)]
type Rows = Annotated[list[str], Process(load_rows)]


@object_rule()
def order(log: list[Any], name: Text, amount: Annotated[int, Process(int)] = 1) -> bool:
    return (name, amount) in log


class TestProcessingArguments:
    def test_positional_and_keyword(self) -> None:
        assert order(" Tea ", "2")([("tea", 2)]) is True
        assert order(name=" Tea ", amount="2")([("tea", 2)]) is True

    def test_defaults_are_not_processed(self) -> None:
        @object_rule()
        def pour(log: list[Any], ml: Annotated[int, Process(int)] = "a lot") -> bool:  # type: ignore[assignment]
            return ml in log

        assert pour()(["a lot"]) is True

    def test_unmarked_arguments_are_untouched(self) -> None:
        marker = object()

        @object_rule()
        def keep(log: list[Any], value: object, amount: Annotated[int, Process(int)]) -> bool:
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

    def test_chained_processors_run_left_to_right(self) -> None:
        @object_rule()
        def tag(
            log: list[Any], value: Annotated[str, Process(str.strip), Process(str.upper), Process(list)]
        ) -> bool:
            return value == log

        assert tag(" ab ")(["A", "B"]) is True

    def test_var_positional_processes_each_item(self) -> None:
        @object_rule()
        def top(log: list[Any], *toppings: Text) -> bool:
            return list(toppings) == log

        assert top(" Foam", "COCOA ")(["foam", "cocoa"]) is True
        assert top()([]) is True

    def test_var_keyword_processes_each_value(self) -> None:
        @object_rule()
        def where(
            log: list[Any], *, strict: Annotated[bool, Process(bool)] = False, **fields: Text
        ) -> bool:
            return log == [strict, fields]

        assert where(strict=1, brand=" SONIC ", color="Red")([True, {"brand": "sonic", "color": "red"}])

    def test_other_annotated_metadata_is_ignored(self) -> None:
        @object_rule()
        def add(total: int, amount: Annotated[int, "documentation", Process(int), 42]) -> bool:
            return total + amount == 3

        assert add("2")(1) is True

    def test_string_annotations(self) -> None:
        @object_rule()
        def later(log: list[Any], name: "Text") -> bool:
            return log == [name]

        assert later(" X ")(["x"]) is True

    @pytest.mark.parametrize(
        ("processor", "raw", "expected"),
        [
            (Decimal, "2.50", Decimal("2.50")),
            (date.fromisoformat, "2026-10-09", date(2026, 10, 9)),
            (Milk, "oat", Milk.OAT),
            (lambda value: value * 2, 21, 42),
        ],
    )
    def test_any_callable_can_process(self, processor: Any, raw: Any, expected: Any) -> None:
        @object_rule()
        def keep(log: list[Any], value: Annotated[Any, Process(processor)]) -> bool:
            return log == [value]

        assert keep(raw)([expected]) is True

    def test_subscriptable_rule_processes_arguments_but_not_the_key(self) -> None:
        @subscriptable_rule()
        def number__gt(
            obj: dict[str, int], key: str, limit: Annotated[int, Process(int)]
        ) -> bool:
            return obj[key] > limit

        assert number__gt("age", "18")({"age": 20}) is True
        assert number__gt("age", limit="30")({"age": 20}) is False

    def test_factory_signature_keeps_the_parameters_without_the_object(self) -> None:
        assert list(signature(order).parameters) == ["name", "amount"]

    def test_processed_value_is_the_one_the_rule_sees(self) -> None:
        seen: list[Any] = []

        @object_rule()
        def remember(_: object, value: Text) -> bool:
            seen.append(value)
            return True

        remember("  V ")(None)
        assert seen == ["v"]


class TestWhenProcessingHappens:
    def test_once_when_the_rule_is_built(self) -> None:
        calls: list[str] = []

        def load(path: str) -> str:
            calls.append(path)
            return path.upper()

        @object_rule()
        def use(log: list[Any], data: Annotated[str, Process(load)]) -> bool:
            return data in log

        predicate = use("a.csv")
        assert calls == ["a.csv"]

        assert predicate(["A.CSV"]) is True
        assert predicate(["A.CSV"]) is True
        assert calls == ["a.csv"]

    def test_bad_arguments_fail_before_processing(self) -> None:
        calls: list[Any] = []

        @object_rule()
        def use(log: list[Any], data: Annotated[str, Process(calls.append)], other: str) -> bool:
            return bool(log)

        with pytest.raises(MissingArgumentError, match="'other'"):
            use("x")
        assert calls == []


class TestFailures:
    def test_failure_names_the_argument_and_value(self) -> None:
        with pytest.raises(
            ProcessArgumentError, match="Argument 'amount' with value 'two' failed to process"
        ) as info:
            order("tea", "two")

        assert isinstance(info.value.__cause__, ValueError)

    def test_failure_is_a_type_error(self) -> None:
        with pytest.raises(TypeError):
            order("tea", "two")

    def test_failure_inside_var_positional(self) -> None:
        @object_rule()
        def total(log: list[Any], *amounts: Annotated[int, Process(int)]) -> bool:
            return sum(amounts) == len(log)

        with pytest.raises(ProcessArgumentError, match="Argument 'amounts' with value 'x'"):
            total("1", "x")

    def test_failure_inside_var_keyword_names_the_key(self) -> None:
        @object_rule()
        def where(log: list[Any], **fields: Text) -> bool:
            return bool(log)

        with pytest.raises(ProcessArgumentError, match="Argument 'brand' with value 5"):
            where(brand=5)

    def test_failure_in_the_second_processor_reports_the_original_value(self) -> None:
        @object_rule()
        def count(log: list[Any], n: Annotated[int, Process(str.strip), Process(int)]) -> bool:
            return bool(log)

        with pytest.raises(ProcessArgumentError, match="Argument 'n' with value ' x '"):
            count(" x ")


class TestInvalidDeclarations:
    def test_marker_as_default_value(self) -> None:
        def bad(log: list[Any], amount: int = Process(int)) -> bool:  # type: ignore[assignment]
            return bool(log)

        with pytest.raises(
            InvalidProcessorError, match=r"uses Process as the default of 'amount'.*Annotated"
        ):
            object_rule()(bad)

    def test_object_under_test_cannot_be_processed(self) -> None:
        def bad(log: Text, amount: int) -> bool:
            return bool(log)

        with pytest.raises(InvalidProcessorError, match="'bad' cannot process 'log'"):
            object_rule()(bad)

    def test_key_cannot_be_processed(self) -> None:
        def bad(obj: dict[str, Any], key: Text) -> bool:
            return bool(obj)

        with pytest.raises(InvalidProcessorError, match="'bad' cannot process 'key'"):
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
