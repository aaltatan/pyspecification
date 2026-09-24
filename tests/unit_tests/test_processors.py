from datetime import date
from decimal import Decimal
from inspect import Parameter, signature
from typing import Any

import pytest
from pyspecification import InvalidProcessorsError, ProcessArgumentError
from pyspecification.processors import process_arguments, processor_lookup


def between(low: int, high: int, *extras: str, **options: str) -> None: ...


def plain(low: int, high: int) -> None: ...


def parameters_of(fn: Any) -> dict[str, Parameter]:
    return dict(signature(fn).parameters)


# -----------------------
# processor_lookup
# -----------------------


def test_lookup_with_callable_applies_to_every_name() -> None:
    lookup = processor_lookup(int, parameters_of(plain), "rule")

    assert lookup("low") is int
    assert lookup("anything") is int


def test_lookup_with_mapping_applies_only_to_named_parameters() -> None:
    lookup = processor_lookup({"low": int}, parameters_of(plain), "rule")

    assert lookup("low") is int
    assert lookup("high") is None


def test_lookup_with_ellipsis_covers_remaining_parameters() -> None:
    lookup = processor_lookup({"low": int, ...: str.strip}, parameters_of(plain), "rule")

    assert lookup("low") is int
    assert lookup("high") is str.strip


def test_lookup_with_empty_mapping_processes_nothing() -> None:
    lookup = processor_lookup({}, parameters_of(plain), "rule")

    assert lookup("low") is None


def test_lookup_with_only_ellipsis_is_allowed_for_rule_without_parameters() -> None:
    lookup = processor_lookup({...: int}, {}, "rule")

    assert lookup("whatever") is int


@pytest.mark.parametrize("processors", [None, 5, "int", ["low"], (int, {})])
def test_lookup_rejects_processors_of_wrong_type(processors: Any) -> None:
    with pytest.raises(InvalidProcessorsError, match="must be a callable or a mapping"):
        processor_lookup(processors, parameters_of(plain), "rule")


def test_lookup_rejects_non_callable_processor() -> None:
    with pytest.raises(InvalidProcessorsError, match=r"must be callables, not for \['low'\]"):
        processor_lookup({"low": "int"}, parameters_of(plain), "rule")  # type: ignore[dict-item]


def test_lookup_rejects_unknown_parameter_and_lists_available_ones() -> None:
    with pytest.raises(InvalidProcessorsError) as error:
        processor_lookup({"lwo": int}, parameters_of(plain), "age__between")

    assert "Processors of rule 'age__between' name unknown parameters ['lwo']" in str(error.value)
    assert "available parameters: low, high" in str(error.value)


def test_lookup_reports_none_when_rule_has_no_parameters() -> None:
    with pytest.raises(InvalidProcessorsError, match=r"available parameters: \(none\)"):
        processor_lookup({"low": int}, {}, "rule")


def test_lookup_allows_any_key_when_rule_accepts_var_keyword() -> None:
    lookup = processor_lookup({"anything": int}, parameters_of(between), "rule")

    assert lookup("anything") is int


def test_invalid_processors_error_is_a_type_error() -> None:
    assert issubclass(InvalidProcessorsError, TypeError)


# -----------------------
# process_arguments
# -----------------------


def test_process_arguments_by_parameter_name_for_positional_and_keyword_values() -> None:
    lookup = {"low": int, "high": Decimal}.get
    bound = signature(plain).bind("1", high="2.5")

    processed = process_arguments(lookup, bound)

    assert processed.arguments == {"low": 1, "high": Decimal("2.5")}


def test_process_arguments_applies_processor_to_each_var_positional_item() -> None:
    bound = signature(between).bind(1, 2, " a ", " b ")

    processed = process_arguments({"extras": str.strip}.get, bound)

    assert processed.args == (1, 2, "a", "b")


def test_process_arguments_looks_up_each_var_keyword_name_individually() -> None:
    bound = signature(between).bind(1, 2, mode="L", note=" hot ")

    processed = process_arguments({"mode": str.lower}.get, bound)

    assert processed.kwargs == {"mode": "l", "note": " hot "}


def test_process_arguments_keeps_values_without_processor() -> None:
    bound = signature(plain).bind("1", "2")

    assert process_arguments({}.get, bound).args == ("1", "2")


def test_process_arguments_does_not_mutate_original_bound_arguments() -> None:
    bound = signature(plain).bind("1", "2")

    process_arguments(lambda _: int, bound)

    assert bound.args == ("1", "2")


def test_process_arguments_does_not_invent_arguments_that_were_not_passed() -> None:
    def with_default(low: int, high: int = 5) -> None: ...

    bound = signature(with_default).bind("1")

    assert process_arguments(lambda _: int, bound).arguments == {"low": 1}


def test_process_arguments_with_processor_returning_none_keeps_none() -> None:
    bound = signature(plain).bind("1", "2")

    assert process_arguments(lambda _: (lambda _v: None), bound).args == (None, None)


def test_process_arguments_wraps_failure_with_parameter_name_and_value() -> None:
    bound = signature(plain).bind("abc", "2")

    with pytest.raises(ProcessArgumentError) as error:
        process_arguments(lambda _: int, bound)

    assert "Argument 'low' with value 'abc' failed to process" in str(error.value)
    assert isinstance(error.value.__cause__, ValueError)


def test_process_arguments_reports_keyword_name_for_var_keyword_failure() -> None:
    bound = signature(between).bind(1, 2, day="not-a-date")

    with pytest.raises(ProcessArgumentError, match="Argument 'day' with value 'not-a-date'"):
        process_arguments({"day": date.fromisoformat}.get, bound)


def test_process_arguments_reports_var_positional_parameter_name_on_failure() -> None:
    bound = signature(between).bind(1, 2, "ok", 3)

    with pytest.raises(ProcessArgumentError, match="Argument 'extras' with value 3"):
        process_arguments({"extras": str.strip}.get, bound)


def test_process_argument_error_is_a_type_error() -> None:
    assert issubclass(ProcessArgumentError, TypeError)
