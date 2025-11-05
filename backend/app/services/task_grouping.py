import re
from collections import defaultdict


class TemplateFinder:
    """Finds common templates in strings by extracting shared segments.

    Templates consist of fixed segments separated by variable placeholders.
    Example: "hello {{var_0}} world {{var_1}} test"
    """

    def __init__(self, min_segment_words: int, min_matching_strings: int):
        """Initialize the TemplateFinder.

        Args:
            min_segment_words: Minimum number of words in a template segment
            min_matching_traces: Minimum number of strings that must match a template

        """
        self.min_segment_words = min_segment_words
        self.min_matching_traces = min_matching_strings

    def match_template(self, template: str, s: str) -> tuple[bool, dict[str, str]]:
        """Check if a string matches a template and extract variable values.

        Args:
            template: Template string with {{var_X}} placeholders
            s: String to match against the template

        Returns:
            Tuple of (matches: bool, variables: dict[str, str])
            If matches is True, variables contains the extracted values

        """
        # Parse template into segments and variable positions

        # Split template by variable placeholders
        # Pattern matches {{var_0}}, {{var_1}}, etc.
        var_pattern = r"\{\{var_\d+\}\}"

        # Find all variables and their positions
        variables = re.findall(var_pattern, template)

        # Split template by variables to get fixed segments
        segments = re.split(var_pattern, template)

        # Convert segments to token lists
        segment_tokens = [seg.split() for seg in segments if seg.strip()]

        # Tokenize the input string
        string_tokens = s.split()

        # Try to match the template
        extracted_vars = {}
        current_pos = 0

        for i, segment in enumerate(segment_tokens):
            if not segment:  # Skip empty segments
                continue

            # Find this segment in the string starting from current_pos
            seg_len = len(segment)
            found = False

            for j in range(current_pos, len(string_tokens) - seg_len + 1):
                if string_tokens[j : j + seg_len] == segment:
                    # Extract variable value before this segment (if any)
                    if i > 0 and current_pos < j:
                        var_name = variables[i - 1].strip("{}")
                        var_value = " ".join(string_tokens[current_pos:j])
                        extracted_vars[var_name] = var_value

                    current_pos = j + seg_len
                    found = True
                    break

            if not found:
                return False, {}

        # Handle trailing variable (after last segment)
        if len(segment_tokens) < len(variables) + 1 and current_pos < len(
            string_tokens,
        ):
            var_name = variables[-1].strip("{}")
            var_value = " ".join(string_tokens[current_pos:])
            extracted_vars[var_name] = var_value
        elif len(segment_tokens) == len(variables) and current_pos < len(string_tokens):
            # Variable at the end
            var_name = variables[-1].strip("{}")
            var_value = " ".join(string_tokens[current_pos:])
            extracted_vars[var_name] = var_value

        # Check if we matched all expected variables
        expected_vars = {var.strip("{}") for var in variables}
        if extracted_vars.keys() != expected_vars:
            return False, {}

        return True, extracted_vars

    def group_strings(self, strs: list[str]) -> dict[str, list[int]]:
        """Group strings by their templates.

        Args:
            strs: List of strings to analyze

        Returns:
            Dict mapping templates to list of string indices that match

        """
        if not strs or self.min_matching_traces < 1:
            return {}

        self.tokenized = [s.split() for s in strs]
        self._build_ngram_index()

        # Extract templates for each string
        string_to_template = {}

        for idx in range(len(strs)):
            segments, length = self._extract_best_template(idx)

            if segments and length >= self.min_segment_words:
                # Create template string with variable placeholders
                template = self._segments_to_template(segments)
                string_to_template[idx] = (template, length)

        # Resolve conflicts: if a string matches multiple templates, assign to longest
        final_assignment = {}
        template_lengths = defaultdict(int)

        # Group by template and track lengths
        template_to_candidates = defaultdict(list)
        for idx, (template, length) in string_to_template.items():
            template_to_candidates[template].append((idx, length))
            template_lengths[template] = max(template_lengths[template], length)

        # Assign each string to its best (longest) template
        for idx, (template, length) in string_to_template.items():
            if idx not in final_assignment or length > final_assignment[idx][1]:
                final_assignment[idx] = (template, length)

        # Build final result
        result = defaultdict(list)
        for idx, (template, length) in final_assignment.items():
            result[template].append(idx)

        # Filter out groups with fewer than min_matching_traces strings
        result = {
            template: indices
            for template, indices in result.items()
            if len(indices) >= self.min_matching_traces
        }

        return dict(result)

    def _build_ngram_index(self):
        """Build n-gram index for fast lookup."""
        self.ngram_to_strings = defaultdict(set)
        n = self.min_segment_words

        for idx, tokens in enumerate(self.tokenized):
            for i in range(len(tokens) - n + 1):
                ngram = tuple(tokens[i : i + n])
                self.ngram_to_strings[ngram].add(idx)

    def _segments_to_template(self, segments: list[list[str]]) -> str:
        """Convert segments to template string with variable placeholders."""
        if not segments:
            return ""

        template_parts = []
        for i, segment in enumerate(segments):
            template_parts.append(" ".join(segment))
            if i < len(segments) - 1:
                template_parts.append(f"{{{{var_{i}}}}}")

        return " ".join(template_parts)

    def _matches_segments(self, sentence: list[str], segments: list[list[str]]) -> bool:
        """Check if sentence contains all segments in order."""
        if not segments:
            return True

        start_idx = 0
        for segment in segments:
            seg_len = len(segment)
            found = False
            for i in range(start_idx, len(sentence) - seg_len + 1):
                if sentence[i : i + seg_len] == segment:
                    start_idx = i + seg_len
                    found = True
                    break
            if not found:
                return False
        return True

    def _get_candidate_matches(self, segment: list[str]) -> set[int]:
        """Quickly find candidate strings that might contain this segment."""
        if len(segment) < self.min_segment_words:
            return set(range(len(self.tokenized)))

        # Use n-gram index for fast filtering
        ngram = tuple(segment[: self.min_segment_words])
        return self.ngram_to_strings.get(ngram, set())

    def _get_matching_indices(self, segments: list[list[str]]) -> list[int]:
        """Get all string indices that match the given segments."""
        if not segments:
            return list(range(len(self.tokenized)))

        # Start with candidates from first segment
        candidates = self._get_candidate_matches(segments[0])

        # Filter candidates that match all segments
        matching = []
        for idx in candidates:
            if self._matches_segments(self.tokenized[idx], segments):
                matching.append(idx)
        return matching

    def _extract_best_template(self, string_idx: int) -> tuple[list[list[str]], int]:
        """Extract the longest valid template from a string using optimized greedy approach.
        Returns (segments, total_length).
        """
        tokens = self.tokenized[string_idx]
        segments = []
        current_pos = 0
        total_len = 0
        n = self.min_segment_words

        while current_pos <= len(tokens) - n:
            # Find the longest segment starting at current_pos
            best_seg = None
            best_seg_len = 0

            # Binary search for maximum valid segment length
            left, right = n, len(tokens) - current_pos

            while left <= right:
                mid = (left + right) // 2
                candidate_seg = tokens[current_pos : current_pos + mid]
                test_segments = segments + [candidate_seg]

                # Quick check using n-gram index
                candidates = self._get_candidate_matches(candidate_seg)
                match_count = sum(
                    1
                    for idx in candidates
                    if self._matches_segments(self.tokenized[idx], test_segments)
                )

                if match_count >= self.min_matching_traces:
                    best_seg = candidate_seg
                    best_seg_len = mid
                    left = mid + 1  # Try longer
                else:
                    right = mid - 1  # Try shorter

            if best_seg:
                segments.append(best_seg)
                total_len += len(best_seg)
                current_pos += len(best_seg)
            else:
                current_pos += 1

        return segments, total_len
