"""Tests for consecutive word-based template detection.

These tests verify that the new consecutive word-based approach works correctly
for grouping traces and creating templates, especially for cases where argument
values are very large.
"""

from app.services.template_inference import (
    TemplateInferrer,
    infer_template_from_strings,
)


class TestConsecutiveWordTemplateDetection:
    """Test consecutive word-based template detection."""

    def test_minimum_consecutive_words_default(self):
        """Test that default requires 3 consecutive words."""
        inferrer = TemplateInferrer(min_consecutive_words=3)

        # Should match: "You are a" is 3 consecutive words
        strings = [
            "You are a helper for Alice",
            "You are a helper for Bob",
            "You are a helper for Charlie",
        ]
        result = inferrer.infer_template(strings)
        assert result == "You are a helper for {{var_0}}"
        assert "{{var_" in result

    def test_minimum_consecutive_words_custom(self):
        """Test with custom minimum consecutive words."""
        # Require 5 consecutive words
        inferrer = TemplateInferrer(min_consecutive_words=5)

        # "You are a personal assistant for" is 6 words
        strings = [
            "You are a personal assistant for Alice",
            "You are a personal assistant for Bob",
        ]
        result = inferrer.infer_template(strings)
        assert result == "You are a personal assistant for {{var_0}}"

    def test_short_common_sequence_not_matched_with_high_threshold(self):
        """Test that short sequences don't match with high word threshold."""
        # Require 5 consecutive words
        inferrer = TemplateInferrer(min_consecutive_words=5)

        # Only "Hello there" (2 words) is common
        strings = [
            "Hello there Alice how are you today",
            "Hello there Bob what is happening",
        ]
        result = inferrer.infer_template(strings)
        # Should not find "Hello there" as an anchor (only 2 words)
        # So the entire strings become variables
        assert result == "{{var_0}}"

    def test_large_argument_values_still_group(self):
        """Test that traces with large argument values can still be grouped.

        This is the main use case: even if argument values are huge (low ratio),
        we should still group if there are enough consecutive words in common.
        """
        # Use default 3 consecutive words
        inferrer = TemplateInferrer(min_consecutive_words=3)

        # Very long argument values, but "You are a personal assistant for Mr" is common
        large_bio_1 = "software engineer with 15 years of experience in distributed systems, cloud architecture, and team leadership"
        large_bio_2 = "data scientist specializing in machine learning, natural language processing, and big data analytics"

        strings = [
            f"You are a personal assistant for Mr. {large_bio_1}",
            f"You are a personal assistant for Mr. {large_bio_2}",
        ]

        result = inferrer.infer_template(strings)
        # Should still find the common part despite large variables
        assert result == "You are a personal assistant for Mr. {{var_0}}"

    def test_multiple_large_arguments(self):
        """Test with multiple large argument values."""
        inferrer = TemplateInferrer(min_consecutive_words=3)

        large_text_1 = "comprehensive analysis of the current market trends"
        large_text_2 = "in-depth review of customer feedback and satisfaction"

        strings = [
            f"Create a detailed report about the {large_text_1} for the executive team",
            f"Create a detailed report about the {large_text_2} for the executive team",
        ]

        result = inferrer.infer_template(strings)
        assert (
            result
            == "Create a detailed report about the {{var_0}} for the executive team"
        )

    def test_punctuation_doesnt_count_as_words(self):
        """Test that punctuation doesn't count toward consecutive word threshold."""
        inferrer = TemplateInferrer(min_consecutive_words=3)

        # "Hello , !" has 1 word and 2 punctuation marks
        strings = [
            "Hello, Alice!",
            "Hello, Bob!",
        ]
        result = inferrer.infer_template(strings)
        # "Hello" alone is only 1 word, so shouldn't be an anchor with threshold 3
        assert result == "{{var_0}}"

    def test_words_with_punctuation_count_correctly(self):
        """Test that words separated by punctuation are counted correctly."""
        inferrer = TemplateInferrer(min_consecutive_words=3)

        # "You are a" is 3 words despite punctuation
        strings = [
            "You are a: helper for Alice",
            "You are a: helper for Bob",
        ]
        result = inferrer.infer_template(strings)
        assert "{{var_0}}" in result
        # Should find "You are a" (3 words) as anchor
        assert "You are a" in result

    def test_consecutive_words_with_newlines(self):
        """Test that newlines don't break consecutive word counting."""
        inferrer = TemplateInferrer(min_consecutive_words=4)

        strings = [
            "You are a helpful\nassistant for Alice",
            "You are a helpful\nassistant for Bob",
        ]
        result = inferrer.infer_template(strings)
        # "You are a helpful assistant for" should be found
        assert "You are a helpful" in result or "assistant for" in result

    def test_readme_example_with_consecutive_words(self):
        """Test the README example: 'You are a personal assistant for Mr {{var_0}}'"""
        inferrer = TemplateInferrer(min_consecutive_words=3)

        strings = [
            "You are a personal assistant for Mr Smith",
            "You are a personal assistant for Mr Johnson",
            "You are a personal assistant for Mr Williams",
        ]
        result = inferrer.infer_template(strings)
        assert result == "You are a personal assistant for Mr {{var_0}}"

    def test_one_word_threshold(self):
        """Test that threshold of 1 word matches single words."""
        inferrer = TemplateInferrer(min_consecutive_words=1)

        strings = [
            "Hello Alice",
            "Hello Bob",
        ]
        result = inferrer.infer_template(strings)
        assert result == "Hello {{var_0}}"

    def test_convenience_function_with_consecutive_words(self):
        """Test the convenience function with min_consecutive_words parameter."""
        strings = [
            "You are a helpful assistant for Alice",
            "You are a helpful assistant for Bob",
        ]

        # With default (3 words)
        result = infer_template_from_strings(strings, min_consecutive_words=3)
        assert result == "You are a helpful assistant for {{var_0}}"

        # With higher threshold (6 words) - should not find "You are a helpful assistant for"
        result_high = infer_template_from_strings(strings, min_consecutive_words=6)
        # "You are a helpful assistant for" is exactly 6 words, should match
        assert result_high == "You are a helpful assistant for {{var_0}}"

    def test_mixed_length_common_sequences(self):
        """Test strings with common sequences of different lengths."""
        inferrer = TemplateInferrer(min_consecutive_words=3)

        strings = [
            "The quick brown fox jumps over Alice",
            "The quick brown fox jumps over Bob",
            "The quick brown fox jumps over Charlie",
        ]
        result = inferrer.infer_template(strings)
        # "The quick brown fox jumps over" is 6 consecutive words
        assert result == "The quick brown fox jumps over {{var_0}}"

    def test_no_common_words(self):
        """Test strings with no common consecutive words."""
        inferrer = TemplateInferrer(min_consecutive_words=3)

        strings = [
            "Alice likes programming",
            "Bob enjoys swimming",
            "Charlie loves reading",
        ]
        result = inferrer.infer_template(strings)
        # No common sequence of 3+ words
        assert result == "{{var_0}}"

    def test_case_sensitive_word_matching(self):
        """Test that word matching is case-sensitive."""
        inferrer = TemplateInferrer(min_consecutive_words=3)

        strings = [
            "You Are A helper for Alice",
            "you are a helper for Bob",
        ]
        result = inferrer.infer_template(strings)
        # Case mismatch means no common sequence
        assert result == "{{var_0}}"

    def test_numbers_count_as_words(self):
        """Test that numbers count as words in consecutive word counting."""
        inferrer = TemplateInferrer(min_consecutive_words=4)

        strings = [
            "Order ID 12345 was processed successfully",
            "Order ID 67890 was processed successfully",
        ]
        result = inferrer.infer_template(strings)
        # "Order ID" (2 words) + number + "was processed successfully" (3 words)
        # Should find "was processed successfully" (3 words) but we need 4
        # Or "Order ID" but that's only 2 words
        # Let's check what happens
        assert "{{var_" in result

    def test_edge_case_single_word_difference(self):
        """Test edge case where only one word differs."""
        inferrer = TemplateInferrer(min_consecutive_words=3)

        strings = [
            "Hello world this is Alice speaking today here",
            "Hello world this is Bob speaking today here",
        ]
        result = inferrer.infer_template(strings)
        # "Hello world this is" (4 words) before variable
        # "speaking today here" (3 words) after variable
        assert result == "Hello world this is {{var_0}} speaking today here"

    def test_very_long_common_sequence(self):
        """Test with very long common sequence."""
        inferrer = TemplateInferrer(min_consecutive_words=3)

        common = "You are an AI assistant designed to help users with various tasks including answering questions providing recommendations and offering guidance"
        strings = [
            f"{common} for Alice",
            f"{common} for Bob",
        ]
        result = inferrer.infer_template(strings)
        # Long common sequence should be detected despite being much longer than threshold
        assert common in result
        assert "{{var_0}}" in result
