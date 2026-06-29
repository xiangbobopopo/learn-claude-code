"""
Pie Chart Creator Agent

A simple agent that generates pie charts from user data.
Follows the agent-builder principles: minimal capabilities, clear context, trusted model.
"""

from pathlib import Path
import json
import csv
import io
import matplotlib.pyplot as plt
import base64

WORKDIR = Path.cwd()

# =============================================================================
# TOOL DEFINITIONS
# =============================================================================

PARSE_DATA_TOOL = {
    "name": "parse_data",
    "description": "Extract data from user input. Supports CSV, JSON, or structured text.",
    "input_schema": {
        "type": "object",
        "properties": {
            "input_data": {
                "type": "string",
                "description": "Raw data input from user"
            },
            "format": {
                "type": "string",
                "enum": ["csv", "json", "text"],
                "description": "Data format (auto-detect if not specified)"
            }
        },
        "required": ["input_data"],
    },
}

VALIDATE_DATA_TOOL = {
    "name": "validate_data",
    "description": "Check if data is suitable for pie chart generation.",
    "input_schema": {
        "type": "object",
        "properties": {
            "data": {
                "type": "array",
                "description": "Parsed data array with labels and values",
                "items": {
                    "type": "object",
                    "properties": {
                        "label": {"type": "string"},
                        "value": {"type": "number"}
                    }
                }
            }
        },
        "required": ["data"],
    },
}

GENERATE_CHART_TOOL = {
    "name": "generate_chart",
    "description": "Create pie chart visualization from validated data.",
    "input_schema": {
        "type": "object",
        "properties": {
            "data": {
                "type": "array",
                "description": "Validated data array",
                "items": {
                    "type": "object",
                    "properties": {
                        "label": {"type": "string"},
                        "value": {"type": "number"}
                    }
                }
            },
            "title": {
                "type": "string",
                "description": "Chart title (optional)"
            },
            "show_percentages": {
                "type": "boolean",
                "description": "Whether to show percentage labels (default: true)"
            }
        },
        "required": ["data"],
    },
}

# Tool list for the agent
TOOLS = [PARSE_DATA_TOOL, VALIDATE_DATA_TOOL, GENERATE_CHART_TOOL]

# =============================================================================
# TOOL IMPLEMENTATIONS
# =============================================================================

def safe_path(p: str) -> Path:
    """Security: Ensure path stays within workspace."""
    path = (WORKDIR / p).resolve()
    if not path.is_relative_to(WORKDIR):
        raise ValueError(f"Path escapes workspace: {p}")
    return path

def parse_data(input_data: str, format: str = None) -> str:
    """
    Parse input data into structured format for pie charts.
    
    Supports:
    - CSV: "Label,Value" format
    - JSON: [{"label": "A", "value": 10}, ...]
    - Text: "Label: Value" or "Label - Value" format
    """
    try:
        data = []
        
        # Auto-detect format if not specified
        if not format:
            if input_data.strip().startswith('[') or input_data.strip().startswith('{'):
                format = 'json'
            elif ',' in input_data:
                format = 'csv'
            else:
                format = 'text'
        
        if format == 'json':
            parsed = json.loads(input_data)
            if isinstance(parsed, list):
                for item in parsed:
                    data.append({"label": str(item.get("label", "")), "value": float(item.get("value", 0))})
            else:
                return "Error: JSON must be an array of objects with 'label' and 'value' fields"
                
        elif format == 'csv':
            lines = input_data.strip().split('\n')
            reader = csv.reader(lines)
            for row in reader:
                if len(row) >= 2:
                    data.append({"label": row[0].strip(), "value": float(row[1].strip())})
                    
        elif format == 'text':
            lines = input_data.strip().split('\n')
            for line in lines:
                line = line.strip()
                if ':' in line:
                    parts = line.split(':', 1)
                elif '-' in line:
                    parts = line.split('-', 1)
                else:
                    continue
                    
                if len(parts) == 2:
                    label = parts[0].strip()
                    try:
                        value = float(parts[1].strip())
                        data.append({"label": label, "value": value})
                    except ValueError:
                        continue
        
        if not data:
            return "Error: No valid data found in input"
            
        return json.dumps(data)
        
    except Exception as e:
        return f"Error parsing data: {e}"

