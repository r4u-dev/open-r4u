import bisect
import hashlib
import random
from collections import defaultdict
from functools import cache


# ---------- Helper: greedy LCS implementation (adapted to run on a subset) ----------
def greedy_lcs_grouping_on_subset(strs_subset, n, m, original_indices):
    """strs_subset: list[str] (subset in original order)
    original_indices: list[int] mapping subset index -> original index

    returns: dict { template_str -> sorted list of original indices }
    """
    # Tokenize & int-encode
    tokenized = [s.split() for s in strs_subset]
    N = len(tokenized)
    vocab = {}
    next_id = 1
    token_ids = []
    for sent in tokenized:
        row = []
        for tok in sent:
            if tok not in vocab:
                vocab[tok] = next_id
                next_id += 1
            row.append(vocab[tok])
        token_ids.append(row)

    max_len = max((len(t) for t in token_ids), default=0)
    if max_len < n:
        return {}

    # rolling hash params
    MASK = (1 << 64) - 1
    BASE = 1000003
    pow_cache = [1] * (max_len + 1)
    for i in range(1, max_len + 1):
        pow_cache[i] = (pow_cache[i - 1] * BASE) & MASK

    prefixes = []
    for tok_ids in token_ids:
        h = [0] * (len(tok_ids) + 1)
        for i, v in enumerate(tok_ids):
            h[i + 1] = ((h[i] * BASE) + v) & MASK
        prefixes.append(h)

    def sub_hash(prefix, l, r):
        return (prefix[r] - (prefix[l] * pow_cache[r - l])) & MASK

    # Global index for all substrings length >= n inside this subset
    global_len_map = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
    for sidx, toks in enumerate(token_ids):
        Ls = len(toks)
        pref = prefixes[sidx]
        for L in range(n, Ls + 1):
            gm = global_len_map[L]
            for start in range(Ls - L + 1):
                h = sub_hash(pref, start, start + L)
                gm[h][sidx].append(start)

    def find_best_sub_in_range(base_idx, start, end):
        base_pref = prefixes[base_idx]
        max_possible = end - start
        if max_possible < n:
            return None
        low, high = n, max_possible
        bestL = 0
        while low <= high:
            mid = (low + high) // 2
            found = False
            gm = global_len_map.get(mid)
            if gm is None:
                high = mid - 1
                continue
            for i in range(start, end - mid + 1):
                h = sub_hash(base_pref, i, i + mid)
                occ = gm.get(h)
                if occ and len(occ) >= m:
                    found = True
                    break
            if found:
                bestL = mid
                low = mid + 1
            else:
                high = mid - 1

        if bestL == 0:
            return None

        gm = global_len_map[bestL]
        best_choice = None
        best_count = 0
        best_pos = None
        for i in range(start, end - bestL + 1):
            h = sub_hash(base_pref, i, i + bestL)
            occ = gm.get(h)
            if not occ:
                continue
            cnt = len(occ)
            if cnt > best_count:
                best_count = cnt
                best_choice = h
                best_pos = (i, i + bestL)
        if not best_pos:
            return None
        return best_pos

    def extract_segments_for_base(base_idx, start, end):
        choice = find_best_sub_in_range(base_idx, start, end)
        if not choice:
            return []
        i, j = choice
        left = extract_segments_for_base(base_idx, start, i)
        right = extract_segments_for_base(base_idx, j, end)
        return left + [(i, j)] + right

    results = {}
    for base_idx in range(N):
        base_tokens = tokenized[base_idx]
        if len(base_tokens) < n:
            continue
        segs = extract_segments_for_base(base_idx, 0, len(base_tokens))
        if not segs:
            continue

        parts = []
        last = 0
        var_idx = 0
        for a, b in segs:
            if a > last:
                parts.append(f"{{{{var_{var_idx}}}}}")
                var_idx += 1
            parts.extend(base_tokens[a:b])
            last = b
        if last < len(base_tokens):
            parts.append(f"{{{{var_{var_idx}}}}}")
        template = " ".join(parts)

        matched = []
        base_pref = prefixes[base_idx]
        for sidx in range(N):
            pos = 0
            ok = True
            for a, b in segs:
                seg_len = b - a
                h = sub_hash(base_pref, a, b)
                starts = global_len_map[seg_len].get(h, {}).get(sidx)
                if not starts:
                    ok = False
                    break
                k = bisect.bisect_left(starts, pos)
                if k == len(starts):
                    ok = False
                    break
                pos = starts[k] + seg_len
            if ok:
                matched.append(original_indices[sidx])  # map back to original index

        if len(matched) >= m:
            results.setdefault(template, set()).update(matched)

    # conflict resolution
    tpl_lengths = {
        tpl: sum(1 for w in tpl.split() if not w.startswith("{{var_"))
        for tpl in results
    }
    owner = {}
    for tpl, idxs in results.items():
        for idx in idxs:
            if idx not in owner or tpl_lengths[tpl] > tpl_lengths[owner[idx]]:
                owner[idx] = tpl

    grouped = defaultdict(list)
    for idx, tpl in owner.items():
        grouped[tpl].append(idx)

    out = {}
    for tpl, idxs in grouped.items():
        if len(idxs) >= m:
            out[tpl] = sorted(idxs)
    return out


