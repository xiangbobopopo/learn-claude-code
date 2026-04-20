"""
Utility functions for MyPackage.
"""

from typing import Union


def add_numbers(a: Union[int, float], b: Union[int, float]) -> Union[int, float]:
    """
    Add two numbers together.

    Args:
        a: First number.
        b: Second number.

    Returns:
        Sum of a and b.
    """
    return a + b


def multiply_numbers(a: Union[int, float], b: Union[int, float]) -> Union[int, float]:
    """
    Multiply two numbers together.

    Args:
        a: First number.
        b: Second number.

    Returns:
        Product of a and b.
    """
    return a * b


def is_even(number: int) -> bool:
    """
    Check if a number is even.

    Args:
        number: Number to check.

    Returns:
        True if number is even, False otherwise.
    """
    return number % 2 == 0


def reverse_string(text: str) -> str:
    """
    Reverse a string.

    Args:
        text: String to reverse.

    Returns:
        Reversed string.
    """
    return text[::-1]


def count_vowels(text: str) -> int:
    """
    Count the number of vowels in a string.

    Args:
        text: String to count vowels in.

    Returns:
        Number of vowels in the string.
    """
    vowels = "aeiouAEIOU"
    return sum(1 for char in text if char in vowels)