def validate_data(data: list) -> str:
    """
    Validate that data is suitable for pie chart generation.
    
    Checks:
    - Non-empty data
    - Positive values only (or handle negatives appropriately)
    - Reasonable number of segments (not too many)
    """
    try:
        if not data:
            return "Error: Empty data array"
            
        if len(data) > 20:
            return f"Warning: Too many segments ({len(data)}). Consider grouping smaller categories."
            
        validated_data = []
        total_value = 0
        
        for item in data:
            label = item.get("label", "").strip()
            value = item.get("value", 0)
            
            if not label:
                return "Error: All items must have non-empty labels"
                
            if value < 0:
                return f"Error: Negative values not allowed for pie charts (found {value} for '{label}')"
                
            if value == 0:
                continue  # Skip zero values
                
            validated_data.append({"label": label, "value": value})
            total_value += value
        
        if not validated_data:
            return "Error: No valid positive values found"
            
        if total_value == 0:
            return "Error: Total value cannot be zero"
            
        return json.dumps(validated_data)
        
    except Exception as e:
        return f"Error validating data: {e}"

def generate_chart(data: list, title: str = None, show_percentages: bool = True) -> str:
    """
    Generate pie chart and return as base64 encoded image.
    """
    try:
        if not data:
            return "Error: No data to chart"
            
        labels = [item["label"] for item in data]
        values = [item["value"] for item in data]
        
        # Create the pie chart
        plt.figure(figsize=(8, 8))
        plt.pie(values, labels=labels if show_percentages else None, autopct='%1.1f%%' if show_percentages else None)
        
        if title:
            plt.title(title)
        else:
            plt.title("Pie Chart")
            
        # Save to bytes buffer
        buf = io.BytesIO()
        plt.savefig(buf, format='png', bbox_inches='tight', dpi=100)
        plt.close()
        
        # Encode as base64
        buf.seek(0)
        img_base64 = base64.b64encode(buf.read()).decode('utf-8')
        
        return f"data:image/png;base64,{img_base64}"
        
    except Exception as e:
        return f"Error generating chart: {e}"

# =============================================================================
# AGENT LOOP
# =============================================================================

def execute_tool(name: str, args: dict) -> str:
    """Dispatch tool call to implementation."""
    if name == "parse_data":
        return parse_data(args["input_data"], args.get("format"))
    elif name == "validate_data":
        return validate_data(args["data"])
    elif name == "generate_chart":
        return generate_chart(args["data"], args.get("title"), args.get("show_percentages", True))
    else:
        return f"Unknown tool: {name}"

def run_pie_chart_agent(user_input: str) -> str:
    """
    Main agent function. Takes user input and generates a pie chart.
    
    This is a simplified version of the agent loop for demonstration.
    In practice, you'd integrate this with your model's tool calling.
    """
    print("Pie Chart Creator Agent started...")
    print(f"User input: {user_input}")
    
    # Step 1: Parse the data
    print("\n1. Parsing data...")
    parse_result = execute_tool("parse_data", {"input_data": user_input})
    
    if parse_result.startswith("Error"):
        return f"Failed to parse data: {parse_result}"
    
    data = json.loads(parse_result)
    print(f"Parsed {len(data)} data points")
    
    # Step 2: Validate the data
    print("\n2. Validating data...")
    validate_result = execute_tool("validate_data", {"data": data})
    
    if validate_result.startswith("Error"):
        return f"Data validation failed: {validate_result}"
    elif validate_result.startswith("Warning"):
        print(f"Warning: {validate_result}")
        # Continue with validation despite warning
        validated_data = json.loads(validate_result.split('\n', 1)[1] if '\n' in validate_result else validate_result)
    else:
        validated_data = json.loads(validate_result)
    
    # Step 3: Generate the chart
    print("\n3. Generating chart...")
    chart_result = execute_tool("generate_chart", {"data": validated_data})
    
    if chart_result.startswith("Error"):
        return f"Chart generation failed: {chart_result}"
    
    print("\n✅ Pie chart generated successfully!")
    return chart_result

if __name__ == "__main__":
    # Example usage
    sample_data = """
    Apples, 45
    Bananas, 30
    Oranges, 25
    Grapes, 20
    """
    
    result = run_pie_chart_agent(sample_data)
    print(f"\nResult: {result[:100]}...")  # Truncate for display