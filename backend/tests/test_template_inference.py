"""Tests for template inference with double-brace placeholders."""

from app.services.template_inference import (
    TemplateInferrer,
    infer_template_from_strings,
)


class TestTemplateInferrer:
    """Test the template inference algorithm."""

    def test_single_string_returns_itself(self):
        """Test that a single string is returned as-is."""
        inferrer = TemplateInferrer()
        result = inferrer.infer_template(["Hello, world!"])
        assert result == "Hello, world!"

    def test_empty_list_returns_empty_string(self):
        """Test that an empty list returns an empty string."""
        inferrer = TemplateInferrer()
        result = inferrer.infer_template([])
        assert result == ""

    def test_simple_variable_inference(self):
        """Test inferring a simple variable."""
        inferrer = TemplateInferrer(min_consecutive_words=1)
        strings = [
            "Hello, Alice!",
            "Hello, Bob!",
            "Hello, Charlie!",
        ]
        result = inferrer.infer_template(strings)
        assert result == "Hello, {{var_0}}"

    def test_multiple_variables_inference(self):
        """Test inferring multiple variables."""
        inferrer = TemplateInferrer(min_consecutive_words=1)
        strings = [
            "User Alice has email alice@example.com",
            "User Bob has email bob@example.com",
            "User Charlie has email charlie@example.com",
        ]
        result = inferrer.infer_template(strings)
        assert "{{var_0}}" in result
        assert "{{var_1}}" in result
        assert "User" in result
        assert "has email" in result

    def test_variable_at_beginning(self):
        """Test variable at the beginning of the string."""
        inferrer = TemplateInferrer()
        strings = [
            "Alice is a developer",
            "Bob is a developer",
            "Charlie is a developer",
        ]
        result = inferrer.infer_template(strings)
        assert result == "{{var_0}} is a developer"

    def test_variable_at_end(self):
        """Test variable at the end of the string."""
        inferrer = TemplateInferrer()
        strings = [
            "The user is Alice",
            "The user is Bob",
            "The user is Charlie",
        ]
        result = inferrer.infer_template(strings)
        assert result == "The user is {{var_0}}"

    def test_multiple_variables_adjacent(self):
        """Test multiple adjacent variables."""
        inferrer = TemplateInferrer()
        strings = [
            "AliceBob",
            "CharlieEve",
            "DavidFrank",
        ]
        result = inferrer.infer_template(strings)
        # Should have at least one variable
        assert "{{var_" in result

    def test_numbers_as_variables(self):
        """Test that numbers are treated as variables."""
        inferrer = TemplateInferrer(min_consecutive_words=1)
        strings = [
            "User ID: 123",
            "User ID: 456",
            "User ID: 789",
        ]
        result = inferrer.infer_template(strings)
        assert result == "User ID: {{var_0}}"

    def test_special_characters_in_common_parts(self):
        """Test that special characters in common parts are preserved."""
        inferrer = TemplateInferrer(min_consecutive_words=1)
        strings = [
            "Email: alice@example.com (active)",
            "Email: bob@example.com (active)",
            "Email: charlie@example.com (active)",
        ]
        result = inferrer.infer_template(strings)
        assert "Email:" in result
        assert "(active)" in result
        assert "{{var_0}}" in result

    def test_multiline_strings(self):
        """Test inference with multiline strings."""
        inferrer = TemplateInferrer(min_consecutive_words=1)
        strings = [
            "Hello Alice\nWelcome to the system",
            "Hello Bob\nWelcome to the system",
            "Hello Charlie\nWelcome to the system",
        ]
        result = inferrer.infer_template(strings)
        assert "Hello {{var_0}}" in result
        assert "Welcome to the system" in result

    def test_custom_placeholder_format(self):
        """Test using a custom placeholder format."""
        inferrer = TemplateInferrer(
            placeholder_format="{{{index}}}",
            min_consecutive_words=1,
        )
        strings = [
            "Hello, Alice!",
            "Hello, Bob!",
        ]
        result = inferrer.infer_template(strings)
        assert result == "Hello, {0}"

    def test_double_brace_default_format(self):
        """Test that default format uses double braces."""
        inferrer = TemplateInferrer(min_consecutive_words=1)
        strings = [
            "Greet user Alice",
            "Greet user Bob",
        ]
        result = inferrer.infer_template(strings)
        # Should use double braces by default
        assert "{{" in result
        assert "}}" in result
        assert result == "Greet user {{var_0}}"

    def test_identical_strings_no_variables(self):
        """Test that identical strings have no variables."""
        inferrer = TemplateInferrer()
        strings = [
            "You are a helpful assistant.",
            "You are a helpful assistant.",
            "You are a helpful assistant.",
        ]
        result = inferrer.infer_template(strings)
        assert result == "You are a helpful assistant."
        assert "{{var_" not in result

    def test_weather_query_pattern(self):
        """Test real-world weather query pattern."""
        inferrer = TemplateInferrer()
        strings = [
            "Get weather for NYC",
            "Get weather for LA",
            "Get weather for Chicago",
        ]
        result = inferrer.infer_template(strings)
        assert result == "Get weather for {{var_0}}"

    def test_greeting_pattern(self):
        """Test real-world greeting pattern."""
        inferrer = TemplateInferrer()
        strings = [
            "Say hello to Alice",
            "Say hello to Bob",
            "Say hello to Charlie",
        ]
        result = inferrer.infer_template(strings)
        assert result == "Say hello to {{var_0}}"

    def test_complex_prompt_pattern(self):
        """Test complex prompt with multiple variables."""
        inferrer = TemplateInferrer()
        strings = [
            "You are a personal assistant for user Alice. Help them with task 123.",
            "You are a personal assistant for user Bob. Help them with task 456.",
            "You are a personal assistant for user Charlie. Help them with task 789.",
        ]
        result = inferrer.infer_template(strings)
        assert "You are a personal assistant for user {{var_0}}" in result
        assert "Help them with task {{var_1}}" in result


