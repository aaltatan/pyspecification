from pyspecification import ObjectPredicateRegistry

from tests.test_predicates.test_object.models import Employee

predicates = ObjectPredicateRegistry[Employee, bool]()


# -----------------------
# name
# -----------------------


@predicates.rule()
def name__eq(employee: Employee, value: str) -> bool:
    return employee.name == value


@predicates.rule()
def name__ieq(employee: Employee, value: str) -> bool:
    return employee.name.lower() == value.lower()


@predicates.rule()
def name__startswith(employee: Employee, value: str) -> bool:
    return employee.name.startswith(value)


@predicates.rule()
def name__istartswith(employee: Employee, value: str) -> bool:
    return employee.name.lower().startswith(value.lower())


@predicates.rule()
def name__endswith(employee: Employee, value: str) -> bool:
    return employee.name.endswith(value)


@predicates.rule()
def name__iendswith(employee: Employee, value: str) -> bool:
    return employee.name.lower().endswith(value.lower())


@predicates.rule()
def name__contains(employee: Employee, value: str) -> bool:
    return value in employee.name


@predicates.rule()
def name__icontains(employee: Employee, value: str) -> bool:
    return value.lower() in employee.name.lower()


@predicates.rule()
def name__in(employee: Employee, value: list[str]) -> bool:
    return employee.name in value


@predicates.rule()
def name__iin(employee: Employee, value: list[str]) -> bool:
    return employee.name.lower() in [v.lower() for v in value]


@predicates.rule()
def name__len_eq(employee: Employee, value: int) -> bool:
    return len(employee.name) == value


@predicates.rule()
def name__len_gt(employee: Employee, value: int) -> bool:
    return len(employee.name) > value


@predicates.rule()
def name__len_lt(employee: Employee, value: int) -> bool:
    return len(employee.name) < value


@predicates.rule()
def name__len_ge(employee: Employee, value: int) -> bool:
    return len(employee.name) >= value


@predicates.rule()
def name__len_le(employee: Employee, value: int) -> bool:
    return len(employee.name) <= value


# -----------------------
# age
# -----------------------


@predicates.rule()
def age__eq(employee: Employee, value: int) -> bool:
    return employee.age == value


@predicates.rule()
def age__gt(employee: Employee, value: int) -> bool:
    return employee.age > value


@predicates.rule()
def age__lt(employee: Employee, value: int) -> bool:
    return employee.age < value


@predicates.rule()
def age__ge(employee: Employee, value: int) -> bool:
    return employee.age >= value


@predicates.rule()
def age__le(employee: Employee, value: int) -> bool:
    return employee.age <= value


# -----------------------
# salary
# -----------------------


@predicates.rule()
def salary__eq(employee: Employee, value: float) -> bool:
    return employee.salary == value


@predicates.rule()
def salary__gt(employee: Employee, value: float) -> bool:
    return employee.salary > value


@predicates.rule()
def salary__lt(employee: Employee, value: float) -> bool:
    return employee.salary < value


@predicates.rule()
def salary__ge(employee: Employee, value: float) -> bool:
    return employee.salary >= value


@predicates.rule()
def salary__le(employee: Employee, value: float) -> bool:
    return employee.salary <= value


# -----------------------
# is active
# -----------------------


@predicates.rule()
def is_active(employee: Employee) -> bool:
    return employee.is_active


# -----------------------
# gender
# -----------------------


@predicates.rule()
def gender__is_male(employee: Employee) -> bool:
    return employee.gender == "male"


@predicates.rule()
def gender__is_female(employee: Employee) -> bool:
    return employee.gender == "female"
