#!/usr/bin/env python3
"""
Test script for the Pie Chart Creator Agent
"""

import sys
from pie_chart_agent import run_pie_chart_agent

def test_csv_data():
    """Test with CSV formatted data"""
    print("=== Testing CSV Data ===")
    csv_input = """
    Sales, 45000
    Marketing, 30000
    Development, 25000
    Support, 20000
    """
    result = run_pie_chart_agent(csv_input)
    print(f"Result: {result[:100]}..." if len(result) > 100 else f"Result: {result}")
    return result

def test_json_data():
    """Test with JSON formatted data"""
    print("\n=== Testing JSON Data ===")
    json_input = """
    [
        {"label": "Desktop", "value": 60},
        {"label": "Mobile", "value": 35},
        {"label": "Tablet", "value": 5}
    ]
    """
    result = run_pie_chart_agent(json_input)
    print(f"Result: {result[:100]}..." if len(result) > 100 else f"Result: {result}")
    return result

def test_text_data():
    """Test with text formatted data"""
    print("\n=== Testing Text Data ===")
    text_input = """
    North America: 40
    Europe: 30
    Asia: 20
    South America: 10
    """
    result = run_pie_chart_agent(text_input)
    print(f"Result: {result[:100]}..." if len(result) > 100 else f"Result: {result}")
    return result

def test_error_cases():
    """Test error handling"""
    print("\n=== Testing Error Cases ===")
    
    # Empty data
    print("1. Empty data:")
    result = run_pie_chart_agent("")
    print(f"Result: {result}")
    
    # Invalid data
    print("\n2. Invalid data:")
    result = run_pie_chart_agent("not,valid,data")
    print(f"Result: {result}")
    
    # Negative values
    print("\n3. Negative values:")
    result = run_pie_chart_agent("Positive, 10\nNegative, -5")
    print(f"Result: {result}")

if __name__ == "__main__":
    print("Testing Pie Chart Creator Agent\n")
    
    try:
        # Test different data formats
        test_csv_data()
        test_json_data()
        test_text_data()
        
        # Test error handling
        test_error_cases()
        
        print("\n✅ All tests completed!")
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        sys.exit(1)