"""
Unit tests for utils.py
"""

import unittest
from mypackage.utils import (
    add_numbers,
    multiply_numbers,
    is_even,
    reverse_string,
    count_vowels
)


class TestUtils(unittest.TestCase):
    """Test cases for utility functions."""
    
    def test_add_numbers(self):
        """Test add_numbers function."""
        self.assertEqual(add_numbers(2, 3), 5)
        self.assertEqual(add_numbers(-1, 1), 0)
        self.assertEqual(add_numbers(0, 0), 0)
        self.assertEqual(add_numbers(2.5, 3.5), 6.0)
    
    def test_multiply_numbers(self):
        """Test multiply_numbers function."""
        self.assertEqual(multiply_numbers(2, 3), 6)
        self.assertEqual(multiply_numbers(-1, 5), -5)
        self.assertEqual(multiply_numbers(0, 10), 0)
        self.assertEqual(multiply_numbers(2.5, 4), 10.0)
    
    def test_is_even(self):
        """Test is_even function."""
        self.assertTrue(is_even(2))
        self.assertTrue(is_even(0))
        self.assertTrue(is_even(-4))
        self.assertFalse(is_even(1))
        self.assertFalse(is_even(-3))
        self.assertFalse(is_even(7))
    
    def test_reverse_string(self):
        """Test reverse_string function."""
        self.assertEqual(reverse_string("hello"), "olleh")
        self.assertEqual(reverse_string("Python"), "nohtyP")
        self.assertEqual(reverse_string(""), "")
        self.assertEqual(reverse_string("a"), "a")
        self.assertEqual(reverse_string("12345"), "54321")
    
    def test_count_vowels(self):
        """Test count_vowels function."""
        self.assertEqual(count_vowels("hello"), 2)
        self.assertEqual(count_vowels("Python"), 1)
        self.assertEqual(count_vowels("AEIOU"), 5)
        self.assertEqual(count_vowels("xyz"), 0)
        self.assertEqual(count_vowels(""), 0)
        self.assertEqual(count_vowels("Hello World"), 3)


if __name__ == '__main__':
    unittest.main()