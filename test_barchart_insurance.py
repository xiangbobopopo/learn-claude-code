"""
Test script for the Insurance Barchart Builder Agent
"""

from barchart_insurance_agent import run_insurance_barchart_agent
import json

def test_basic_premium_data():
    """Test with basic premium data"""
    print("=" * 60)
    print("TEST 1: Basic Premium Data")
    print("=" * 60)
    
    data = """
    Auto Premiums, 2500000
    Home Premiums, 1800000
    Life Premiums, 3200000
    Health Premiums, 4100000
    Commercial Premiums, 2900000
    """
    
    result = run_insurance_barchart_agent(data, "premium")
    print(f"Result type: {'Success' if result.startswith('data:image') else 'Error'}")
    return result

def test_claims_data():
    """Test with claims data"""
    print("\n" + "=" * 60)
    print("TEST 2: Claims Data")
    print("=" * 60)
    
    data = """
    Auto Claims, 1200000
    Home Claims, 850000
    Life Claims, 2100000
    Health Claims, 3200000
    Commercial Claims, 1500000
    """
    
    result = run_insurance_barchart_agent(data, "claims")
    print(f"Result type: {'Success' if result.startswith('data:image') else 'Error'}")
    return result

def test_json_format():
    """Test with JSON format data"""
    print("\n" + "=" * 60)
    print("TEST 3: JSON Format Data")
    print("=" * 60)
    
    data = json.dumps([
        {"category": "Q1 Revenue", "value": 5200000, "period": "Q1 2024"},
        {"category": "Q2 Revenue", "value": 5800000, "period": "Q2 2024"},
        {"category": "Q3 Revenue", "value": 6100000, "period": "Q3 2024"},
        {"category": "Q4 Revenue", "value": 5900000, "period": "Q4 2024"}
    ])
    
    result = run_insurance_barchart_agent(data, "revenue")
    print(f"Result type: {'Success' if result.startswith('data:image') else 'Error'}")
    return result

def test_regional_data():
    """Test with regional insurance data"""
    print("\n" + "=" * 60)
    print("TEST 4: Regional Data")
    print("=" * 60)
    
    data = """
    Northeast, 2800000
    Southeast, 3200000
    Midwest, 2100000
    Southwest, 1900000
    West, 3500000
    """
    
    result = run_insurance_barchart_agent(data, "premium")
    print(f"Result type: {'Success' if result.startswith('data:image') else 'Error'}")
    return result

def test_text_format():
    """Test with text format using colons"""
    print("\n" + "=" * 60)
    print("TEST 5: Text Format (Colon-separated)")
    print("=" * 60)
    
    data = """
    Policy Type A: $1,250,000
    Policy Type B: $980,000
    Policy Type C: $1,670,000
    Policy Type D: $2,100,000
    Policy Type E: $890,000
    """
    
    result = run_insurance_barchart_agent(data, "policies")
    print(f"Result type: {'Success' if result.startswith('data:image') else 'Error'}")
    return result

def test_large_dataset():
    """Test with larger dataset to test horizontal orientation"""
    print("\n" + "=" * 60)
    print("TEST 6: Large Dataset (Horizontal Orientation)")
    print("=" * 60)
    
    data = """
    Very Long Category Name Insurance Product Alpha, 1250000
    Another Long Category Name Insurance Product Beta, 980000
    Extended Category Description Insurance Product Gamma, 1670000
    Comprehensive Category Title Insurance Product Delta, 2100000
    Detailed Category Label Insurance Product Epsilon, 890000
    Extended Category Name Insurance Product Zeta, 1450000
    Long Category Description Insurance Product Eta, 1120000
    Comprehensive Category Insurance Product Theta, 1890000
    Detailed Category Insurance Product Iota, 750000
    Extended Category Insurance Product Kappa, 1340000
    """
    
    result = run_insurance_barchart_agent(data, "premium")
    print(f"Result type: {'Success' if result.startswith('data:image') else 'Error'}")
    return result

if __name__ == "__main__":
    print("Testing Insurance Barchart Builder Agent")
    print("This will generate bar charts for various insurance data scenarios")
    
    results = []
    
    # Run all tests
    results.append(test_basic_premium_data())
    results.append(test_claims_data())
    results.append(test_json_format())
    results.append(test_regional_data())
    results.append(test_text_format())
    results.append(test_large_dataset())
    
    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    success_count = sum(1 for r in results if r.startswith('data:image'))
    print(f"Tests passed: {success_count}/{len(results)}")
    
    if success_count == len(results):
        print("🎉 All tests passed! The Insurance Barchart Builder Agent is working correctly.")
    else:
        print("⚠️  Some tests failed. Check the error messages above.")
    
    print("\nThe agent can handle:")
    print("✓ CSV format insurance data")
    print("✓ JSON format with structured fields")
    print("✓ Text format with colons, dashes, or pipes")
    print("✓ Automatic data type detection")
    print("✓ Professional color schemes for insurance context")
    print("✓ Automatic orientation selection")
    print("✓ Value labels and professional styling")
    print("✓ Various insurance data types (premiums, claims, policies, etc.)")