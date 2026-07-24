"""
source/algorithm_solution_score_matrix.xlsx 의 실제 헤더에서 그대로 뽑아낸 컬럼 순서/태그 목록.
prompt_v1.txt 6-2, 7-1 절의 스펙과 동일하되, 실제 xlsx 템플릿이 진짜 출력 양식이므로 이쪽을 기준으로 삼는다.

주의: ALGO_TAGS 에는 HEAP_GREEDY, BITMASK_DP 가 각각 "섹션"이 달라 두 번 등장한다
(원본 prompt_v1.txt 6-2절 목록 자체의 중복이며, xlsx 템플릿도 158컬럼 중 실질 태그는 120개뿐이다).
JSON 키는 중복될 수 없으므로 LLM에게는 DEDUPED_ALGO_TAGS(120개)로만 점수를 요청하고,
xlsx로 쓸 때 두 컬럼 모두에 같은 값을 채운다.
"""

BASE_INFO_COLS = [
    "problem_solution_key", "no", "source", "id", "title", "rating", "difficulty",
    "official_tags", "time_limit_ms", "memory_limit_mb", "testcase_count",
    "checker_status", "selected_language", "selected_submission_index",
    "description", "source_url",
]

SOLUTION_ID_COLS = [
    "solution_column", "solution_index", "is_selected_solution", "solution_valid",
    "solution_language", "solution_length", "solution_summary",
]

ALGO_TAGS = [
    'IMPLEMENTATION', 'SIMULATION', 'GRID_SIMULATION', 'EVENT_SIMULATION', 'STATE_SIMULATION',
    'BRUTE_FORCE', 'BACKTRACKING', 'PERMUTATION_SEARCH', 'COMBINATION_SEARCH', 'BRANCH_AND_BOUND',
    'SORTING', 'CUSTOM_SORTING', 'COUNTING_SORT',
    'BINARY_SEARCH', 'PARAMETRIC_SEARCH', 'BOUND_SEARCH',
    'TWO_POINTERS', 'SLIDING_WINDOW', 'FIXED_WINDOW', 'VARIABLE_WINDOW',
    'PREFIX_SUM', 'PREFIX_SUM_2D', 'DIFFERENCE_ARRAY', 'IMOS',
    'HASH', 'HASH_MAP', 'HASH_SET', 'STRING_HASHING',
    'STACK', 'MONOTONIC_STACK', 'QUEUE', 'DEQUE', 'MONOTONIC_QUEUE',
    'HEAP', 'PRIORITY_QUEUE', 'HEAP_GREEDY',
    'BFS', 'DFS', 'GRAPH_TRAVERSAL', 'GRID_TRAVERSAL', 'FLOOD_FILL', 'CONNECTED_COMPONENTS',
    'MULTI_SOURCE_BFS', 'STATE_SPACE_SEARCH',
    'DIJKSTRA', 'BELLMAN_FORD', 'FLOYD_WARSHALL', 'ZERO_ONE_BFS', 'SHORTEST_PATH_DAG',
    'UNION_FIND', 'MST', 'KRUSKAL', 'PRIM',
    'TOPO_SORT', 'TOPO_SORT_DP',
    'DP', 'DP_1D', 'DP_2D', 'GRID_DP', 'KNAPSACK_DP', 'INTERVAL_DP', 'BITMASK_DP', 'TREE_DP',
    'DP_ON_DAG', 'DIGIT_DP', 'LIS', 'LCS', 'EDIT_DISTANCE',
    'GREEDY', 'SORTING_GREEDY', 'HEAP_GREEDY', 'INTERVAL_GREEDY',
    'TREE', 'TREE_TRAVERSAL', 'LCA', 'EULER_TOUR', 'TREE_DIAMETER', 'SUBTREE_QUERY',
    'SEGMENT_TREE', 'LAZY_SEGMENT_TREE', 'FENWICK_TREE', 'RANGE_SUM_QUERY', 'RANGE_MIN_QUERY',
    'COORD_COMP_SEGMENT', 'DYNAMIC_SEGMENT_TREE',
    'TRIE', 'BINARY_TRIE',
    'STRING', 'KMP', 'PALINDROME', 'MANACHER', 'AHO_CORASICK',
    'MATH', 'NUMBER_THEORY', 'GCD_LCM', 'PRIME_CHECK', 'SIEVE', 'MODULAR_ARITHMETIC',
    'FAST_POWER', 'MODULAR_INVERSE', 'COMBINATORICS', 'INCLUSION_EXCLUSION',
    'PROBABILITY', 'EXPECTED_VALUE', 'GAME_THEORY',
    'GEOMETRY', 'CCW', 'LINE_SEGMENT_INTERSECTION', 'CONVEX_HULL', 'POLYGON_AREA',
    'BITMASK', 'BITMASK_BRUTE_FORCE', 'BITMASK_DP', 'BIT_MANIPULATION', 'SUBSET_ENUMERATION',
    'DIVIDE_AND_CONQUER', 'SWEEP_LINE', 'COORDINATE_COMPRESSION', 'OFFLINE_QUERY',
    'MEET_IN_THE_MIDDLE', 'SPARSE_TABLE',
    'UNKNOWN',
]
assert len(ALGO_TAGS) == 122

