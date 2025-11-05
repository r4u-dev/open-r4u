import re


class TemplateFinder:
    """Class to group similar strings into templates with variable segments."""

    def __init__(self, min_segment_words: int = 2, min_matching_strings: int = 2):
        self.min_segment_words = min_segment_words
        self.min_matching_strings = min_matching_strings

    def _tokenize(self, s: str) -> list[str]:
        """Tokenize a string into words."""
        return s.split()

    def _find_matching_indexes(self, segment, indexes, strs) -> list[int]:
        """Find indexes of strings that contain the segment."""
        return [i for i in indexes if segment in strs[i]]

    def _expand_segment(
        self,
        strs,
        tokens,
        start_idx,
        end_idx,
        indexes,
    ) -> tuple[int | None, int | None, list[int]]:
        """Expand a segment to include as many matching strings as possible."""
        current_segment = " ".join(tokens[start_idx:end_idx])
        matching = self._find_matching_indexes(current_segment, indexes, strs)

        if len(matching) < self.min_matching_strings:
            return None, None, []

        best_start = start_idx
        best_end = end_idx
        best_matching = matching

        # Expand left
        temp_start = start_idx
        while temp_start > 0:
            temp_start -= 1
            expanded = " ".join(tokens[temp_start:end_idx])
            new_matching = self._find_matching_indexes(expanded, best_matching, strs)
            if len(new_matching) >= self.min_matching_strings:
                best_start = temp_start
                best_matching = new_matching
            else:
                break

        # Expand right
        temp_end = best_end
        while temp_end < len(tokens):
            temp_end += 1
            expanded = " ".join(tokens[best_start:temp_end])
            new_matching = self._find_matching_indexes(expanded, best_matching, strs)
            if len(new_matching) >= self.min_matching_strings:
                best_end = temp_end
                best_matching = new_matching
            else:
                break

        return best_start, best_end, best_matching

    def _find_all_segments_for_seed(
        self,
        seed_idx,
        strs,
        indexes,
    ) -> list[tuple[int, int, list[int], str]]:
        """Find all valid segments for a seed string."""
        tokens = self._tokenize(strs[seed_idx])
        segments = []

        for i in range(len(tokens) - self.min_segment_words + 1):
            start, end, matches = self._expand_segment(
                strs,
                tokens,
                i,
                i + self.min_segment_words,
                indexes,
            )
            if start is not None and len(matches) >= self.min_matching_strings:
                seg_text = " ".join(tokens[start:end])
                segments.append((start, end, matches, seg_text))
        return segments

    def _build_template_from_segments(self, seed_idx, strs, segments) -> str:
        """Build a template string from identified segments."""
        tokens = self._tokenize(strs[seed_idx])
        sorted_segments = sorted(segments, key=lambda x: x[0])

        template_parts = []
        last_pos = 0
        var_counter = 0

        for start, end, _, _ in sorted_segments:
            if start > last_pos:
                template_parts.append(f"{{{{var_{var_counter}}}}}")
                var_counter += 1

            template_parts.append(" ".join(tokens[start:end]))
            last_pos = end

        if last_pos < len(tokens):
            template_parts.append(f"{{{{var_{var_counter}}}}}")

        return " ".join(template_parts)

    def _select_best_segments(
        self,
        all_segments,
    ) -> list[tuple[int, int, list[int], str]]:
        """Select the best non-overlapping segments."""
        if not all_segments:
            return []
        sorted_segs = sorted(all_segments, key=lambda x: (x[0], -(x[1] - x[0])))
        selected, used = [], set()
        for seg in sorted_segs:
            r = set(range(seg[0], seg[1]))
            if not (r & used):
                selected.append(seg)
                used |= r
        return selected

    def _find_group(
        self,
        seed_idx,
        strs,
        indexes,
    ) -> tuple[str | None, list[int] | None]:
        """Find a group of similar strings for a given seed index."""
        all_segs = self._find_all_segments_for_seed(
            seed_idx,
            strs,
            indexes,
        )
        if not all_segs:
            return None, None

        best_segs = self._select_best_segments(all_segs)
        if not best_segs:
            return None, None

        template = self._build_template_from_segments(seed_idx, strs, best_segs)

        matching = indexes.copy()
        for _, _, matches, _ in best_segs:
            matching = [i for i in matching if i in matches]

        if len(matching) >= self.min_matching_strings:
            return template, matching
        return None, None

    def group_strings(
        self,
        strs: list[str],
    ) -> dict[str, list[int]]:
        """Group similar strings into templates with variable segments.

        Args:
            strs: List of input strings to be grouped.
            min_segment_words: Minimum number of words in a segment to consider for grouping.
            min_matching_strings: Minimum number of strings that must match a template for it to be valid.

        Returns:
            A dictionary mapping template strings to lists of indexes of matching strings.

        """
        groups = {}
        assigned = set()

        for i, _ in enumerate(strs):
            if i in assigned:
                continue

            available = [j for j in range(len(strs)) if j not in assigned]
            if len(available) < self.min_matching_strings:
                break

            template, matching = self._find_group(
                i,
                strs,
                available,
            )
            if template and matching:
                groups[template] = matching
                assigned |= set(matching)

        return groups

    def match_template(
        self,
        template: str,
        s: str,
    ) -> tuple[bool, dict[str, str]]:
        """Match a string against a template and extract variables.

        Args:
            template: Template with placeholders like {{var_0}}
            s: Input string to test

        Returns:
            (bool, dict)
            bool = True if string matches template
            dict = variable assignments, e.g. {"var_0": "Alice"}

        """
        # Tokenize template into segments: fixed parts and variables
        # Example: "{{var_0}} likes pizza" -> ["{{var_0}}", "likes pizza"]

        # Identify variable placeholders and fixed text outside them
        var_pattern = re.compile(r"\{\{(var_\d+)\}\}")
        tokens = template.split()  # template words
        s_tokens = s.split()  # string words

        t_i = 0  # index in template tokens
        s_i = 0  # index in string tokens
        variables = {}

        while t_i < len(tokens) and s_i <= len(s_tokens):
            t_word = tokens[t_i]
            m = var_pattern.fullmatch(t_word)

            # If this template token is a variable placeholder
            if m:
                var_name = m.group(1)

                # If it's the last token, variable consumes the rest
                if t_i == len(tokens) - 1:
                    variables[var_name] = " ".join(s_tokens[s_i:])
                    return True, variables

                # Otherwise capture until next fixed word is found
                next_fixed = tokens[t_i + 1]
                next_is_var = var_pattern.fullmatch(next_fixed)

                # If next is also a variable, we cannot determine split — return false
                if next_is_var:
                    return False, {}

                # Find location of next fixed token in s_tokens
                collected = []
                found = False
                for j in range(s_i, len(s_tokens)):
                    collected.append(s_tokens[j])
                    # match start of substring — make sure next fixed word matches exactly
                    if s_tokens[j] == next_fixed:
                        found = True
                        break

                if not found:
                    return False, {}

                # variable = everything before the fixed token
                if len(collected) == 1:  # next token matched immediately => empty var
                    variables[var_name] = ""
                else:
                    variables[var_name] = " ".join(collected[:-1])

                # Move string pointer to the fixed token
                s_i = s_i + len(collected) - 1
                t_i += 1

            else:
                # Fixed token, must match exactly
                if s_i >= len(s_tokens) or tokens[t_i] != s_tokens[s_i]:
                    return False, {}
                t_i += 1
                s_i += 1

        # After loop, if we used all template tokens AND string tokens
        if t_i == len(tokens) and s_i == len(s_tokens):
            return True, variables

        return False, {}
