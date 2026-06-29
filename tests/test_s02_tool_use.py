#!/usr/bin/env python3
"""
Unit tests for s02_tool_use.py

Tests the tool dispatch system, file operations, path safety, and tool handlers.
"""

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock


# Add agents directory to path for importing
AGENTS_DIR = Path(__file__).resolve().parents[1] / "agents"
sys.path.insert(0, str(AGENTS_DIR))


class TestS02ToolUse(unittest.TestCase):
    """Test cases for s02_tool_use.py functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create a temporary directory for testing
        self.temp_dir = tempfile.TemporaryDirectory()
        self.test_dir = Path(self.temp_dir.name)
        
        # Import the module
        import s02_tool_use
        self.s02 = s02_tool_use
        
    def tearDown(self):
        """Clean up test fixtures."""
        self.temp_dir.cleanup()
    
    def test_safe_path_valid(self):
        """Test safe_path allows valid relative paths."""
        # Change WORKDIR for this test
        original_workdir = self.s02.WORKDIR
        self.s02.WORKDIR = self.test_dir
        
        try:
            test_cases = [
                "file.txt",
                "subdir/file.txt",
                "./file.txt",
                "a/b/c/deep.txt"
            ]
            
            for path in test_cases:
                with self.subTest(path=path):
                    result = self.s02.safe_path(path)
                    self.assertTrue(result.is_relative_to(self.test_dir))
        finally:
            self.s02.WORKDIR = original_workdir
    
    def test_safe_path_escapes_workspace(self):
        """Test safe_path blocks paths that escape workspace."""
        # Change WORKDIR for this test
        original_workdir = self.s02.WORKDIR
        self.s02.WORKDIR = self.test_dir
        
        try:
            dangerous_paths = [
                "../../../etc/passwd",
                "/etc/passwd",
                "../../../../root/.ssh/id_rsa",
                "../file.txt"  # This should escape since test_dir is temp
            ]
            
            for path in dangerous_paths:
                with self.subTest(path=path):
                    with self.assertRaises(ValueError) as cm:
                        self.s02.safe_path(path)
                    self.assertIn("Path escapes workspace", str(cm.exception))
        finally:
            self.s02.WORKDIR = original_workdir
    
    def test_safe_path_escapes_workspace(self):
        """Test safe_path blocks paths that escape workspace."""
        dangerous_paths = [
            "../../../etc/passwd",
            "/etc/passwd",
            "../../../../root/.ssh/id_rsa"
        ]
        
        for path in dangerous_paths:
            with self.subTest(path=path):
                with self.assertRaises(ValueError) as cm:
                    self.s02.safe_path(path)
                self.assertIn("Path escapes workspace", str(cm.exception))
    
    def test_run_read_basic(self):
        """Test run_read reads file contents correctly."""
        # Change WORKDIR for this test
        original_workdir = self.s02.WORKDIR
        self.s02.WORKDIR = self.test_dir
        
        try:
            test_file = self.test_dir / "test.txt"
            test_content = "Hello, world!\nThis is a test file."
            test_file.write_text(test_content)
            
            result = self.s02.run_read("test.txt")
            self.assertEqual(result, test_content)
        finally:
            self.s02.WORKDIR = original_workdir
    
    def test_run_read_with_limit(self):
        """Test run_read respects line limit."""
        # Change WORKDIR for this test
        original_workdir = self.s02.WORKDIR
        self.s02.WORKDIR = self.test_dir
        
        try:
            test_file = self.test_dir / "test.txt"
            lines = [f"Line {i}" for i in range(10)]
            test_file.write_text("\n".join(lines))
            
            result = self.s02.run_read("test.txt", limit=3)
            self.assertIn("Line 0", result)
            self.assertIn("Line 1", result)
            self.assertIn("Line 2", result)
            self.assertIn("(7 more lines)", result)
            self.assertNotIn("Line 3", result)
        finally:
            self.s02.WORKDIR = original_workdir
    
    def test_run_read_nonexistent_file(self):
        """Test run_read handles nonexistent files."""
        result = self.s02.run_read("nonexistent.txt")
        self.assertIn("Error:", result)
        self.assertIn("does not exist", result)
    
    def test_run_read_output_truncation(self):
        """Test run_read truncates very long content."""
        test_file = self.test_dir / "test.txt"
        long_content = "x" * 60000  # Longer than 50000 limit
        test_file.write_text(long_content)
        
        result = self.s02.run_read("test.txt")
        self.assertEqual(len(result), 50000)
    
    def test_run_write_basic(self):
        """Test run_write creates and writes files correctly."""
        content = "Test content for writing"
        result = self.s02.run_write("output.txt", content)
        
        self.assertIn("Wrote", result)
        self.assertIn(str(len(content)), result)
        self.assertIn("output.txt", result)
        
        # Verify file was actually written
        written_file = self.test_dir / "output.txt"
        self.assertTrue(written_file.exists())
        self.assertEqual(written_file.read_text(), content)
    
    def test_run_write_creates_directories(self):
        """Test run_write creates parent directories."""
        content = "Content in subdirectory"
        result = self.s02.run_write("subdir/nested/file.txt", content)
        
        self.assertIn("Wrote", result)
        
        # Verify directory and file were created
        written_file = self.test_dir / "subdir" / "nested" / "file.txt"
        self.assertTrue(written_file.exists())
        self.assertEqual(written_file.read_text(), content)
    
    def test_run_write_invalid_path(self):
        """Test run_write handles invalid paths."""
        result = self.s02.run_write("../../../escape.txt", "content")
        self.assertIn("Error:", result)
        self.assertIn("Path escapes workspace", result)
    
    def test_run_edit_basic(self):
        """Test run_edit replaces text correctly."""
        test_file = self.test_dir / "test.txt"
        original_content = "Hello world! This is a test."
        test_file.write_text(original_content)
        
        result = self.s02.run_edit("test.txt", "world", "Python")
        
        self.assertEqual(result, "Edited test.txt")
        self.assertEqual(test_file.read_text(), "Hello Python! This is a test.")
    
    def test_run_edit_text_not_found(self):
        """Test run_edit handles text not found."""
        test_file = self.test_dir / "test.txt"
        test_file.write_text("Hello world!")
        
        result = self.s02.run_edit("test.txt", "not found", "replacement")
        
        self.assertIn("Error:", result)
        self.assertIn("Text not found", result)
    
    def test_run_edit_only_first_occurrence(self):
        """Test run_edit only replaces first occurrence."""
        test_file = self.test_dir / "test.txt"
        original_content = "test test test"
        test_file.write_text(original_content)
        
        result = self.s02.run_edit("test.txt", "test", "REPLACED")
        
        self.assertEqual(result, "Edited test.txt")
        self.assertEqual(test_file.read_text(), "REPLACED test test")
    
    def test_run_edit_invalid_path(self):
        """Test run_edit handles invalid paths."""
        result = self.s02.run_edit("../../../escape.txt", "old", "new")
        self.assertIn("Error:", result)
        self.assertIn("Path escapes workspace", result)
    
    def test_tool_handlers_exist(self):
        """Test that all expected tool handlers exist."""
        expected_handlers = ["bash", "read_file", "write_file", "edit_file"]
        
        for handler_name in expected_handlers:
            with self.subTest(handler=handler_name):
                self.assertIn(handler_name, self.s02.TOOL_HANDLERS)
                self.assertTrue(callable(self.s02.TOOL_HANDLERS[handler_name]))
    
    def test_tool_handlers_bash(self):
        """Test bash tool handler."""
        handler = self.s02.TOOL_HANDLERS["bash"]
        result = handler(command="echo test")
        self.assertEqual(result, "test")
    
    def test_tool_handlers_read_file(self):
        """Test read_file tool handler."""
        # Create test file
        test_file = self.test_dir / "test.txt"
        test_file.write_text("test content")
        
        handler = self.s02.TOOL_HANDLERS["read_file"]
        result = handler(path="test.txt")
        self.assertEqual(result, "test content")
        
        # Test with limit
        result_with_limit = handler(path="test.txt", limit=1)
        self.assertEqual(result_with_limit, "test content")  # Single line file
    
    def test_tool_handlers_write_file(self):
        """Test write_file tool handler."""
        handler = self.s02.TOOL_HANDLERS["write_file"]
        result = handler(path="output.txt", content="test content")
        
        self.assertIn("Wrote", result)
        self.assertIn("output.txt", result)
        
        # Verify file was written
        written_file = self.test_dir / "output.txt"
        self.assertTrue(written_file.exists())
        self.assertEqual(written_file.read_text(), "test content")
    
    def test_tool_handlers_edit_file(self):
        """Test edit_file tool handler."""
        # Create test file
        test_file = self.test_dir / "test.txt"
        test_file.write_text("old text here")
        
        handler = self.s02.TOOL_HANDLERS["edit_file"]
        result = handler(path="test.txt", old_text="old", new_text="new")
        
        self.assertEqual(result, "Edited test.txt")
        self.assertEqual(test_file.read_text(), "new text here")
    
    def test_tools_structure(self):
        """Test that TOOLS structure is correct."""
        expected_tools = ["bash", "read_file", "write_file", "edit_file"]
        
        self.assertEqual(len(self.s02.TOOLS), 4)
        
        for i, tool_name in enumerate(expected_tools):
            tool = self.s02.TOOLS[i]
            self.assertEqual(tool["name"], tool_name)
            self.assertIn("description", tool)
            self.assertIn("input_schema", tool)
    
    def test_bash_tool_schema(self):
        """Test bash tool schema structure."""
        bash_tool = next(t for t in self.s02.TOOLS if t["name"] == "bash")
        
        self.assertEqual(bash_tool["input_schema"]["type"], "object")
        self.assertIn("command", bash_tool["input_schema"]["properties"])
        self.assertEqual(bash_tool["input_schema"]["properties"]["command"]["type"], "string")
        self.assertIn("command", bash_tool["input_schema"]["required"])
    
    def test_read_file_tool_schema(self):
        """Test read_file tool schema structure."""
        read_tool = next(t for t in self.s02.TOOLS if t["name"] == "read_file")
        
        self.assertEqual(read_tool["input_schema"]["type"], "object")
        self.assertIn("path", read_tool["input_schema"]["properties"])
        self.assertIn("limit", read_tool["input_schema"]["properties"])
        self.assertEqual(read_tool["input_schema"]["properties"]["path"]["type"], "string")
        self.assertEqual(read_tool["input_schema"]["properties"]["limit"]["type"], "integer")
        self.assertIn("path", read_tool["input_schema"]["required"])
        self.assertNotIn("limit", read_tool["input_schema"]["required"])
    
    def test_write_file_tool_schema(self):
        """Test write_file tool schema structure."""
        write_tool = next(t for t in self.s02.TOOLS if t["name"] == "write_file")
        
        self.assertEqual(write_tool["input_schema"]["type"], "object")
        self.assertIn("path", write_tool["input_schema"]["properties"])
        self.assertIn("content", write_tool["input_schema"]["properties"])
        self.assertEqual(write_tool["input_schema"]["properties"]["path"]["type"], "string")
        self.assertEqual(write_tool["input_schema"]["properties"]["content"]["type"], "string")
        self.assertCountEqual(write_tool["input_schema"]["required"], ["path", "content"])
    
    def test_edit_file_tool_schema(self):
        """Test edit_file tool schema structure."""
        edit_tool = next(t for t in self.s02.TOOLS if t["name"] == "edit_file")
        
        self.assertEqual(edit_tool["input_schema"]["type"], "object")
        self.assertIn("path", edit_tool["input_schema"]["properties"])
        self.assertIn("old_text", edit_tool["input_schema"]["properties"])
        self.assertIn("new_text", edit_tool["input_schema"]["properties"])
        self.assertEqual(edit_tool["input_schema"]["properties"]["path"]["type"], "string")
        self.assertEqual(edit_tool["input_schema"]["properties"]["old_text"]["type"], "string")
        self.assertEqual(edit_tool["input_schema"]["properties"]["new_text"]["type"], "string")
        self.assertCountEqual(edit_tool["input_schema"]["required"], ["path", "old_text", "new_text"])
    
    @patch('s02_tool_use.client.messages.create')
    def test_agent_loop_unknown_tool(self, mock_create):
        """Test agent loop handles unknown tools gracefully."""
        # Mock response with unknown tool
        mock_response = Mock()
        mock_response.stop_reason = "tool_use"
        mock_tool_use = Mock()
        mock_tool_use.type = "tool_use"
        mock_tool_use.name = "unknown_tool"
        mock_tool_use.id = "test-id"
        mock_tool_use.input = {"param": "value"}
        mock_response.content = [mock_tool_use]
        
        # Second response to end the loop
        mock_response2 = Mock()
        mock_response2.stop_reason = "end_turn"
        mock_response2.content = []
        
        mock_create.side_effect = [mock_response, mock_response2]
        
        messages = [{"role": "user", "content": "Use unknown tool"}]
        
        self.s02.agent_loop(messages)
        
        # Check that unknown tool error was handled
        tool_result = messages[2]["content"][0]
        self.assertEqual(tool_result["type"], "tool_result")
        self.assertIn("Unknown tool: unknown_tool", tool_result["content"])


if __name__ == '__main__':
    unittest.main()