# ruff: noqa: DTZ007, DTZ001
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any

import pytest
from pyspecification import ProcessArgumentError
from pyspecification.processors import ProcessFn, process_arguments


@pytest.fixture
def processors_tuple() -> tuple[ProcessFn, dict[str, ProcessFn]]:
    return (
        lambda v: datetime.strptime(v, "%d-%m-%Y"),
        {
            "new_value": lambda v: datetime.strptime(v, "%d-%m-%Y"),
        },
    )


@pytest.mark.parametrize(
    "processors, arguments, expected",
    [
        (
            (lambda value: value * 2, {}),
            (
                (1,),
                {"value": 2},
            ),
            (
                (2,),
                {"value": 4},
            ),
        ),
        (
            (lambda value: value * 2, {"value": lambda _: "X"}),
            (
                (1,),
                {"value": 2},
            ),
            (
                (2,),
                {"value": "X"},
            ),
        ),
        (
            (Decimal, {}),
            (
                ("10.22", "100.11", "1000.22", 100),
                {},
            ),
            (
                (
                    Decimal("10.22"),
                    Decimal("100.11"),
                    Decimal("1000.22"),
                    Decimal(100),
                ),
                {},
            ),
        ),
        (
            (
                lambda value: datetime.strptime(value, "%d-%m-%Y"),
                {
                    "start_date": lambda value: (
                        datetime.strptime(value, "%d-%m-%Y") + timedelta(days=1)
                    ),
                },
            ),
            (
                ("01-01-2023", "02-02-2023", "03-03-2023"),
                {
                    "start_date": "01-01-2023",
                    "end_date": "03-03-2023",
                },
            ),
            (
                (datetime(2023, 1, 1), datetime(2023, 2, 2), datetime(2023, 3, 3)),
                {
                    "start_date": datetime(2023, 1, 2),
                    "end_date": datetime(2023, 3, 3),
                },
            ),
        ),
    ],
)
def test_process_arguments(
    processors: tuple[ProcessFn, dict[str, ProcessFn]],
    arguments: tuple[tuple[Any, ...], dict[str, Any]],
    expected: tuple[tuple[Any, ...], dict[str, Any]],
) -> None:
    args, kwargs = arguments
    assert process_arguments(processors, *args, **kwargs) == expected


def test_raises_process_argument_error(
    processors_tuple: tuple[ProcessFn, dict[str, ProcessFn]],
) -> None:
    with pytest.raises(ProcessArgumentError):
        process_arguments(processors_tuple, "xxx")


def test_raises_process_argument_error_2(
    processors_tuple: tuple[ProcessFn, dict[str, ProcessFn]],
) -> None:
    with pytest.raises(ProcessArgumentError):
        process_arguments(processors_tuple, new_value="xxx")
