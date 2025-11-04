"""Template inference algorithm for extracting common patterns from strings.

Based on the r4u-trace implementation, this module provides tools to:
1. Infer templates from multiple similar strings
2. Extract variable values from rendered strings using templates
3. Validate template consistency
"""


class TemplateInferrer:
    """Infers the original template from multiple strings that were generated from it.

    The algorithm:
    1. Finds common substrings that appear in all input strings
    2. These common parts act as "anchors" that separate variable regions
    3. Identifies variable regions between anchors
    4. Reconstructs the template with placeholder markers
    """

    def __init__(self, placeholder_format: str = "{{{{var_{index}}}}}"):
        """Args:
        placeholder_format: Format string for placeholders. Use {index} for numbering.
                          Quadruple braces {{{{}}}} will produce double braces {{}} in output.

        """
        self.placeholder_format = placeholder_format

    def infer_template(self, strings: list[str]) -> str:
        """Infer the template from a list of rendered strings.

        Args:
            strings: List of strings generated from the same template

        Returns:
            The inferred template string

        """
        if not strings:
            return ""
        if len(strings) == 1:
            return strings[0]

        # Find common substrings that can serve as anchors
        anchors = self._find_common_anchors(strings)

        # Split strings using anchors and build segments
        segments = self._build_segments(strings, anchors)

        # Build the template
        template = self._construct_template(segments)
        return template

    def _find_common_anchors(self, strings: list[str]) -> list[str]:
        """Find common substrings that appear in all strings in the same relative order.
        Uses a token-aware approach to avoid fragmenting words.

        Returns:
            List of anchor texts in order of appearance.

        """
        if len(strings) < 2:
            return []

        # Tokenize the reference string into words and separators
        reference = min(strings, key=len)
        tokens = self._tokenize(reference)

        # Find common token sequences
        anchors_with_positions = []
        i = 0
        token_pos = 0  # Position in reference string

        while i < len(tokens):
            # Try to find the longest common sequence of tokens
            best_anchor = None
            best_positions = None
            best_token_count = 0

            for token_count in range(len(tokens) - i, 0, -1):
                # Build candidate from tokens
                candidate_tokens = tokens[i : i + token_count]
                candidate = "".join(candidate_tokens)

                # Find positions in all strings
                positions = self._find_positions_in_all(candidate, strings)

                if positions and self._positions_maintain_order(
                    positions, anchors_with_positions,
                ):
                    # Check if this is a meaningful anchor
                    if self._is_token_sequence_meaningful(
                        candidate_tokens, token_count,
                    ):
                        best_anchor = candidate
                        best_positions = positions
                        best_token_count = token_count
                        break

            if best_anchor:
                anchors_with_positions.append((best_anchor, best_positions))
                i += best_token_count
                token_pos += len(best_anchor)
            else:
                token_pos += len(tokens[i])
                i += 1

        # Return just the anchor texts
        return [anchor for anchor, _ in anchors_with_positions]

    def _tokenize(self, text: str) -> list[str]:
        """Tokenize text into words and separators.
        Each token is either a sequence of alphanumeric chars or a single non-alphanumeric char.
        """
        tokens = []
        i = 0
        while i < len(text):
            if text[i].isalnum():
                # Collect alphanumeric sequence
                j = i
                while j < len(text) and text[j].isalnum():
                    j += 1
                tokens.append(text[i:j])
                i = j
            else:
                # Single non-alphanumeric character
                tokens.append(text[i])
                i += 1
        return tokens

    def _is_token_sequence_meaningful(self, tokens: list[str], count: int) -> bool:
        """Check if a token sequence is meaningful as an anchor."""
        # Single token sequences
        if count == 1:
            token = tokens[0]
            # Allow single punctuation/whitespace tokens
            if not token.isalnum():
                return True
            # Allow long words (5+ chars)
            if len(token) >= 5:
                return True
            # Reject short word fragments
            return False

        # Multi-token sequences are generally meaningful
        # But reject very short sequences that are purely alphabetic
        sequence = "".join(tokens)
        if sequence.isalpha() and len(sequence) <= 3:
            return False

        return True

    def _find_positions_in_all(
        self, substring: str, strings: list[str],
    ) -> list[int] | None:
        """Find the position of substring in each string. Returns None if not found in any string."""
        positions = []

        for s in strings:
            pos = s.find(substring)
            if pos == -1:
                return None
            positions.append(pos)

        return positions

    def _positions_maintain_order(
        self, new_positions: list[int], existing_anchors: list[tuple[str, list[int]]],
    ) -> bool:
        """Check if new positions come after all existing anchor positions."""
        if not existing_anchors:
            return True

        # Get the last anchor's positions
        last_anchor_text, last_positions = existing_anchors[-1]
        last_anchor_len = len(last_anchor_text)

        # New positions should be after (last_position + last_anchor_length) in all strings
        for i, (last_pos, new_pos) in enumerate(zip(last_positions, new_positions)):
            if new_pos < last_pos + last_anchor_len:
                return False

        return True

    def _build_segments(
        self, strings: list[str], anchors: list[str],
    ) -> list[tuple[str | None, bool]]:
        """Build segments by splitting strings using anchors."""
        if not anchors:
            # No common parts - entire strings are variable
            return [(None, False)]

        segments = []
        reference = strings[0]
        pos = 0

        for anchor in anchors:
            # Find where this anchor appears in the reference string
            anchor_pos = reference.find(anchor, pos)

            if anchor_pos > pos:
                # There's a variable region before this anchor
                segments.append((None, False))

            # Add the anchor as a common segment
            segments.append((anchor, True))
            pos = anchor_pos + len(anchor)

        # Check if there's a variable region at the end
        if pos < len(reference):
            segments.append((None, False))

        return segments

    def _construct_template(self, segments: list[tuple[str | None, bool]]) -> str:
        """Construct the template string from segments."""
        template_parts = []
        placeholder_index = 0

        for text, is_common in segments:
            if is_common:
                template_parts.append(text)
            else:
                # Variable segment - add placeholder
                placeholder = self.placeholder_format.format(index=placeholder_index)
                template_parts.append(placeholder)
                placeholder_index += 1

        return "".join(template_parts)


def infer_template_from_strings(
    strings: list[str], placeholder_format: str = "{{{{var_{index}}}}}",
) -> str:
    """Convenience function to infer a template from a list of strings.

    Args:
        strings: List of strings generated from the same template
        placeholder_format: Format for placeholders (use {index} for numbering, quadruple braces {{{{}}}} for double braces {{}})

    Returns:
        The inferred template string

    """
    inferrer = TemplateInferrer(placeholder_format)
    return inferrer.infer_template(strings)
