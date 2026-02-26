"""
Parameterized generator for TEST4: Property-Based Tests from Spec Invariants.

TNI Pattern A: Spec lists exact invariants. Brief says "write property tests."

Each seed produces:
- A different module type (sort_utils, codec, collections_utils, math_utils)
- 4-7 invariants per module, drawn from a rich pool
- A correct module.py implementation of the target functions
- A skeleton tests/test_properties.py the agent must fill in
- Mutant implementations (one per invariant) for mutation testing

Grading checks:
1.  test file exists
2.  property-based approach used (hypothesis imported or @given used)
3.  each invariant has a corresponding test function
4.  all tests pass on correct module.py
5+. each mutant is caught (tests fail when mutant replaces module)
10. total mutants caught >= (num_invariants - 1) out of num_invariants
11. test count >= num_invariants
12. tests use @given or st. (hypothesis strategies)
"""
from __future__ import annotations

import textwrap
from generators.base import TaskGenerator, GeneratedTask
from generators.primitives import SeededRandom

# ---------------------------------------------------------------------------
# Module + Invariant definitions
# ---------------------------------------------------------------------------

# Each MODULE_DEF has:
#   name, display_name, description
#   functions: list of (func_name, signature_comment, correct_body, docstring)
#   invariants: list of invariant dicts with:
#       id, title, formal (the property statement), hypothesis_hint,
#       mutant_body (replaces one function body to violate the invariant),
#       mutant_func (which function is mutated), check_desc

