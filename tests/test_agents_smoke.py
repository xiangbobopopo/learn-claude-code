from __future__ import annotations

from pathlib import Path
import py_compile

import unittest


ROOT = Path(__file__).resolve().parents[1]
AGENTS_DIR = ROOT / "agents"
AGENT_FILES = sorted(
    path for path in AGENTS_DIR.glob("*.py") if path.name != "__init__.py"
)


class AgentSmokeTests(unittest.TestCase):
    """Smoke tests to verify agent scripts compile successfully."""
    
    def test_agent_scripts_exist(self):
        """Test that agent scripts exist."""
        self.assertTrue(len(AGENT_FILES) > 0, "expected at least one agent script")
    
    def test_s01_agent_loop_compiles(self):
        """Test s01_agent_loop.py compiles without syntax errors."""
        s01_path = AGENTS_DIR / "s01_agent_loop.py"
        self.assertTrue(s01_path.exists(), "s01_agent_loop.py should exist")
        _ = py_compile.compile(str(s01_path), doraise=True)
    
    def test_s02_tool_use_compiles(self):
        """Test s02_tool_use.py compiles without syntax errors."""
        s02_path = AGENTS_DIR / "s02_tool_use.py"
        self.assertTrue(s02_path.exists(), "s02_tool_use.py should exist")
        _ = py_compile.compile(str(s02_path), doraise=True)
    
    def test_s_full_compiles(self):
        """Test s_full.py compiles without syntax errors."""
        s_full_path = AGENTS_DIR / "s_full.py"
        self.assertTrue(s_full_path.exists(), "s_full.py should exist")
        _ = py_compile.compile(str(s_full_path), doraise=True)
    
    def test_all_agent_scripts_compile(self):
        """Test all agent scripts compile without syntax errors."""
        for agent_path in AGENT_FILES:
            with self.subTest(agent=agent_path.name):
                _ = py_compile.compile(str(agent_path), doraise=True)
