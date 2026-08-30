import pytest
from pyspecification.validators import validate_python_vars_fn_naming_convention


@pytest.mark.parametrize(
    "value",
    [
        "IS_TRUE",
        "Is_TRue",
        "isTrue",
        "is_true",
        "is_true_is_true",
        "is_true_is_true_is_true",
        "is_true_is_true_is_true_is_true",
    ],
)
def test_valid_naming_convention(value: str) -> None:
    v = validate_python_vars_fn_naming_convention(value)
    assert isinstance(v, str)


@pytest.mark.parametrize(
    "value",
    [
        "is-true",
        "is-true-is-true",
        "1is_true",
        "*is_true",
        "is_true*",
        "is_*true",
        "is true",
        "Is True",
    ],
)
def test_invalid_naming_convention(value: str) -> None:
    with pytest.raises(ValueError):
        validate_python_vars_fn_naming_convention(value)