MODULE_POOL = [
    # ── sort_utils ────────────────────────────────────────────────────────
    {
        "name": "sort_utils",
        "display_name": "Sort Utilities",
        "description": "sorting and ordering functions",
        "module_header": """\
\"\"\"Sort utilities — correct implementation.\"\"\"
from typing import List
""",
        "functions": {
            "sort_list": """\
def sort_list(xs: List[int]) -> List[int]:
    \"\"\"Return a new sorted list (ascending).\"\"\"
    return sorted(xs)
""",
            "sort_stable": """\
def sort_stable(xs: List[int]) -> List[int]:
    \"\"\"Return a stable sorted list. Equivalent to sort_list for ints.\"\"\"
    return sorted(xs)
""",
            "is_sorted": """\
def is_sorted(xs: List[int]) -> bool:
    \"\"\"Return True if list is non-decreasing.\"\"\"
    return all(xs[i] <= xs[i+1] for i in range(len(xs)-1))
""",
            "merge_sorted": """\
def merge_sorted(a: List[int], b: List[int]) -> List[int]:
    \"\"\"Merge two sorted lists into one sorted list.\"\"\"
    result = []
    i = j = 0
    while i < len(a) and j < len(b):
        if a[i] <= b[j]:
            result.append(a[i]); i += 1
        else:
            result.append(b[j]); j += 1
    result.extend(a[i:])
    result.extend(b[j:])
    return result
""",
        },
        "invariants": [
            {
                "id": "SORT_IDEMPOTENT",
                "title": "sort is idempotent: sort(sort(x)) == sort(x)",
                "formal": "sort_list(sort_list(xs)) == sort_list(xs) for all lists xs",
                "hypothesis_hint": "@given(st.lists(st.integers()))",
                "mutant_func": "sort_list",
                "mutant_body": """\
def sort_list(xs: List[int]) -> List[int]:
    \"\"\"Return a new sorted list (ascending).\"\"\"
    # MUTANT: reverse sort breaks idempotency check (sort(sort(x)) != sort(x) when reversed)
    return sorted(xs, reverse=True)
""",
                "check_desc": "sort(sort(x)) equals sort(x)",
            },
            {
                "id": "SORT_PRESERVES_LENGTH",
                "title": "sort preserves list length",
                "formal": "len(sort_list(xs)) == len(xs) for all lists xs",
                "hypothesis_hint": "@given(st.lists(st.integers()))",
                "mutant_func": "sort_list",
                "mutant_body": """\
def sort_list(xs: List[int]) -> List[int]:
    \"\"\"Return a new sorted list (ascending).\"\"\"
    # MUTANT: drops duplicates — breaks length preservation
    return sorted(set(xs))
""",
                "check_desc": "len(sort_list(xs)) == len(xs)",
            },
            {
                "id": "SORT_PRESERVES_ELEMENTS",
                "title": "sort preserves elements (same multiset)",
                "formal": "sorted(sort_list(xs)) == sorted(xs) — same elements with same frequencies",
                "hypothesis_hint": "@given(st.lists(st.integers()))",
                "mutant_func": "sort_list",
                "mutant_body": """\
def sort_list(xs: List[int]) -> List[int]:
    \"\"\"Return a new sorted list (ascending).\"\"\"
    # MUTANT: adds an extra element — breaks element preservation
    return sorted(xs) + [0]
""",
                "check_desc": "sort_list(xs) contains same elements as xs",
            },
            {
                "id": "SORT_ORDERED",
                "title": "sort output is non-decreasing",
                "formal": "is_sorted(sort_list(xs)) == True for all lists xs",
                "hypothesis_hint": "@given(st.lists(st.integers()))",
                "mutant_func": "is_sorted",
                "mutant_body": """\
def is_sorted(xs: List[int]) -> bool:
    \"\"\"Return True if list is non-decreasing.\"\"\"
    # MUTANT: always returns True — masks unsorted output
    return True
""",
                "check_desc": "is_sorted(sort_list(xs)) is True",
            },
            {
                "id": "MERGE_LENGTH",
                "title": "merge_sorted output length equals sum of input lengths",
                "formal": "len(merge_sorted(a, b)) == len(a) + len(b) for sorted inputs a, b",
                "hypothesis_hint": "@given(st.lists(st.integers()), st.lists(st.integers()))",
                "mutant_func": "merge_sorted",
                "mutant_body": """\
def merge_sorted(a: List[int], b: List[int]) -> List[int]:
    \"\"\"Merge two sorted lists into one sorted list.\"\"\"
    # MUTANT: skips duplicates — breaks length invariant
    return sorted(set(a) | set(b))
""",
                "check_desc": "len(merge_sorted(a,b)) == len(a)+len(b)",
            },
            {
                "id": "MERGE_SORTED",
                "title": "merge_sorted output is sorted",
                "formal": "is_sorted(merge_sorted(a, b)) == True for sorted inputs a, b",
                "hypothesis_hint": "@given(st.lists(st.integers()).map(sorted), st.lists(st.integers()).map(sorted))",
                "mutant_func": "merge_sorted",
                "mutant_body": """\
def merge_sorted(a: List[int], b: List[int]) -> List[int]:
    \"\"\"Merge two sorted lists into one sorted list.\"\"\"
    # MUTANT: concatenate without merging — result not sorted when inputs interleave
    return list(a) + list(b)
""",
                "check_desc": "is_sorted(merge_sorted(a,b)) is True for sorted a,b",
            },
        ],
    },
    # ── codec ─────────────────────────────────────────────────────────────
    {
        "name": "codec",
        "display_name": "String Codec",
        "description": "string encoding and decoding functions",
        "module_header": """\
\"\"\"String codec — correct implementation.\"\"\"
import base64
from typing import Optional
""",
        "functions": {
            "encode": """\
def encode(s: str) -> str:
    \"\"\"Base64-encode a UTF-8 string, return ASCII string.\"\"\"
    return base64.b64encode(s.encode('utf-8')).decode('ascii')
""",
            "decode": """\
def decode(s: str) -> str:
    \"\"\"Base64-decode an ASCII string, return UTF-8 string.\"\"\"
    return base64.b64decode(s.encode('ascii')).decode('utf-8')
""",
            "reverse_str": """\
def reverse_str(s: str) -> str:
    \"\"\"Reverse a string.\"\"\"
    return s[::-1]
""",
            "compress": """\
def compress(s: str) -> str:
    \"\"\"Run-length encode: 'aabbc' -> 'a2b2c1'.\"\"\"
    if not s:
        return ''
    result = []
    count = 1
    for i in range(1, len(s)):
        if s[i] == s[i-1]:
            count += 1
        else:
            result.append(s[i-1] + str(count))
            count = 1
    result.append(s[-1] + str(count))
    return ''.join(result)
""",
            "decompress": """\
def decompress(s: str) -> str:
    \"\"\"Decode run-length encoded string: 'a2b2c1' -> 'aabbc'.\"\"\"
    result = []
    i = 0
    while i < len(s):
        ch = s[i]
        i += 1
        num = []
        while i < len(s) and s[i].isdigit():
            num.append(s[i])
            i += 1
        result.append(ch * int(''.join(num) if num else '1'))
    return ''.join(result)
""",
        },
        "invariants": [
            {
                "id": "CODEC_ROUNDTRIP",
                "title": "decode(encode(x)) == x for all valid strings x",
                "formal": "decode(encode(s)) == s for all printable ASCII strings s",
                "hypothesis_hint": "@given(st.text(alphabet=st.characters(whitelist_categories=('Lu','Ll','Nd'), min_codepoint=32, max_codepoint=126)))",
                "mutant_func": "encode",
                "mutant_body": """\
def encode(s: str) -> str:
    \"\"\"Base64-encode a UTF-8 string, return ASCII string.\"\"\"
    # MUTANT: encodes twice — decode(encode(x)) != x
    return base64.b64encode(base64.b64encode(s.encode('utf-8'))).decode('ascii')
""",
                "check_desc": "decode(encode(s)) == s",
            },
            {
                "id": "CODEC_ENCODE_INJECTIVE",
                "title": "encode is injective: encode(a) == encode(b) implies a == b",
                "formal": "if encode(a) == encode(b) then a == b",
                "hypothesis_hint": "@given(st.text(), st.text())",
                "mutant_func": "encode",
                "mutant_body": """\
def encode(s: str) -> str:
    \"\"\"Base64-encode a UTF-8 string, return ASCII string.\"\"\"
    # MUTANT: always returns same value — not injective
    return 'AAAA'
""",
                "check_desc": "encode(a) != encode(b) when a != b",
            },
            {
                "id": "REVERSE_INVOLUTION",
                "title": "reverse is its own inverse: reverse(reverse(x)) == x",
                "formal": "reverse_str(reverse_str(s)) == s for all strings s",
                "hypothesis_hint": "@given(st.text())",
                "mutant_func": "reverse_str",
                "mutant_body": """\
def reverse_str(s: str) -> str:
    \"\"\"Reverse a string.\"\"\"
    # MUTANT: only reverses half — not an involution
    return s[:len(s)//2][::-1] + s[len(s)//2:]
""",
                "check_desc": "reverse_str(reverse_str(s)) == s",
            },
            {
                "id": "REVERSE_PRESERVES_LENGTH",
                "title": "reverse preserves string length",
                "formal": "len(reverse_str(s)) == len(s) for all strings s",
                "hypothesis_hint": "@given(st.text())",
                "mutant_func": "reverse_str",
                "mutant_body": """\
def reverse_str(s: str) -> str:
    \"\"\"Reverse a string.\"\"\"
    # MUTANT: drops last character — breaks length preservation
    return s[:-1][::-1] if s else s
""",
                "check_desc": "len(reverse_str(s)) == len(s)",
            },
            {
                "id": "COMPRESS_ROUNDTRIP",
                "title": "decompress(compress(x)) == x for all strings",
                "formal": "decompress(compress(s)) == s for all strings s with no digits",
                "hypothesis_hint": "@given(st.text(alphabet='abcdefghijklmnopqrstuvwxyz'))",
                "mutant_func": "compress",
                "mutant_body": """\
def compress(s: str) -> str:
    \"\"\"Run-length encode: 'aabbc' -> 'a2b2c1'.\"\"\"
    # MUTANT: counts are always 1 regardless of runs — breaks roundtrip for repeated chars
    if not s:
        return ''
    return ''.join(c + '1' for c in s)
""",
                "check_desc": "decompress(compress(s)) == s",
            },
            {
                "id": "COMPRESS_LENGTH",
                "title": "compress output is never longer than O(2*len(s))",
                "formal": "len(compress(s)) <= 2 * len(s) for all non-empty strings s",
                "hypothesis_hint": "@given(st.text(alphabet='abcdefghijklmnopqrstuvwxyz', min_size=1))",
                "mutant_func": "compress",
                "mutant_body": """\
def compress(s: str) -> str:
    \"\"\"Run-length encode: 'aabbc' -> 'a2b2c1'.\"\"\"
    # MUTANT: inserts extra separator — output can exceed 2*len
    if not s:
        return ''
    return '||'.join(c + str(1) for c in s)
""",
                "check_desc": "len(compress(s)) <= 2*len(s)",
            },
        ],
    },
    # ── collections_utils ─────────────────────────────────────────────────
    {
        "name": "collections_utils",
        "display_name": "Collection Utilities",
        "description": "collection manipulation functions (filter, map, merge, deduplicate)",
        "module_header": """\
\"\"\"Collection utilities — correct implementation.\"\"\"
from typing import List, Callable, TypeVar

T = TypeVar('T')
""",
        "functions": {
            "filter_items": """\
def filter_items(items: List[int], predicate: Callable[[int], bool]) -> List[int]:
    \"\"\"Return items for which predicate returns True.\"\"\"
    return [x for x in items if predicate(x)]
""",
            "deduplicate": """\
def deduplicate(items: List[int]) -> List[int]:
    \"\"\"Remove duplicates while preserving first-occurrence order.\"\"\"
    seen = set()
    result = []
    for x in items:
        if x not in seen:
            seen.add(x)
            result.append(x)
    return result
""",
            "flatten": """\
def flatten(nested: List[List[int]]) -> List[int]:
    \"\"\"Flatten one level of nesting.\"\"\"
    result = []
    for sublist in nested:
        result.extend(sublist)
    return result
""",
            "chunked": """\
def chunked(items: List[int], size: int) -> List[List[int]]:
    \"\"\"Split list into chunks of given size (last chunk may be smaller).\"\"\"
    if size <= 0:
        raise ValueError('chunk size must be positive')
    return [items[i:i+size] for i in range(0, len(items), size)]
""",
        },
        "invariants": [
            {
                "id": "FILTER_SUBSET",
                "title": "filter output is a subset of input",
                "formal": "all(x in items for x in filter_items(items, pred)) for all items, pred",
                "hypothesis_hint": "@given(st.lists(st.integers()))",
                "mutant_func": "filter_items",
                "mutant_body": """\
def filter_items(items: List[int], predicate: Callable[[int], bool]) -> List[int]:
    \"\"\"Return items for which predicate returns True.\"\"\"
    # MUTANT: returns negation — elements may not satisfy predicate
    return [x for x in items if not predicate(x)]
""",
                "check_desc": "all filtered elements satisfy predicate",
            },
            {
                "id": "FILTER_SATISFIES_PREDICATE",
                "title": "all elements in filtered output satisfy the predicate",
                "formal": "all(pred(x) for x in filter_items(items, pred)) for all items, pred",
                "hypothesis_hint": "@given(st.lists(st.integers()), st.integers())",
                "mutant_func": "filter_items",
                "mutant_body": """\
def filter_items(items: List[int], predicate: Callable[[int], bool]) -> List[int]:
    \"\"\"Return items for which predicate returns True.\"\"\"
    # MUTANT: includes one extra wrong element
    result = [x for x in items if predicate(x)]
    if items:
        result.append(items[0])
    return result
""",
                "check_desc": "every element in output satisfies predicate",
            },
            {
                "id": "DEDUP_UNIQUE",
                "title": "deduplicate output has no duplicates",
                "formal": "len(deduplicate(xs)) == len(set(xs)) for all lists xs",
                "hypothesis_hint": "@given(st.lists(st.integers()))",
                "mutant_func": "deduplicate",
                "mutant_body": """\
def deduplicate(items: List[int]) -> List[int]:
    \"\"\"Remove duplicates while preserving first-occurrence order.\"\"\"
    # MUTANT: returns original — does not remove duplicates
    return list(items)
""",
                "check_desc": "len(deduplicate(xs)) == len(set(xs))",
            },
            {
                "id": "DEDUP_SUBSET",
                "title": "deduplicate output elements are subset of input",
                "formal": "all(x in xs for x in deduplicate(xs)) for all lists xs",
                "hypothesis_hint": "@given(st.lists(st.integers()))",
                "mutant_func": "deduplicate",
                "mutant_body": """\
def deduplicate(items: List[int]) -> List[int]:
    \"\"\"Remove duplicates while preserving first-occurrence order.\"\"\"
    # MUTANT: adds extra element — output not subset of input
    seen = set()
    result = []
    for x in items:
        if x not in seen:
            seen.add(x)
            result.append(x)
    result.append(999999)  # extra element not in input
    return result
""",
                "check_desc": "all deduplicated elements came from input",
            },
            {
                "id": "FLATTEN_LENGTH",
                "title": "flatten preserves total element count",
                "formal": "len(flatten(xss)) == sum(len(xs) for xs in xss) for all nested lists",
                "hypothesis_hint": "@given(st.lists(st.lists(st.integers())))",
                "mutant_func": "flatten",
                "mutant_body": """\
def flatten(nested: List[List[int]]) -> List[int]:
    \"\"\"Flatten one level of nesting.\"\"\"
    # MUTANT: only takes first element of each sublist
    return [sub[0] for sub in nested if sub]
""",
                "check_desc": "len(flatten(xss)) == sum(len(xs) for xs in xss)",
            },
            {
                "id": "CHUNKED_ROUNDTRIP",
                "title": "flatten(chunked(xs, n)) == xs for all xs and positive n",
                "formal": "flatten(chunked(xs, n)) == xs for all xs and n > 0",
                "hypothesis_hint": "@given(st.lists(st.integers()), st.integers(min_value=1, max_value=10))",
                "mutant_func": "chunked",
                "mutant_body": """\
def chunked(items: List[int], size: int) -> List[List[int]]:
    \"\"\"Split list into chunks of given size (last chunk may be smaller).\"\"\"
    # MUTANT: drops remainder — flatten(chunked(xs,n)) may not equal xs
    if size <= 0:
        raise ValueError('chunk size must be positive')
    chunks = []
    for i in range(0, len(items) - size + 1, size):
        chunks.append(items[i:i+size])
    return chunks
""",
                "check_desc": "flatten(chunked(xs, n)) == xs",
            },
            {
                "id": "CHUNKED_SIZE",
                "title": "each chunk (except last) has exactly size elements",
                "formal": "all(len(c) == n for c in chunked(xs, n)[:-1]) for all xs and n > 0",
                "hypothesis_hint": "@given(st.lists(st.integers(), min_size=1), st.integers(min_value=1, max_value=5))",
                "mutant_func": "chunked",
                "mutant_body": """\
def chunked(items: List[int], size: int) -> List[List[int]]:
    \"\"\"Split list into chunks of given size (last chunk may be smaller).\"\"\"
    # MUTANT: uses size+1 step — chunks are too small
    if size <= 0:
        raise ValueError('chunk size must be positive')
    return [items[i:i+size-1] for i in range(0, len(items), size)]
""",
                "check_desc": "each chunk except last has exactly size elements",
            },
        ],
    },
    # ── math_utils ────────────────────────────────────────────────────────
    {
        "name": "math_utils",
        "display_name": "Math Utilities",
        "description": "mathematical functions with algebraic properties",
        "module_header": """\
\"\"\"Math utilities — correct implementation.\"\"\"
import math
from typing import List
""",
        "functions": {
            "gcd": """\
def gcd(a: int, b: int) -> int:
    \"\"\"Greatest common divisor of non-negative integers.\"\"\"
    a, b = abs(a), abs(b)
    while b:
        a, b = b, a % b
    return a
""",
            "lcm": """\
def lcm(a: int, b: int) -> int:
    \"\"\"Least common multiple of non-negative integers.\"\"\"
    if a == 0 or b == 0:
        return 0
    return abs(a * b) // gcd(a, b)
""",
            "clamp": """\
def clamp(value: float, lo: float, hi: float) -> float:
    \"\"\"Clamp value to [lo, hi] inclusive.\"\"\"
    if lo > hi:
        raise ValueError('lo must be <= hi')
    return max(lo, min(hi, value))
""",
            "running_average": """\
def running_average(values: List[float]) -> List[float]:
    \"\"\"Return list of running averages.\"\"\"
    if not values:
        return []
    result = []
    total = 0.0
    for i, v in enumerate(values, 1):
        total += v
        result.append(total / i)
    return result
""",
        },
        "invariants": [
            {
                "id": "GCD_DIVIDES_BOTH",
                "title": "gcd(a,b) divides both a and b",
                "formal": "a % gcd(a,b) == 0 and b % gcd(a,b) == 0 for all non-negative a, b (not both zero)",
                "hypothesis_hint": "@given(st.integers(min_value=1, max_value=10**6), st.integers(min_value=1, max_value=10**6))",
                "mutant_func": "gcd",
                "mutant_body": """\
def gcd(a: int, b: int) -> int:
    \"\"\"Greatest common divisor of non-negative integers.\"\"\"
    # MUTANT: returns a — may not divide b
    return abs(a)
""",
                "check_desc": "gcd(a,b) divides both a and b",
            },
            {
                "id": "GCD_COMMUTATIVE",
                "title": "gcd is commutative: gcd(a,b) == gcd(b,a)",
                "formal": "gcd(a, b) == gcd(b, a) for all non-negative a, b",
                "hypothesis_hint": "@given(st.integers(min_value=0, max_value=10**6), st.integers(min_value=0, max_value=10**6))",
                "mutant_func": "gcd",
                "mutant_body": """\
def gcd(a: int, b: int) -> int:
    \"\"\"Greatest common divisor of non-negative integers.\"\"\"
    # MUTANT: not symmetric — uses a-b which is not commutative
    return abs(a - b) if b != 0 else abs(a)
""",
                "check_desc": "gcd(a,b) == gcd(b,a)",
            },
            {
                "id": "LCM_MULTIPLE",
                "title": "lcm(a,b) is divisible by both a and b",
                "formal": "lcm(a,b) % a == 0 and lcm(a,b) % b == 0 for positive a, b",
                "hypothesis_hint": "@given(st.integers(min_value=1, max_value=1000), st.integers(min_value=1, max_value=1000))",
                "mutant_func": "lcm",
                "mutant_body": """\
def lcm(a: int, b: int) -> int:
    \"\"\"Least common multiple of non-negative integers.\"\"\"
    # MUTANT: returns a+b — not necessarily a multiple of either
    return abs(a + b)
""",
                "check_desc": "lcm(a,b) % a == 0 and lcm(a,b) % b == 0",
            },
            {
                "id": "LCM_GCD_IDENTITY",
                "title": "gcd(a,b) * lcm(a,b) == a * b",
                "formal": "gcd(a, b) * lcm(a, b) == abs(a * b) for positive a, b",
                "hypothesis_hint": "@given(st.integers(min_value=1, max_value=1000), st.integers(min_value=1, max_value=1000))",
                "mutant_func": "lcm",
                "mutant_body": """\
def lcm(a: int, b: int) -> int:
    \"\"\"Least common multiple of non-negative integers.\"\"\"
    # MUTANT: off by one — violates gcd*lcm == a*b
    if a == 0 or b == 0:
        return 0
    return abs(a * b) // gcd(a, b) + 1
""",
                "check_desc": "gcd(a,b) * lcm(a,b) == a*b",
            },
            {
                "id": "CLAMP_IN_RANGE",
                "title": "clamp output is always within [lo, hi]",
                "formal": "lo <= clamp(v, lo, hi) <= hi for all v, lo <= hi",
                "hypothesis_hint": "@given(st.floats(allow_nan=False, allow_infinity=False), st.floats(allow_nan=False, allow_infinity=False), st.floats(allow_nan=False, allow_infinity=False))",
                "mutant_func": "clamp",
                "mutant_body": """\
def clamp(value: float, lo: float, hi: float) -> float:
    \"\"\"Clamp value to [lo, hi] inclusive.\"\"\"
    # MUTANT: off-by-one on upper bound
    if lo > hi:
        raise ValueError('lo must be <= hi')
    return max(lo, min(hi - 1, value))
""",
                "check_desc": "lo <= clamp(v, lo, hi) <= hi",
            },
            {
                "id": "CLAMP_IDEMPOTENT",
                "title": "clamp is idempotent: clamp(clamp(v,lo,hi),lo,hi) == clamp(v,lo,hi)",
                "formal": "clamp(clamp(v, lo, hi), lo, hi) == clamp(v, lo, hi) for all v, lo <= hi",
                "hypothesis_hint": "@given(st.floats(allow_nan=False, allow_infinity=False, min_value=-1e6, max_value=1e6), st.floats(allow_nan=False, allow_infinity=False, min_value=-1e6, max_value=0), st.floats(allow_nan=False, allow_infinity=False, min_value=0, max_value=1e6))",
                "mutant_func": "clamp",
                "mutant_body": """\
def clamp(value: float, lo: float, hi: float) -> float:
    \"\"\"Clamp value to [lo, hi] inclusive.\"\"\"
    # MUTANT: adds epsilon — not idempotent
    if lo > hi:
        raise ValueError('lo must be <= hi')
    return max(lo, min(hi, value)) + 0.0001
""",
                "check_desc": "clamp(clamp(v,lo,hi),lo,hi) == clamp(v,lo,hi)",
            },
            {
                "id": "RUNNING_AVG_LENGTH",
                "title": "running_average output has same length as input",
                "formal": "len(running_average(xs)) == len(xs) for all lists xs",
                "hypothesis_hint": "@given(st.lists(st.floats(allow_nan=False, allow_infinity=False, min_value=-1e6, max_value=1e6)))",
                "mutant_func": "running_average",
                "mutant_body": """\
def running_average(values: List[float]) -> List[float]:
    \"\"\"Return list of running averages.\"\"\"
    # MUTANT: skips first element — length is one less
    if not values:
        return []
    result = []
    total = 0.0
    for i, v in enumerate(values[1:], 2):
        total += v
        result.append(total / i)
    return result
""",
                "check_desc": "len(running_average(xs)) == len(xs)",
            },
        ],
    },
]


