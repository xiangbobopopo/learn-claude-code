"""
Test the fixed version
"""

from barchart_insurance_agent_fixed import run_insurance_barchart_agent

def test_fixed():
    data = """Auto Premiums, 2500000
Home Premiums, 1800000
Life Premiums, 3200000
Health Premiums, 4100000
Commercial Premiums, 2900000"""
    
    print("Testing auto-detection (no format specified):")
    result = run_insurance_barchart_agent(data, "premium")
    print(f"Success: {result.startswith('{')}")
    
    print("\nTesting explicit CSV format:")
    result2 = run_insurance_barchart_agent(data, "premium")
    print(f"Success: {result2.startswith('{')}")

if __name__ == "__main__":
    test_fixed()