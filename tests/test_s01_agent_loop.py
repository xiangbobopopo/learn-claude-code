#!/usr/bin/env python3
"""
Unit tests for s01_agent_loop.py

Tests the core agent loop functionality, bash command execution, and safety mechanisms.
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


class TestS01AgentLoop(unittest.TestCase):
    """Test cases for s01_agent_loop.py functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Mock environment variables
        self.env_patcher = patch.dict(os.environ, {
            'MODEL_ID': 'test-model',
            'ANTHROPIC_API_KEY': 'test-key'
        })
        self.env_patcher.start()
        
        # Import the module after setting up environment
        import s01_agent_loop
        self.s01 = s01_agent_loop
        
    def tearDown(self):
        """Clean up test fixtures."""
        self.env_patcher.stop()
    
    def test_run_bash_basic_command(self):
        """Test run_bash executes basic commands safely."""
        result = self.s01.run_bash("echo 'hello world'")
        self.assertEqual(result, "hello world")
    
    def test_run_bash_dangerous_command_blocked(self):
        """Test run_bash blocks dangerous commands."""
        dangerous_commands = [
            "rm -rf /",
            "sudo ls",
            "shutdown now",
            "reboot",
            "echo test > /dev/null"
        ]
        
        for cmd in dangerous_commands:
            with self.subTest(command=cmd):
                result = self.s01.run_bash(cmd)
                self.assertEqual(result, "Error: Dangerous command blocked")
    
    def test_run_bash_timeout_handling(self):
        """Test run_bash handles timeouts properly."""
        with patch('subprocess.run') as mock_run:
            mock_run.side_effect = subprocess.TimeoutExpired("sleep", 120)
            result = self.s01.run_bash("sleep 200")
            self.assertEqual(result, "Error: Timeout (120s)")
    
    def test_run_bash_file_not_found(self):
        """Test run_bash handles file not found errors."""
        with patch('subprocess.run') as mock_run:
            mock_run.side_effect = FileNotFoundError("Command not found")
            result = self.s01.run_bash("nonexistent_command")
            self.assertEqual(result, "Error: Command not found")
    
    def test_run_bash_output_truncation(self):
        """Test run_bash truncates very long output."""
        # Create a command that would produce very long output
        long_output = "x" * 60000  # Longer than 50000 limit
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(
                stdout=long_output,
                stderr="",
                returncode=0
            )
            result = self.s01.run_bash("echo 'long output'")
            self.assertEqual(len(result), 50000)
            self.assertTrue(result.startswith("x"))
    
    def test_run_bash_no_output(self):
        """Test run_bash handles commands with no output."""
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(
                stdout="",
                stderr="",
                returncode=0
            )
            result = self.s01.run_bash("true")  # Command that produces no output
            self.assertEqual(result, "(no output)")
    
    def test_run_bash_stderr_included(self):
        """Test run_bash includes stderr in output."""
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(
                stdout="stdout content",
                stderr="stderr content",
                returncode=0
            )
            result = self.s01.run_bash("test command")
            self.assertIn("stdout content", result)
            self.assertIn("stderr content", result)
    
    def test_dangerous_command_detection(self):
        """Test that dangerous command patterns are properly detected."""
        # Test partial matches
        dangerous_patterns = [
            "sudo apt update",  # Contains sudo
            "rm -rf /tmp/test",  # Contains rm -rf /
            "echo test > /dev/sda",  # Contains > /
            "systemctl shutdown",  # Contains shutdown
            "sudo reboot now",  # Contains both sudo and reboot
        ]
        
        for cmd in dangerous_patterns:
            with self.subTest(command=cmd):
                result = self.s01.run_bash(cmd)
                self.assertEqual(result, "Error: Dangerous command blocked")
    
    @patch('s01_agent_loop.client.messages.create')
    def test_agent_loop_basic_flow(self, mock_create):
        """Test the basic agent loop flow without tool calls."""
        # Mock a response that doesn't use tools (stop_reason != "tool_use")
        mock_response = Mock()
        mock_response.stop_reason = "end_turn"
        mock_response.content = [Mock(text="Hello, I'm ready to help!")]
        mock_create.return_value = mock_response
        
        messages = [{"role": "user", "content": "Hello"}]
        
        # This should return without error and not loop infinitely
        self.s01.agent_loop(messages)
        
        # Verify the assistant response was added to messages
        self.assertEqual(len(messages), 2)
        self.assertEqual(messages[1]["role"], "assistant")
    
    @patch('s01_agent_loop.client.messages.create')
    def test_agent_loop_with_tool_use(self, mock_create):
        """Test agent loop with tool usage."""
        # First response: tool use
        mock_response1 = Mock()
        mock_response1.stop_reason = "tool_use"
        mock_tool_use = Mock()
        mock_tool_use.type = "tool_use"
        mock_tool_use.id = "test-tool-id"
        mock_tool_use.input = {"command": "echo test"}
        mock_response1.content = [mock_tool_use]
        
        # Second response: end turn
        mock_response2 = Mock()
        mock_response2.stop_reason = "end_turn"
        mock_response2.content = [Mock(text="Task completed")]
        
        mock_create.side_effect = [mock_response1, mock_response2]
        
        messages = [{"role": "user", "content": "Run echo test"}]
        
        with patch('s01_agent_loop.run_bash') as mock_run_bash:
            mock_run_bash.return_value = "test output"
            self.s01.agent_loop(messages)
        
        # Verify bash was called
        mock_run_bash.assert_called_once_with("echo test")
        
        # Verify messages structure
        self.assertEqual(len(messages), 4)  # user -> assistant -> user(tool_result) -> assistant
        
        # Check tool result structure
        tool_result = messages[2]["content"][0]
        self.assertEqual(tool_result["type"], "tool_result")
        self.assertEqual(tool_result["tool_use_id"], "test-tool-id")
        self.assertEqual(tool_result["content"], "test output")
    
    def test_system_prompt_contains_cwd(self):
        """Test that SYSTEM prompt includes current working directory."""
        expected_cwd = os.getcwd()
        self.assertIn(expected_cwd, self.s01.SYSTEM)
    
    def test_tools_structure(self):
        """Test that TOOLS structure is correct."""
        self.assertEqual(len(self.s01.TOOLS), 1)
        bash_tool = self.s01.TOOLS[0]
        
        self.assertEqual(bash_tool["name"], "bash")
        self.assertEqual(bash_tool["description"], "Run a shell command.")
        self.assertIn("input_schema", bash_tool)
        self.assertIn("properties", bash_tool["input_schema"])
        self.assertIn("command", bash_tool["input_schema"]["properties"])
        self.assertIn("required", bash_tool["input_schema"])
        self.assertIn("command", bash_tool["input_schema"]["required"])


if __name__ == '__main__':
    unittest.main()