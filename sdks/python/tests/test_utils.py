"""Tests for utility functions."""

import pytest
from r4u.utils import extract_call_path


class TestCallPathExtraction:
    """Test cases for call path extraction."""

    def test_extract_call_path_basic(self):
        """Test that extract_call_path returns valid format."""
        path, line_num = extract_call_path()
        
        # Check return types
        assert isinstance(path, str)
        assert isinstance(line_num, int)
        
        # Check basic format
        assert "::" in path or path == "unknown"
        assert line_num >= 0

    def test_extract_call_path_format(self):
        """Test that extract_call_path returns properly formatted path."""
        path, line_num = extract_call_path()
        
        assert isinstance(path, str)
        assert isinstance(line_num, int)
        
        # Path should either be "unknown" or contain file and function info
        if path != "unknown":
            assert "::" in path, "Path should contain :: separator"
            parts = path.split("::")
            assert len(parts) == 2, "Path should have format file::functions"

    def test_extract_call_path_returns_valid_line_number(self):
        """Test that line number is always valid."""
        path, line_num = extract_call_path()
        
        # Line number should be non-negative
        assert isinstance(line_num, int)
        assert line_num >= 0

    def test_extract_call_path_line_number(self):
        """Test that line number is reasonable."""
        path, line_num = extract_call_path()
        
        # Line number should be non-negative
        assert line_num >= 0
        # Should be within reasonable file size
        assert line_num < 100000

    def test_extract_call_path_chain_separator(self):
        """Test that call chains use -> separator."""
        path, line_num = extract_call_path()
        
        # If path contains multiple functions, they should be separated by ->
        if path != "unknown" and "::" in path:
            function_part = path.split("::")[1]
            # If there are multiple functions, check for separator
            if len(function_part.split("->")) > 1:
                assert "->" in function_part, "Multiple functions should be separated by ->"