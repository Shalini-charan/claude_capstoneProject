"""Example module for T-14 smoke test."""


def greet(name: str) -> str:
    """Return a greeting string.

    Args:
        name: The name to greet.

    Returns:
        A greeting message.
    """
    return f"Hello, {name}!"


class Calculator:
    """A simple calculator.

    Attributes:
        value: The current accumulated value.
    """

    def add(self, x: float, y: float) -> float:
        """Add two numbers and return the result."""
        return x + y
