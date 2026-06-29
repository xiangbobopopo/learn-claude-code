"""
Test with fresh Python process
"""

# Copy the function directly here to avoid any caching issues
def parse_insurance_data(input_data: str, format: str = None, data_type: str = None):
    print(f"DEBUG: parse_insurance_data called with format={format}, data_type={data_type}")
    
    try:
        data = []
        
        # Auto-detect format if not specified
        if format is None:
            print(f"DEBUG: Auto-detecting format for: {repr(input_data.strip())}")
            input_clean = input_data.strip()
            if input_clean.startswith('[') or input_clean.startswith('{'):
                format = 'json'
                print("DEBUG: Detected JSON")
            elif '\t' in input_clean:
                format = 'table'
                print("DEBUG: Detected TABLE")
            elif ',' in input_clean and '\n' in input_clean:
                format = 'csv'
                print("DEBUG: Detected CSV (multi-line)")
            elif ',' in input_clean:
                format = 'csv'
                print("DEBUG: Detected CSV (single-line)")
            else:
                format = 'text'
                print("DEBUG: Detected TEXT")
        print(f"DEBUG: Using format: {format}")
        
        if format == 'csv':
            print("DEBUG: Processing as CSV")
            lines = input_data.strip().split('\n')
            print(f"DEBUG: Lines: {lines}")
            import csv
            reader = csv.reader(lines)
            all_rows = list(reader)
            print(f"DEBUG: All rows: {all_rows}")
            
            if not all_rows:
                return "Error: No data found in CSV input"
                
            headers = all_rows[0]
            print(f"DEBUG: Headers: {headers}")
            
            # No meaningful headers, treat all rows as data
            for row in all_rows:
                if len(row) >= 2:
                    try:
                        category = row[0].strip()
                        value = float(row[1].strip())
                        data.append({
                            "category": category,
                            "value": value,
                            "period": "",
                            "region": "",
                            "data_type": data_type
                        })
                        print(f"DEBUG: Added data: {category}, {value}")
                    except ValueError as e:
                        print(f"DEBUG: ValueError: {e}")
                        continue
        
        if not data:
            return "Error: No valid insurance data found in input"
            
        import json
        return json.dumps(data)
        
    except Exception as e:
        return f"Error parsing insurance data: {e}"

def test_debug():
    data = """Auto Premiums, 2500000
Home Premiums, 1800000
Life Premiums, 3200000"""
    
    print("Testing with format=None:")
    result = parse_insurance_data(data, None, "premium")
    print(f"Result: {result}")

if __name__ == "__main__":
    test_debug()