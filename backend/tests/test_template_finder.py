import pytest

from app.services.task_grouping import TemplateFinder


class TestTemplateFinder:
    def test_group_strings_basic(self):
        """Test grouping of similar strings into templates."""
        strings = [
            "Order pizza for Alice",
            "Order pizza for Bob",
            "Order sushi for Alice",
            "Order sushi for Bob",
            "Cancel pizza order for Alice",
        ]
        finder = TemplateFinder()
        groups = finder.group_strings(
            strings,
            min_segment_words=2,
            min_matching_strings=2,
        )
        # There should be at least two groups: one for "Order pizza for ..." and one for "Order sushi for ..."
        templates = list(groups.keys())
        assert any("Order pizza for" in t for t in templates)
        assert any("Order sushi for" in t for t in templates)
        # Each group should have at least 2 strings
        for idxs in groups.values():
            assert len(idxs) >= 2
        # All grouped indices should be valid
        all_indices = [i for idxs in groups.values() for i in idxs]
        assert all(isinstance(i, int) and 0 <= i < len(strings) for i in all_indices)

    def test_group_strings_with_variables(self):
        """Test that variable segments are detected and templated."""
        strings = [
            "Send email to Alice about project X",
            "Send email to Bob about project X",
            "Send email to Alice about project Y",
            "Send email to Bob about project Y",
        ]
        finder = TemplateFinder()
        groups = finder.group_strings(
            strings,
            min_segment_words=2,
            min_matching_strings=2,
        )
        assert len(groups) == 2
        template = next(iter(groups))
        # Should have two variable placeholders
        print(groups)
        assert template.count("{{var_0}}") == 1
        assert "Send email to Alice about project" in template

        finder = TemplateFinder()
        groups = finder.group_strings(
            strings,
            min_segment_words=2,
            min_matching_strings=2,
        )
        # Should have at least one group with the common pattern
        assert len(groups) >= 1
        # Find the template that has the pattern
        templates = list(groups.keys())
        matching_template = None
        for t in templates:
            if "Send email to" in t and "about project" in t:
                matching_template = t
                break
        assert matching_template is not None
        # Should have variable placeholders
        assert "{{var_" in matching_template
        assert "Send email to" in matching_template
        assert "about project" in matching_template

    @pytest.mark.parametrize(
        "template,s,expected_match,expected_vars",
        [
            (
                "Order pizza for {{var_0}}",
                "Order pizza for Alice",
                True,
                {"var_0": "Alice"},
            ),
            (
                "Order pizza for {{var_0}}",
                "Order pizza for Bob",
                True,
                {"var_0": "Bob"},
            ),
            (
                "Order pizza for {{var_0}}",
                "Order sushi for Alice",
                False,
                {},
            ),
            (
                "Send email to {{var_0}} about project {{var_1}}",
                "Send email to Alice about project X",
                True,
                {"var_0": "Alice", "var_1": "X"},
            ),
            (
                "Send email to {{var_0}} about project {{var_1}}",
                "Send email to Bob about project Y",
                True,
                {"var_0": "Bob", "var_1": "Y"},
            ),
            (
                "Send email to {{var_0}} about project {{var_1}}",
                "Send email to Alice about project",
                False,
                {},
            ),
            (
                "{{var_0}} is a developer",
                "Alice is a developer",
                True,
                {"var_0": "Alice"},
            ),
            (
                "{{var_0}} is a developer",
                "Bob is a designer",
                False,
                {},
            ),
            (
                "Welcome {{var_0}} to {{var_1}}",
                "Welcome John to Paris",
                True,
                {"var_0": "John", "var_1": "Paris"},
            ),
            (
                "Welcome {{var_0}} to {{var_1}}",
                "Welcome John",
                False,
                {},
            ),
        ],
    )
    def test_match_template(self, template, s, expected_match, expected_vars):
        """Test matching strings to templates and extracting variables."""
        finder = TemplateFinder()
        match, variables = finder.match_template(template, s)
        assert match == expected_match
        assert variables == expected_vars

    def test_match_template_variable_at_end(self):
        finder = TemplateFinder()
        template = "Hello {{var_0}}"
        s = "Hello Alice"
        match, variables = finder.match_template(template, s)
        assert match is True
        assert variables == {"var_0": "Alice"}

    def test_match_template_variable_at_start(self):
        finder = TemplateFinder()
        template = "{{var_0}} likes pizza"
        s = "Bob likes pizza"
        match, variables = finder.match_template(template, s)
        assert match is True
        assert variables == {"var_0": "Bob"}

    def test_match_template_multiple_variables(self):
        finder = TemplateFinder()
        template = "{{var_0}} ordered {{var_1}}"
        s = "Alice ordered sushi"
        match, variables = finder.match_template(template, s)
        assert match is True
        assert variables == {"var_0": "Alice", "var_1": "sushi"}
