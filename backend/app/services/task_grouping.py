import re
from collections import defaultdict


class TemplateFinder:
    """Finds common templates in strings by extracting shared segments.

    Templates consist of fixed segments separated by variable placeholders.
    Example: "hello {{var_0}} world {{var_1}} test"
    """

    def _tokenize(self, text: str) -> list[str]:
        """Tokenize text while preserving newlines as separate tokens."""
        # Replace newlines with a special marker, split, then restore
        parts = []
        current = []

        for char_idx, char in enumerate(text):
            if char == "\n":
                if current:
                    parts.extend("".join(current).split())
                    current = []
                parts.append("\n")
            else:
                current.append(char)

        if current:
            parts.extend("".join(current).split())

        return parts

    def match_template(self, template: str, s: str) -> tuple[bool, dict[str, str]]:
        """Match `s` against a template with placeholders {{var_name}}.

        Returns:
            (matched: bool, mapping: dict(var_name -> value))

        Rules:
            - Fixed text must match exactly.
            - A variable can match an empty string.
            - Repeated variables must match the same substring.
            - The entire string s must be consumed (no partial matches).

        """
        # Parse template into fixed parts + variable names
        pattern = re.compile(r"\{\{\s*([^}]+?)\s*\}\}")
        var_names = [m.group(1) for m in pattern.finditer(template)]
        fixed_parts = pattern.split(template)[::2]  # fixed0, fixed1, ..., fixedN
        n_vars = len(var_names)
        n_fixed = len(fixed_parts)

        # Quick case: no variables at all
        if n_vars == 0:
            return (s == template, {})

        L = len(s)

        # Precompute remaining fixed-part lengths for pruning
        suffix_fixed_len = [0] * (n_fixed + 1)
        for i in range(n_fixed - 1, -1, -1):
            suffix_fixed_len[i] = suffix_fixed_len[i + 1] + len(fixed_parts[i])

        # Occurrences of a fixed substring f in s starting at or after min_pos
        def occurrences(f: str, min_pos: int):
            if f == "":
                for p in range(min_pos, L + 1):
                    yield p
            else:
                pos = s.find(f, min_pos)
                while pos != -1:
                    yield pos
                    pos = s.find(f, pos + 1)

        # Backtracking, copies mapping on each branch to avoid backtracking complexity
        def dfs(i: int, prev_end: int, assignments: dict[str, str]):
            # Can remaining fixed parts even fit?
            if suffix_fixed_len[i] > L - prev_end:
                return False, {}

            fixed = fixed_parts[i]
            # For the very first fixed part, if nonempty, it must be placed at position 0
            min_pos = prev_end if not (i == 0 and fixed != "") else 0

            for p in occurrences(fixed, min_pos):
                if i == 0 and fixed != "" and p != 0:
                    continue

                end = p + len(fixed)

                # If this is the last fixed part, must end exactly at the end of s
                if i == n_vars and end != L:
                    continue

                # Cannot move backwards
                if p < prev_end:
                    continue

                new_map = assignments.copy()

                # Extract variable before this fixed (except for i == 0)
                if i > 0:
                    var_name = var_names[i - 1]
                    var_value = s[prev_end:p]

                    if var_name in new_map:
                        if new_map[var_name] != var_value:
                            continue
                    else:
                        new_map[var_name] = var_value

                if i == n_vars:  # placed last fixed part
                    return True, new_map

                ok, result = dfs(i + 1, end, new_map)
                if ok:
                    return True, result

            return False, {}

        return dfs(0, 0, {})

    def group_strings(
        self,
        strs: list[str],
        min_segment_words: int,
        min_matching_strings,
    ) -> dict[str, list[int]]:
        """Group strings by their templates.

        Args:
            strs: List of strings to analyze

        Returns:
            Dict mapping templates to list of string indices that match

        """
        if not strs or min_matching_strings < 1:
            return {}

        self.tokenized = [self._tokenize(s) for s in strs]
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

                    # Add the fixed segment, preserving newlines
                    segment_str = self._tokens_to_string(segment)
                    template_parts.append(segment_str)
                    current_token_pos = j + seg_len
                    break

        # Add trailing variable if there are tokens after the last segment
        if current_token_pos < len(tokens):
            template_parts.append(f"{{{{var_{var_counter}}}}}")

        return " ".join(template_parts)

    def _tokens_to_string(self, tokens: list[str]) -> str:
        """Convert tokens back to string, handling newlines specially."""
        result = []
        for i, token in enumerate(tokens):
            if token == "\n":
                # Don't add space before/after newlines
                if result and result[-1] != "\n":
                    result.append("\n")
                else:
                    result.append("\n")
            else:
                if result and result[-1] != "\n":
                    result.append(" ")
                result.append(token)

        return "".join(result)

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

    def _get_matching_indices(
        self,
        segments: list[list[str]],
        min_segment_words: int,
    ) -> list[int]:
        """Get all string indices that match the given segments."""
        if not segments:
            return list(range(len(self.tokenized)))

        # Start with candidates from first segment
        candidates = self._get_candidate_matches(segments[0], min_segment_words)

        # Filter candidates that match all segments
        matching = []
        for idx in candidates:
            if self._matches_segments(self.tokenized[idx], segments):
                matching.append(idx)
        return matching

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