# JSON 키 중복 방지용 목록 (LLM에게 실제로 요청하는 태그 집합)
DEDUPED_ALGO_TAGS = list(dict.fromkeys(ALGO_TAGS))
assert len(DEDUPED_ALGO_TAGS) == 120

SUMMARY_COLS = [
    "primary_algorithm", "primary_score", "secondary_algorithms", "is_composite",
    "composite_algorithm", "top_3_algorithms", "code_evidence", "time_complexity_reasoning",
    "classification_reason", "rejected_candidates", "confidence", "uncertain_points",
    "compared_with_other_solutions",
]

ALL_SCORE_COLUMNS = (
    ["problem_solution_key"] + BASE_INFO_COLS[1:] + SOLUTION_ID_COLS + ALGO_TAGS + SUMMARY_COLS
)
assert len(ALL_SCORE_COLUMNS) == 158

RECHECK_BASE_COLS = [
    "problem_solution_key", "id", "title", "solution_column", "solution_index",
    "source_broad_tag", "source_broad_score",
]

RECHECK_CANDIDATE_UNION = [
    'BACKTRACKING', 'BFS', 'BINARY_SEARCH', 'BITMASK', 'BRUTE_FORCE', 'COMBINATORICS',
    'DFS', 'DIJKSTRA', 'DP', 'FENWICK_TREE', 'GCD_LCM', 'GEOMETRY', 'GRAPH', 'GREEDY',
    'MATH', 'MODULAR_ARITHMETIC', 'PARAMETRIC_SEARCH', 'PREFIX_SUM', 'PRIORITY_QUEUE',
    'SEGMENT_TREE', 'SIEVE', 'SIMULATION', 'SORTING', 'STACK', 'TOPO_SORT', 'TREE',
    'TWO_POINTERS', 'UNION_FIND',
]
assert len(RECHECK_CANDIDATE_UNION) == 28

RECHECK_SUMMARY_COLS = ["recheck_best_candidate", "recheck_best_score", "recheck_decision", "recheck_reason"]

RECHECK_COLUMNS = RECHECK_BASE_COLS + RECHECK_CANDIDATE_UNION + RECHECK_SUMMARY_COLS
assert len(RECHECK_COLUMNS) == 39

# prompt_v1.txt 8~11절: 넓은 태그별 재검증 후보 (순서는 prompt_v1.txt 그대로)
BROAD_TAG_CANDIDATES = {
    "GREEDY": ["SORTING", "PRIORITY_QUEUE", "SEGMENT_TREE", "FENWICK_TREE", "UNION_FIND",
               "BINARY_SEARCH", "PARAMETRIC_SEARCH", "TWO_POINTERS", "STACK", "DP", "GRAPH"],
    "DP": ["PREFIX_SUM", "BFS", "DFS", "DIJKSTRA", "SEGMENT_TREE", "FENWICK_TREE",
           "BINARY_SEARCH", "GREEDY", "TOPO_SORT", "TREE", "BITMASK"],
    "BITMASK": ["BRUTE_FORCE", "BACKTRACKING", "DP", "BFS", "DFS", "SIMULATION", "MATH"],
    "MATH": ["GCD_LCM", "SIEVE", "COMBINATORICS", "MODULAR_ARITHMETIC", "BINARY_SEARCH",
             "PARAMETRIC_SEARCH", "GEOMETRY", "GREEDY", "DP", "BRUTE_FORCE"],
}
BROAD_TAGS = list(BROAD_TAG_CANDIDATES.keys())  # GREEDY, DP, BITMASK, MATH