# ---------- MinHash + LSH utilities ----------
def deterministic_shingle_hash(shingle_str):
    # deterministic hash -> integer using sha1
    return int(hashlib.sha1(shingle_str.encode("utf8")).hexdigest(), 16)


def compute_shingles_for_token_list(tokens, k):
    """Return set of integer shingle hashes for token list (k-shingles)."""
    L = len(tokens)
    if k > L:
        return set()
    s = set()
    for i in range(L - k + 1):
        sh = " ".join(tokens[i : i + k])
        s.add(deterministic_shingle_hash(sh))
    return s


def make_minhash_signature(shingle_set, num_perm, a_coeffs, b_coeffs, prime):
    """Compute MinHash signature (list of ints) for a set of shingle ints."""
    if not shingle_set:
        # return large values for empty sets
        return [prime] * num_perm
    sig = []
    for a, b in zip(a_coeffs, b_coeffs):
        mn = prime + 1
        for sh in shingle_set:
            hv = (a * (sh % prime) + b) % prime
            mn = min(mn, hv)
        sig.append(mn)
    return sig


def lsh_buckets_from_signatures(signatures, num_bands):
    """signatures: list of lists (num_perm length)
    returns buckets: dict (band_id, band_hash) -> list of indices
    """
    if not signatures:
        return {}
    num_perm = len(signatures[0])
    rows = num_perm // num_bands
    buckets = defaultdict(list)
    for idx, sig in enumerate(signatures):
        for b in range(num_bands):
            start = b * rows
            band_slice = tuple(sig[start : start + rows])
            # hash the band tuple deterministically
            band_hash = hashlib.sha1(
                ",".join(map(str, band_slice)).encode(),
            ).hexdigest()
            buckets[(b, band_hash)].append(idx)
    return buckets


# union-find for creating clusters
def union_find_make(n):
    parent = list(range(n))
    rank = [0] * n

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra == rb:
            return
        if rank[ra] < rank[rb]:
            parent[ra] = rb
        else:
            parent[rb] = ra
            if rank[ra] == rank[rb]:
                rank[ra] += 1

    return parent, find, union


