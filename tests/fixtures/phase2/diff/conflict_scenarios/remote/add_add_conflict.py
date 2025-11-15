#!/usr/bin/env python3
"""Remote version of a newly added file."""


def calculate_product(x, y):
    """Calculate product of two numbers - REMOTE implementation."""
    return x * y


def main():
    """Main function - REMOTE version."""
    result = calculate_product(5, 4)
    print(f"Remote result: {result}")


if __name__ == "__main__":
    main()
