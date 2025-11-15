#!/usr/bin/env python3
"""Updated version with improved documentation."""


def hello(name="World"):
    """Say hello to someone.

    Args:
        name: Name of the person to greet (default: "World")
    """
    print(f"Hello, {name}!")


def goodbye(name="World"):
    """Say goodbye to someone.

    Args:
        name: Name of the person (default: "World")
    """
    print(f"Goodbye, {name}!")


if __name__ == "__main__":
    hello()
    goodbye()