# ---------- Top-level wrapper: MinHash + LSH + greedy LCS ----------
def minhash_lsh_greedy_grouping(
    strs,
    n,
    m,
    shingle_size=2,
    num_perm=128,
    num_bands=32,
    min_cluster_size=None,
    seed=42,
):
    """Main function.
    - strs: list[str]
    - n: minimum words per fixed segment
    - m: min matching strings needed for a template
    - shingle_size: k for k-shingles (default 2 or 3 recommended)
    - num_perm: MinHash permutations (higher -> better accuracy, slower)
    - num_bands: LSH bands (num_perm must be divisible by num_bands)
    - min_cluster_size: minimum cluster size to process (default = m)
    Returns: dict {template -> sorted list of original indices}
    """
    if min_cluster_size is None:
        min_cluster_size = m
    assert num_perm % num_bands == 0, "num_perm must be divisible by num_bands"

    # Tokenize once
    tokenized = [s.split() for s in strs]
    N = len(tokenized)

    # --- prepare MinHash hash functions ---
    random.seed(seed)
    prime = (1 << 61) - 1  # large prime for hashing mod
    a_coeffs = [random.randrange(1, prime - 1) for _ in range(num_perm)]
    b_coeffs = [random.randrange(0, prime - 1) for _ in range(num_perm)]

    # --- compute shingle sets and signatures ---
    shingle_sets = [
        compute_shingles_for_token_list(tokens, shingle_size) for tokens in tokenized
    ]
    signatures = [
        make_minhash_signature(s, num_perm, a_coeffs, b_coeffs, prime)
        for s in shingle_sets
    ]

    # --- LSH banding into buckets ---
    buckets = lsh_buckets_from_signatures(signatures, num_bands)

    # --- union-find to cluster sentences that share any bucket ---
    parent, find, union = union_find_make(N)
    for bucket_key, members in buckets.items():
        if len(members) <= 1:
            continue
        first = members[0]
        for other in members[1:]:
            union(first, other)

    # build clusters
    clusters = defaultdict(list)
    for i in range(N):
        clusters[find(i)].append(i)
    cluster_lists = [sorted(v) for v in clusters.values()]

    # --- process each cluster with greedy LCS (only clusters >= min_cluster_size) ---
    all_groupings = {}
    for cluster in cluster_lists:
        if len(cluster) < min_cluster_size:
            continue
        strs_subset = [strs[i] for i in cluster]
        orig_indices = list(cluster)
        g = greedy_lcs_grouping_on_subset(strs_subset, n, m, orig_indices)
        # merge g into all_groupings (templates are text -> set of indices)
        for tpl, idxs in g.items():
            all_groupings.setdefault(tpl, set()).update(idxs)

    # Optionally: run greedy on leftover (ungrouped) sentences or large singletons if desired
    # (Left out here for brevity.)

    # Final conflict resolution (if a sentence in multiple templates assign to longest template)
    tpl_lengths = {
        tpl: sum(1 for w in tpl.split() if not w.startswith("{{var_"))
        for tpl in all_groupings
    }
    owner = {}
    for tpl, idxs in all_groupings.items():
        for idx in idxs:
            if idx not in owner or tpl_lengths[tpl] > tpl_lengths[owner[idx]]:
                owner[idx] = tpl

    grouped = defaultdict(list)
    for idx, tpl in owner.items():
        grouped[tpl].append(idx)

    out = {}
    for tpl, idxs in grouped.items():
        if len(idxs) >= m:
            out[tpl] = sorted(idxs)
    return out


class TemplateFinder:
    def __init__(
        self,
        min_segment_words: int = 2,
        min_matching_strings: int = 2,
    ):
        """max_segment_words: optional cap on segment length to reduce index size and boost speed.
        If None, segments up to the full token length are indexed.
        """
        self.min_segment_words = min_segment_words
        self.min_matching_strings = min_matching_strings

    @staticmethod
    def _tokenize(s: str) -> list[str]:
        return s.split()

    def group_strings(self, strs: list[str]) -> dict[str, list[int]]:
        """Greedy LCS template grouping.

        Args:
            strs: list of sentences (strings)
            n: minimum number of words in a fixed segment
            m: minimum number of sentences that must match a template

        Returns:
            dict { template_string -> sorted list of sentence indices }

        """
        return minhash_lsh_greedy_grouping(
            strs,
            self.min_segment_words,
            self.min_matching_strings,
        )

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
