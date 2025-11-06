from functools import cache


class TemplateFinder:
    def __init__(
        self,
        min_segment_words: int = 2,
        min_matching_strings: int = 2,
        max_segment_words: int | None = None,
    ):
        """max_segment_words: optional cap on segment length to reduce index size and boost speed.
        If None, segments up to the full token length are indexed.
        """
        self.min_segment_words = min_segment_words
        self.min_matching_strings = min_matching_strings
        self.max_segment_words = max_segment_words

    @staticmethod
    def _tokenize(s: str) -> list[str]:
        return s.split()

    def _build_ngram_index(
        self,
        all_tokens: list[list[str]],
    ) -> dict[tuple[str, ...], set[int]]:
        """Build inverted index mapping n-gram tuples to set of string indices that contain that n-gram.
        Complexity: O(N * L^2) time and O(N * L^2) index entries in worst case.
        """
        idx = {}
        N = len(all_tokens)
        for i, tokens in enumerate(all_tokens):
            T = len(tokens)
            max_len = (
                T if self.max_segment_words is None else min(self.max_segment_words, T)
            )
            for start in range(T):
                # only consider lengths >= min_segment_words
                for length in range(self.min_segment_words, max_len - start + 1):
                    ng = tuple(tokens[start : start + length])
                    if ng in idx:
                        idx[ng].add(i)
                    else:
                        idx[ng] = {i}
        return idx

    def group_strings(self, strs: list[str]) -> dict[str, list[int]]:
        n = self.min_segment_words
        m = self.min_matching_strings
        all_tokens = [self._tokenize(s) for s in strs]
        N = len(strs)

        # Build n-gram index once
        ngram_index = self._build_ngram_index(all_tokens)

        candidates = []  # (template_str, matched_set, total_fixed_words)

        for base_idx, base_tokens in enumerate(all_tokens):
            L = len(base_tokens)
            if n > L:
                continue

            # For a base, we can look up any segment (start,length) by tuple lookup
            seg_matches = {}
            for start in range(L):
                max_len = (
                    L - start
                    if self.max_segment_words is None
                    else min(self.max_segment_words, L - start)
                )
                for length in range(n, max_len + 1):
                    seg = tuple(base_tokens[start : start + length])
                    matches = ngram_index.get(seg, set())
                    seg_matches[(start, length)] = matches

            # dynamic programming search for best non-overlapping segments
            @cache
            def dfs(
                pos: int,
                current_matches_fs: frozenset,
                chosen_count: int,
            ) -> tuple[int, tuple[tuple[int, int], ...]]:
                current_matches = set(current_matches_fs)
                if len(current_matches) < m:
                    return (-(10**9), ())
                if pos >= L:
                    if chosen_count > 0:
                        return (0, ())
                    return (-(10**9), ())

                best_score = -(10**9)
                best_segments: tuple[tuple[int, int], ...] = ()
                # skip
                skip_score, skip_segs = dfs(pos + 1, current_matches_fs, chosen_count)
                if skip_score > best_score:
                    best_score = skip_score
                    best_segments = skip_segs

                # choose segment starting at pos
                max_length_possible = (
                    L - pos
                    if self.max_segment_words is None
                    else min(self.max_segment_words, L - pos)
                )
                for length in range(n, max_length_possible + 1):
                    seg_key = (pos, length)
                    seg_set = seg_matches.get(seg_key, set())
                    if not seg_set:
                        continue
                    new_matches = current_matches.intersection(seg_set)
                    if len(new_matches) < m:
                        continue
                    new_matches_fs = frozenset(new_matches)
                    tail_score, tail_segs = dfs(
                        pos + length,
                        new_matches_fs,
                        chosen_count + 1,
                    )
                    if tail_score < -(10**8):
                        continue
                    score = length + tail_score
                    if score > best_score:
                        best_score = score
                        best_segments = ((pos, length),) + tail_segs

                return (best_score, best_segments)

            initial_set = frozenset(range(N))
            best_score, best_segments = dfs(0, initial_set, 0)
            if best_score > 0 and len(best_segments) > 0:
                # compute matched set intersection
                matched = set(range(N))
                for seg in best_segments:
                    matched &= seg_matches[seg]
                if len(matched) >= m:
                    template_str = self._build_template_from_segments(
                        base_tokens,
                        sorted(best_segments, key=lambda x: x[0]),
                    )
                    candidates.append((template_str, matched, best_score))

        # Merge identical templates, pick best scores
        merged = {}
        for tpl, matched, score in candidates:
            if tpl in merged:
                prev_matched, prev_score = merged[tpl]
                if score > prev_score:
                    merged[tpl] = (set(matched), score)
                else:
                    merged[tpl] = (prev_matched.union(matched), prev_score)
            else:
                merged[tpl] = (set(matched), score)

        template_items = [
            (tpl, matched, score) for tpl, (matched, score) in merged.items()
        ]

        # Assign each string to best template by score
        assignment = {tpl: set() for tpl, _, _ in template_items}
        for idx in range(N):
            best_tpl = None
            best_score = -1
            for tpl, matched, score in template_items:
                if idx in matched and score > best_score:
                    best_score = score
                    best_tpl = tpl
            if best_tpl is not None:
                assignment[best_tpl].add(idx)

        final = {}
        for tpl, members in assignment.items():
            if len(members) >= m:
                final[tpl] = sorted(members)
        return final

    def _build_template_from_segments(
        self,
        tokens: list[str],
        segments: list[tuple[int, int]],
    ) -> str:
        parts = []
        var_idx = 0
        pos = 0
        for start, length in segments:
            if start > pos:
                parts.append(f"{{{{var_{var_idx}}}}}")
                var_idx += 1
            seg_text = " ".join(tokens[start : start + length])
            parts.append(seg_text)
            pos = start + length
        if pos < len(tokens):
            parts.append(f"{{{{var_{var_idx}}}}}")
        return " ".join(parts)

    def match_template(self, template: str, s: str) -> tuple[bool, dict[str, str]]:
        """Check if string s matches template (placeholders like {{var_0}}).
        If it matches, return (True, mapping) where mapping maps placeholder names
        to their extracted substring (joined by spaces). Otherwise return (False, {}).
        """
        t_tokens = template.split()
        s_tokens = self._tokenize(s)

        # Identify which template tokens are placeholders and extract their names
        is_placeholder = []
        placeholder_names = []
        for tt in t_tokens:
            if tt.startswith("{{") and tt.endswith("}}"):
                is_placeholder.append(True)
                placeholder_names.append(tt[2:-2].strip())
            else:
                is_placeholder.append(False)
                placeholder_names.append(None)

        # Precompute indices of remaining fixed tokens counts for pruning
        fixed_remaining_from = [0] * (len(t_tokens) + 1)
        cnt = 0
        for i in range(len(t_tokens) - 1, -1, -1):
            if not is_placeholder[i]:
                cnt += 1
            fixed_remaining_from[i] = cnt
        fixed_remaining_from[len(t_tokens)] = 0

        # recursive backtracking
        @cache
        def backtrack(
            t_idx: int,
            s_idx: int,
            assignments_tuple: tuple[tuple[str, tuple[int, int]], ...],
        ) -> tuple[tuple[tuple[str, tuple[int, int]], ...], int] | None:
            """Try to match template from t_idx against s_tokens from s_idx.
            assignments_tuple stores already assigned placeholder spans as ((name,(start,end)), ...)
            Returns a tuple (assignments_tuple_updated, end_s_idx) on success or None on failure.
            """
            assignments = dict(assignments_tuple)
            # prune: if not enough tokens left to match remaining fixed tokens, fail
            # Need at least fixed_remaining_from[t_idx] tokens remaining
            if len(s_tokens) - s_idx < fixed_remaining_from[t_idx]:
                return None

            if t_idx == len(t_tokens) and s_idx == len(s_tokens):
                return (tuple(sorted(assignments.items())), s_idx)
            if t_idx == len(t_tokens) or s_idx > len(s_tokens):
                return None

            if not is_placeholder[t_idx]:
                # fixed token must match the current s token
                if s_idx < len(s_tokens) and s_tokens[s_idx] == t_tokens[t_idx]:
                    return backtrack(
                        t_idx + 1,
                        s_idx + 1,
                        tuple(sorted(assignments.items())),
                    )
                return None
            name = placeholder_names[t_idx]
            # find next fixed token index after this placeholder (if any)
            next_fixed_idx = None
            for j in range(t_idx + 1, len(t_tokens)):
                if not is_placeholder[j]:
                    next_fixed_idx = j
                    break

            # If same placeholder appears again later, we must ensure consistency.
            already_assigned_span = assignments.get(name)

            # If there's no next fixed token, placeholder consumes the rest of s_tokens
            if next_fixed_idx is None:
                # assign remaining tokens (could be empty? require at least one token)
                if s_idx >= len(s_tokens):
                    return None  # require at least one token for placeholder
                span = (s_idx, len(s_tokens))
                # check consistency with previous assignment if any
                if already_assigned_span is not None:
                    # previous assigned text must equal current span text
                    prev_start, prev_end = already_assigned_span
                    prev_text = " ".join(s_tokens[prev_start:prev_end])
                    curr_text = " ".join(s_tokens[span[0] : span[1]])
                    if prev_text != curr_text:
                        return None
                    # else keep assignments
                    assignments[name] = span
                    return backtrack(
                        t_idx + 1,
                        len(s_tokens),
                        tuple(sorted(assignments.items())),
                    )
                assignments[name] = span
                return backtrack(
                    t_idx + 1,
                    len(s_tokens),
                    tuple(sorted(assignments.items())),
                )

            # there's a next fixed token; find occurrences of that fixed token in s_tokens after s_idx
            next_fixed_token = t_tokens[next_fixed_idx]
            # search positions where next_fixed_token occurs
            possible_positions = [
                p
                for p in range(s_idx, len(s_tokens))
                if s_tokens[p] == next_fixed_token
            ]
            if not possible_positions:
                return None

            for pos in possible_positions:
                # placeholder would take s_tokens[s_idx:pos]
                if pos == s_idx:
                    # allow empty? We require at least one token for placeholder
                    continue
                span = (s_idx, pos)
                if already_assigned_span is not None:
                    prev_start, prev_end = already_assigned_span
                    prev_text = " ".join(s_tokens[prev_start:prev_end])
                    curr_text = " ".join(s_tokens[span[0] : span[1]])
                    if prev_text != curr_text:
                        continue  # inconsistent, try next pos
                # tentatively assign and try to match remaining (including the next fixed token at pos)
                new_assignments = dict(assignments)
                new_assignments[name] = span
                res = backtrack(
                    next_fixed_idx,
                    pos,
                    tuple(sorted(new_assignments.items())),
                )
                if res is not None:
                    return res
            return None

        result = backtrack(0, 0, tuple())
        if result is None:
            return (False, {})
        assignments_tuple, _ = result
        # convert spans to strings
        mapping: dict[str, str] = {}
        for name, (start, end) in assignments_tuple:
            mapping[name] = " ".join(s_tokens[start:end])
        return (True, mapping)