RECHECK_DECISIONS = ["KEEP_ORIGINAL", "REVIEW_NEEDED", "LIKELY_SPECIFIC_ALGORITHM"]
CONFIDENCE_LEVELS = ["HIGH", "MEDIUM", "LOW"]


def build_response_schema(n_solutions: int) -> dict:
    """batch 안에 담긴 n_solutions개 solution 각각에 대한 구조화 출력 JSON Schema (google-genai response_schema용)."""

    algo_score_props = {tag: {"type": "INTEGER", "minimum": 0, "maximum": 100} for tag in DEDUPED_ALGO_TAGS}

    def recheck_block_schema(broad_tag: str) -> dict:
        cand_props = {c: {"type": "INTEGER", "minimum": 0, "maximum": 100}
                      for c in BROAD_TAG_CANDIDATES[broad_tag]}
        return {
            "type": "OBJECT",
            "properties": {
                "candidate_scores": {"type": "OBJECT", "properties": cand_props, "required": list(cand_props)},
                "recheck_decision": {"type": "STRING", "enum": RECHECK_DECISIONS},
                "recheck_reason": {"type": "STRING"},
            },
            "required": ["candidate_scores", "recheck_decision", "recheck_reason"],
        }

    top3_item_schema = {
        "type": "OBJECT",
        "properties": {
            "tag": {"type": "STRING", "enum": DEDUPED_ALGO_TAGS},
            "score": {"type": "INTEGER", "minimum": 0, "maximum": 100},
        },
        "required": ["tag", "score"],
    }

    solution_schema = {
        "type": "OBJECT",
        "properties": {
            "solution_index": {"type": "INTEGER", "description": "이 결과가 어느 solution_N에 대한 것인지 (프롬프트에서 제공한 번호와 동일해야 함)"},
            "solution_summary": {"type": "STRING"},
            "algorithm_scores": {"type": "OBJECT", "properties": algo_score_props, "required": list(algo_score_props)},
            "primary_algorithm": {"type": "STRING", "enum": DEDUPED_ALGO_TAGS},
            "secondary_algorithms": {"type": "ARRAY", "items": {"type": "STRING", "enum": DEDUPED_ALGO_TAGS}},
            "is_composite": {"type": "BOOLEAN"},
            "composite_algorithm": {"type": "ARRAY", "items": {"type": "STRING", "enum": DEDUPED_ALGO_TAGS},
                                     "description": "복합 알고리즘이면 핵심 조합 2개, 아니면 빈 배열"},
            "top_3_algorithms": {"type": "ARRAY", "items": top3_item_schema, "minItems": 3, "maxItems": 3},
            "code_evidence": {"type": "STRING"},
            "time_complexity_reasoning": {"type": "STRING"},
            "classification_reason": {"type": "STRING"},
            "rejected_candidates": {"type": "STRING"},
            "confidence": {"type": "STRING", "enum": CONFIDENCE_LEVELS},
            "uncertain_points": {"type": "STRING"},
            "compared_with_other_solutions": {"type": "STRING"},
            "greedy_recheck": recheck_block_schema("GREEDY"),
            "dp_recheck": recheck_block_schema("DP"),
            "bitmask_recheck": recheck_block_schema("BITMASK"),
            "math_recheck": recheck_block_schema("MATH"),
        },
        "required": [
            "solution_index", "solution_summary", "algorithm_scores", "primary_algorithm",
            "secondary_algorithms", "is_composite", "composite_algorithm", "top_3_algorithms",
            "code_evidence", "time_complexity_reasoning", "classification_reason",
            "rejected_candidates", "confidence", "uncertain_points", "compared_with_other_solutions",
            "greedy_recheck", "dp_recheck", "bitmask_recheck", "math_recheck",
        ],
    }

    return {
        "type": "OBJECT",
        "properties": {
            "solutions": {"type": "ARRAY", "items": solution_schema, "minItems": n_solutions, "maxItems": n_solutions},
        },
        "required": ["solutions"],
    }