def _build_module(mod: dict, selected_inv_ids: list[str]) -> str:
    """Build the correct module.py from the module definition."""
    parts = [mod["module_header"]]
    for func_body in mod["functions"].values():
        parts.append(func_body)
    return "\n".join(parts)


def _build_mutant_module(mod: dict, target_inv: dict) -> str:
    """Build a mutant module.py where one function is replaced by the mutant body."""
    parts = [mod["module_header"]]
    mutant_func = target_inv["mutant_func"]
    for func_name, func_body in mod["functions"].items():
        if func_name == mutant_func:
            parts.append(target_inv["mutant_body"])
        else:
            parts.append(func_body)
    return "\n".join(parts)


class Generator(TaskGenerator):
    task_id = "TEST4_property"
    domain = "testing"
    difficulty = "hard"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        rng = SeededRandom(seed)

        # Pick module type
        mod = MODULE_POOL[rng.randint(0, len(MODULE_POOL) - 1)]

        # Pick 4-7 invariants from the module's pool
        all_invs = mod["invariants"]
        num_inv = rng.randint(4, min(7, len(all_invs)))
        inv_indices = rng.sample(list(range(len(all_invs))), num_inv)
        selected_invs = [all_invs[i] for i in inv_indices]

        # Build workspace files
        module_src = _build_module(mod, [inv["id"] for inv in selected_invs])

        workspace_files: dict[str, str] = {
            "module.py": module_src,
            "tests/__init__.py": "",
            "tests/test_properties.py": self._test_skeleton(mod, selected_invs),
        }

        # Add mutant variants for grader (one per invariant)
        for inv in selected_invs:
            mutant_src = _build_mutant_module(mod, inv)
            workspace_files[f"mutants/{inv['id']}.py"] = mutant_src

        spec_md = self._generate_spec(mod, selected_invs, seed)
        brief_md = self._generate_brief(mod, selected_invs)

        expected = {
            "module_name": mod["name"],
            "invariant_ids": [inv["id"] for inv in selected_invs],
            "num_invariants": num_inv,
            "min_tests": num_inv,
            "min_mutants_caught": num_inv - 1,
            "mutant_ids": [inv["id"] for inv in selected_invs],
        }

        return GeneratedTask(
            task_id=self.task_id,
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected=expected,
            workspace_files=workspace_files,
        )

    def _test_skeleton(self, mod: dict, invs: list[dict]) -> str:
        func_names = list(mod["functions"].keys())
        imports_line = ", ".join(func_names)
        lines = [
            f'"""Property-based tests for {mod["display_name"]}.',
            "",
            "Use hypothesis to write property tests for each invariant listed below.",
            "Each @given test must:",
            "  1. Pass on the correct module.py.",
            "  2. FAIL when the corresponding mutant is substituted.",
            '"""',
            "import pytest",
            "from hypothesis import given, settings",
            "from hypothesis import strategies as st",
            f"from module import {imports_line}",
            "",
            "",
            "# TODO: Write property-based tests below.",
            "# Each invariant in the spec must have a corresponding test function.",
            "# Use @given decorators with hypothesis strategies.",
            "",
        ]
        for inv in invs:
            lines.append(f"# Invariant {inv['id']}: {inv['title']}")
            lines.append(f"# Formal: {inv['formal']}")
            lines.append(f"# Hint: {inv['hypothesis_hint']}")
            lines.append(f"# def test_{inv['id'].lower()}(...):")
            lines.append("#     ...")
            lines.append("")
        return "\n".join(lines) + "\n"

    def _generate_spec(self, mod: dict, invs: list[dict], seed: int) -> str:
        func_list = ", ".join(f"`{f}`" for f in mod["functions"])
        num_inv = len(invs)

        inv_sections = []
        for idx, inv in enumerate(invs, start=1):
            section = textwrap.dedent(f"""\
                ### Invariant {idx}: {inv['title']} (`{inv['id']}`)

                **Formal property**: {inv['formal']}

                **Hypothesis strategy hint**: `{inv['hypothesis_hint']}`

                **What to check**: {inv['check_desc']}
            """)
            inv_sections.append(section)

        invs_text = "\n".join(inv_sections)

        return textwrap.dedent(f"""\
            # TEST4: Property-Based Tests from Spec Invariants

            ## Context

            The `{mod['name']}` module provides {mod['description']}.
            It exposes the following functions: {func_list}.

            A correct implementation is provided in `module.py`.
            The module has been verified against its mathematical specification,
            but we need **property-based tests** to guard against future regressions.

            ## Your Task

            Write property-based tests in `tests/test_properties.py` using the
            **hypothesis** library. Each invariant below must have a corresponding
            test function decorated with `@given`.

            ## Invariants to Test (Seed {seed})

            {invs_text}

            ## Requirements

            - Use `hypothesis` with `@given` decorators (not just example-based tests).
            - Each of the {num_inv} invariants must have at least one dedicated test function.
            - All tests must pass on the provided `module.py`.
            - Each test must be sensitive enough to catch the corresponding mutant.
            - Test functions must begin with `test_`.

            ## Running Tests

            ```bash
            pip install hypothesis pytest
            python -m pytest tests/test_properties.py -v
            ```

            ## Deliverables

            - `tests/test_properties.py` with at least {num_inv} `@given` test functions.
            - Tests must run cleanly: `python -m pytest tests/test_properties.py`.

            ## Grading

            - **Check 1**: `tests/test_properties.py` exists.
            - **Check 2**: File imports from `hypothesis` (property-based approach used).
            - **Checks 3-{num_inv+2}**: Each invariant has a corresponding test that catches its mutant.
            - **Check {num_inv+3}**: All tests pass on correct `module.py`.
            - **Check {num_inv+4}**: Test function count >= {num_inv}.
            - **Check {num_inv+5}**: At least {num_inv-1} mutants are caught overall.
        """)

    def _generate_brief(self, mod: dict, invs: list[dict]) -> str:
        num_inv = len(invs)
        inv_list = "\n".join(f"  - {inv['title']}" for inv in invs)
        return textwrap.dedent(f"""\
            # TEST4: Property-Based Tests (Brief)

            The `{mod['name']}` module needs property-based tests to verify its correctness guarantees.

            Write `@given` hypothesis tests in `tests/test_properties.py` covering these invariants:
            {inv_list}

            - Run with: `python -m pytest tests/test_properties.py`
            - Use `hypothesis` library with `@given` decorators.
            - Each invariant must have at least one test function.
            - All tests must pass on the provided `module.py`.
        """)