class TestInferTemplateFromStringsFunction:
    """Test the convenience function."""

    def test_convenience_function_works(self):
        """Test that the convenience function works correctly."""
        strings = [
            "Hello, Alice!",
            "Hello, Bob!",
        ]
        result = infer_template_from_strings(strings, min_consecutive_words=1)
        assert result == "Hello, {{var_0}}"

    def test_convenience_function_with_custom_format(self):
        """Test convenience function with custom placeholder format."""
        strings = [
            "Hello, Alice!",
            "Hello, Bob!",
        ]
        result = infer_template_from_strings(
            strings,
            placeholder_format="<{index}>",
            min_consecutive_words=1,
        )
        assert result == "Hello, <0>"

    def test_convenience_function_default_double_braces(self):
        """Test that convenience function uses double braces by default."""
        strings = [
            "User Alice logged in",
            "User Bob logged in",
        ]
        result = infer_template_from_strings(strings, min_consecutive_words=1)
        assert "{{" in result
        assert "}}" in result
        assert result == "User {{var_0}} logged in"

    def test_task_grouping_example(self):
        """Test the example from task grouping documentation."""
        strings = [
            "Say hello to Alice",
            "Say hello to Bob",
            "Say hello to Charlie",
        ]
        result = infer_template_from_strings(strings)
        # Should match the documented example
        assert result == "Say hello to {{var_0}}"

    def test_weather_example(self):
        """Test the weather query example from documentation."""
        strings = [
            "Get weather for NYC",
            "Get weather for LA",
            "Get weather for Chicago",
        ]
        result = infer_template_from_strings(strings)
        # Should match the documented example
        assert result == "Get weather for {{var_0}}"

    def test_personal_assistant_example(self):
        """Test the personal assistant example from README."""
        strings = [
            "You are a personal assistant for user Alice",
            "You are a personal assistant for user Bob",
            "You are a personal assistant for user Charlie",
        ]
        result = infer_template_from_strings(strings)
        # Should match the documented format
        assert result == "You are a personal assistant for user {{var_0}}"
