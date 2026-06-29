#!/usr/bin/env python3
"""
A simple calculator program that supports basic arithmetic operations.
"""

import sys

class Calculator:
    """A basic calculator class with arithmetic operations."""
    
    def add(self, a, b):
        """Add two numbers."""
        return a + b
    
    def subtract(self, a, b):
        """Subtract two numbers."""
        return a - b
    
    def multiply(self, a, b):
        """Multiply two numbers."""
        return a * b
    
    def divide(self, a, b):
        """Divide two numbers."""
        if b == 0:
            raise ValueError("Cannot divide by zero!")
        return a / b
    
    def power(self, a, b):
        """Calculate a raised to the power of b."""
        return a ** b
    
    def modulo(self, a, b):
        """Calculate the remainder of a divided by b."""
        if b == 0:
            raise ValueError("Cannot perform modulo by zero!")
        return a % b

def get_number(prompt):
    """Get a number from user input with error handling."""
    while True:
        try:
            return float(input(prompt))
        except ValueError:
            print("Please enter a valid number.")

def get_operation():
    """Get operation choice from user."""
    operations = {
        '1': ('Addition', '+'),
        '2': ('Subtraction', '-'),
        '3': ('Multiplication', '*'),
        '4': ('Division', '/'),
        '5': ('Power', '^'),
        '6': ('Modulo', '%')
    }
    
    print("\nSelect operation:")
    for key, (name, symbol) in operations.items():
        print(f"{key}. {name} ({symbol})")
    
    while True:
        choice = input("\nEnter choice (1-6): ").strip()
        if choice in operations:
            return choice, operations[choice]
        print("Invalid choice. Please enter 1-6.")

def perform_calculation(calculator, operation, num1, num2):
    """Perform the calculation based on the operation."""
    try:
        if operation == '1':
            result = calculator.add(num1, num2)
        elif operation == '2':
            result = calculator.subtract(num1, num2)
        elif operation == '3':
            result = calculator.multiply(num1, num2)
        elif operation == '4':
            result = calculator.divide(num1, num2)
        elif operation == '5':
            result = calculator.power(num1, num2)
        elif operation == '6':
            result = calculator.modulo(num1, num2)
        
        return result
    except ValueError as e:
        print(f"Error: {e}")
        return None

def main():
    """Main function to run the calculator."""
    calculator = Calculator()
    
    print("Welcome to the Calculator!")
    print("=" * 30)
    
    while True:
        # Get operation choice
        operation_choice, (operation_name, operation_symbol) = get_operation()
        
        # Get numbers
        num1 = get_number("Enter first number: ")
        num2 = get_number("Enter second number: ")
        
        # Perform calculation
        result = perform_calculation(calculator, operation_choice, num1, num2)
        
        # Display result
        if result is not None:
            print(f"\nResult: {num1} {operation_symbol} {num2} = {result}")
        
        # Ask if user wants to continue
        while True:
            continue_choice = input("\nDo you want to perform another calculation? (y/n): ").strip().lower()
            if continue_choice in ['y', 'yes', 'n', 'no']:
                break
            print("Please enter 'y' for yes or 'n' for no.")
        
        if continue_choice in ['n', 'no']:
            print("Thank you for using the calculator. Goodbye!")
            break

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nCalculator terminated by user. Goodbye!")
        sys.exit(0)