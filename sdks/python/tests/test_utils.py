from r4u.utils import extract_call_path


def test_extract_call_path_direct_call():
    """Test that extract_call_path returns the correct path for a direct call."""
    call_path, line_number = extract_call_path()

    # Should contain this test file and function name
    assert "test_utils.py::test_extract_call_path_direct_call" in call_path
    assert isinstance(line_number, int)
    assert line_number > 0


def test_extract_call_path_nested_call():
    """Test that extract_call_path works correctly from nested function calls."""

    def inner_function():
        return extract_call_path()

    def outer_function():
        return inner_function()

    call_path, line_number = outer_function()

    # Should return the first non-library file which is this test file
    # and the function should be inner_function (where extract_call_path was actually called)
    assert "test_utils.py::inner_function" in call_path
    assert isinstance(line_number, int)
    assert line_number > 0


def test_extract_call_path_with_max_depth():
    """Test that max_depth parameter limits frame inspection."""

    def level_3():
        return extract_call_path(max_depth=1)

    def level_2():
        return level_3()

    def level_1():
        return level_2()

    call_path, line_number = level_1()

    # Should still find a valid path
    assert "::" in call_path
    assert isinstance(line_number, int)


def test_extract_call_path_return_format():
    """Test that the return format is correct."""
    call_path, line_number = extract_call_path()

    # Check format: should contain :: separator
    assert "::" in call_path

    # Should have file path before :: and function name after
    parts = call_path.split("::")
    assert len(parts) == 2

    file_path, function_name = parts
    assert file_path  # Not empty
    assert function_name  # Not empty

    # Line number should be positive integer
    assert isinstance(line_number, int)
    assert line_number > 0


def test_extract_call_path_from_class_method():
    """Test that extract_call_path works from within a class method."""

    class TestClass:
        def test_method(self):
            return extract_call_path()

    instance = TestClass()
    call_path, line_number = instance.test_method()

    # Should contain the method name
    assert "test_method" in call_path
    assert "test_utils.py" in call_path
    assert isinstance(line_number, int)
    assert line_number > 0

