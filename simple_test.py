"""
Simple test to isolate the parsing issue
"""

from barchart_insurance_agent_light import parse_insurance_data

def test_simple():
    data = "Auto Premiums, 2500000\nHome Premiums, 1800000"
    result = parse_insurance_data(data, "csv", "premium")
    print(f"Result: {result}")

if __name__ == "__main__":
    test_simple()