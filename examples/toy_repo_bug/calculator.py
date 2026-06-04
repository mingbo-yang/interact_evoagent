"""A simple calculator with a division-by-zero bug."""


def add(a: float, b: float) -> float:
    return a + b


def subtract(a: float, b: float) -> float:
    return a - b


def multiply(a: float, b: float) -> float:
    return a * b


def divide(a: float, b: float) -> float:
    """Divide a by b. BUG: does not handle b=0."""
    return a / b
