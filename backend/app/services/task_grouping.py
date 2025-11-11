from collections import defaultdict


class TemplateFinder:
    """Finds common templates in strings by extracting shared segments.

    Templates consist of fixed segments separated by variable placeholders.
    Example: "hello {{var_0}} world {{var_1}} test"
    """

    def match_template(self, template: str, s: str) -> tuple[bool, dict[str, str]]:
        """Match a string against a template with variable placeholders.

        Args:
            template: Template string with {{var_name}} placeholders
            s: String to match against the template

        Returns:
            Tuple of (match_success, variable_mapping)

        Example:
            >>> match_template("Hi Mr. {{var_0}}, how are you?", "Hi Mr. Johnson, how are you?")
            (True, {'var_0': 'Johnson'})

        """
        # Parse template into tokens (literals and variables)
        tokens = []
        i = 0

        while i < len(template):
            var_start = template.find("{{", i)

            if var_start == -1:
                # No more variables, rest is literal
                if i < len(template):
                    tokens.append(("lit", template[i:]))
                break

            # Add literal before variable (if any)
            if var_start > i:
                tokens.append(("lit", template[i:var_start]))

            # Find variable end
            var_end = template.find("}}", var_start + 2)
            if var_end == -1:
                return False, {}  # Malformed template

            var_name = template[var_start + 2 : var_end]
            tokens.append(("var", var_name))
            i = var_end + 2

        # Match tokens against string
        variables = {}
        pos = 0

        for idx in range(len(tokens)):
            token_type, token_value = tokens[idx]

            if token_type == "lit":
                # Literal must match exactly
                lit_len = len(token_value)
                if pos + lit_len > len(s) or s[pos : pos + lit_len] != token_value:
                    return False, {}
                pos += lit_len

            else:  # variable
                # Determine how much to consume for this variable
                if idx == len(tokens) - 1:
                    # Last token - consume remaining string
                    var_value = s[pos:]
                else:
                    # Find next literal token
                    next_lit_idx = idx + 1
                    while (
                        next_lit_idx < len(tokens) and tokens[next_lit_idx][0] != "lit"
                    ):
                        next_lit_idx += 1

                    if next_lit_idx >= len(tokens):
                        # No more literals - greedy match for first var, empty for rest
                        if idx == next_lit_idx - 1:
                            var_value = s[pos:]
                        else:
                            var_value = ""
                    else:
                        # Find next literal in string
                        next_lit = tokens[next_lit_idx][1]

                        # Search for the literal, considering we need to match remaining pattern
                        search_start = pos
                        found_pos = s.find(next_lit, search_start)

                        if found_pos == -1:
                            return False, {}

                        # For consecutive variables before this literal,
                        # give everything to the first one
                        consecutive_vars_before = 0
                        check_idx = idx
                        while check_idx > 0 and tokens[check_idx - 1][0] == "var":
                            consecutive_vars_before += 1
                            check_idx -= 1

                        if consecutive_vars_before == 0:
                            var_value = s[pos:found_pos]
                        else:
                            # We're not the first in a sequence of consecutive vars
                            var_value = ""

                # Validate consistency if variable seen before
                if token_value in variables:
                    if variables[token_value] != var_value:
                        return False, {}
                else:
                    variables[token_value] = var_value

                pos += len(var_value)

        # Verify entire string was consumed
        return (pos == len(s), variables)

    def group_strings(
        self,
        strs: list[str],
        min_segment_words: int,
        min_matching_strings: int,
    ) -> dict[str, list[int]]:
        """Group strings by their templates.

        Args:
            strs: List of strings to analyze

        Returns:
            Dict mapping templates to list of string indices that match

        """
        if not strs or min_matching_strings < 1:
            return {}

        self.tokenized = [s.split() for s in strs]
        self._build_ngram_index(min_segment_words)

        # Extract templates for each string
        string_to_template = {}

        for idx in range(len(strs)):
            segments, length = self._extract_best_template(
                idx,
                min_segment_words,
                min_matching_strings,
            )

            if segments and length >= min_segment_words:
                # Create template string with variable placeholders
                template = self._segments_to_template(segments, idx)
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

        # Filter out groups with fewer than min_matching_strings strings
        result = {
            template: indices
            for template, indices in result.items()
            if len(indices) >= min_matching_strings
        }

        return dict(result)

    def _build_ngram_index(self, min_segment_words: int):
        """Build n-gram index for fast lookup."""
        self.ngram_to_strings = defaultdict(set)
        n = min_segment_words

        for idx, tokens in enumerate(self.tokenized):
            for i in range(len(tokens) - n + 1):
                ngram = tuple(tokens[i : i + n])
                self.ngram_to_strings[ngram].add(idx)

    def _segments_to_template(self, segments: list[list[str]], string_idx: int) -> str:
        """Convert segments to template string with variable placeholders."""
        if not segments:
            return ""

        template_parts = []
        tokens = self.tokenized[string_idx]
        current_token_pos = 0
        var_counter = 0

        for i, segment in enumerate(segments):
            # Find where this segment appears in the original string
            seg_len = len(segment)
            for j in range(current_token_pos, len(tokens) - seg_len + 1):
                if tokens[j : j + seg_len] == segment:
                    # Add variable placeholder for any gap before this segment
                    if j > current_token_pos:
                        template_parts.append(f"{{{{var_{var_counter}}}}}")
                        var_counter += 1

                    # Add the fixed segment
                    template_parts.append(" ".join(segment))
                    current_token_pos = j + seg_len
                    break

        # Add trailing variable if there are tokens after the last segment
        if current_token_pos < len(tokens):
            template_parts.append(f"{{{{var_{var_counter}}}}}")

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

    def _get_candidate_matches(
        self,
        segment: list[str],
        min_segment_words: int,
    ) -> set[int]:
        """Quickly find candidate strings that might contain this segment."""
        if len(segment) < min_segment_words:
            return set(range(len(self.tokenized)))

        # Use n-gram index for fast filtering
        ngram = tuple(segment[:min_segment_words])
        return self.ngram_to_strings.get(ngram, set())

    def _extract_best_template(
        self,
        string_idx: int,
        min_segment_words: int,
        min_matching_strings: int,
    ) -> tuple[list[list[str]], int]:
        """Extract the longest valid template from a string using optimized greedy approach.
        Returns (segments, total_length).
        """
        tokens = self.tokenized[string_idx]
        segments = []
        current_pos = 0
        total_len = 0
        n = min_segment_words

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
                candidates = self._get_candidate_matches(
                    candidate_seg,
                    min_segment_words,
                )
                match_count = sum(
                    1
                    for idx in candidates
                    if self._matches_segments(self.tokenized[idx], test_segments)
                )

                if match_count >= min_matching_strings:
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
