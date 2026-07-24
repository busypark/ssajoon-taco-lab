"""prompt_v1.txt의 판정 규칙(6~24절: 점수 기준, 재검증 규칙, 코드 분석 우선순위, 세부 판정 규칙)을
그대로 system_instruction으로 재사용하고, 실제 호출 단위(batch: solution 1~2개)에 맞는
JSON 출력 형식 지시만 매 호출 프롬프트에 새로 붙인다.

response_schema(구조화 출력)는 이 모델/스키마 조합에서 property 110~114개를 넘기면
400 INVALID_ARGUMENT 로 거부되는 것을 스모크 테스트로 확인했음 (algorithm_scores만 120개).
그래서 response_mime_type="application/json" 로 JSON 모드는 켜되, response_schema는 쓰지 않고
프롬프트 텍스트로 정확한 형식을 지시한 뒤 파싱 시점에 검증/재시도한다 (old 11·16번 노트북과 동일 패턴).
"""

from pathlib import Path
import schema

_PROMPT_V1_PATH = Path(__file__).resolve().parent.parent / "prompt" / "prompt_v1.txt"
PROMPT_V1_TEXT = _PROMPT_V1_PATH.read_text(encoding="utf-8")

SYSTEM_INSTRUCTION = f"""{PROMPT_V1_TEXT}

---

# 실제 호출 방식에 대한 보충 지시

너는 지금부터 위 규칙을 지키되, 문제 하나의 solution 전체를 한 번에 받는 게 아니라
API 호출 1번마다 같은 문제의 solution 중 일부(1~2개)만 전달받는다.

- 각 호출에서 주어진 solution만 분석한다. 주어지지 않은 다른 solution의 내용을 추측하지 않는다.
- `compared_with_other_solutions` 는 이번 호출에 함께 주어진 solution들끼리만 비교한다.
  이번 호출에 solution이 1개뿐이면 "다른 solution과 비교 불가 (이번 호출 단위가 1개)"라고 적는다.
- 출력은 순수 JSON 객체 하나다. 마크다운 코드블록(```), 설명 텍스트, 주석을 절대 포함하지 않는다.
- `algorithm_scores` 객체에는 아래 태그를 전부 정수 0~100 점으로 채워야 한다 (하나도 빠짐없이, 추가 태그 금지).
- `greedy_recheck` / `dp_recheck` / `bitmask_recheck` / `math_recheck` 는 실제로 해당 넓은 태그가
  주요 후보였는지와 무관하게 항상 스펙대로 채운다. (해당 solution의 BROAD_TAG_RECHECK_SCORE 포함 여부는
  후처리에서 별도로 판단한다.)
"""

_TAGS_BLOCK = ", ".join(schema.DEDUPED_ALGO_TAGS)


def _recheck_json_snippet(broad_tag: str) -> str:
    candidates = schema.BROAD_TAG_CANDIDATES[broad_tag]
    cand_json = ", ".join(f'"{c}": 0~100' for c in candidates)
    return (
        f'{{"candidate_scores": {{{cand_json}}}, '
        f'"recheck_decision": "KEEP_ORIGINAL|REVIEW_NEEDED|LIKELY_SPECIFIC_ALGORITHM", '
        f'"recheck_reason": "..."}}'
    )


_OUTPUT_FORMAT_ONE = f"""
출력 JSON 형식 (solution 1개 분석 결과):
{{
  "solution_index": <int>,
  "solution_summary": "<한 문장 요약>",
  "algorithm_scores": {{ "<태그명>": 0~100, ... 아래 태그 전부 포함 ... }},
  "primary_algorithm": "<태그명 1개>",
  "secondary_algorithms": ["<태그명>", ...],
  "is_composite": true|false,
  "composite_algorithm": ["<태그명>", "<태그명>"] 또는 [],
  "top_3_algorithms": [{{"tag": "<태그명>", "score": 0~100}}, ... 정확히 3개],
  "code_evidence": "...",
  "time_complexity_reasoning": "...",
  "classification_reason": "...",
  "rejected_candidates": "...",
  "confidence": "HIGH|MEDIUM|LOW",
  "uncertain_points": "...",
  "compared_with_other_solutions": "...",
  "greedy_recheck": {_recheck_json_snippet("GREEDY")},
  "dp_recheck": {_recheck_json_snippet("DP")},
  "bitmask_recheck": {_recheck_json_snippet("BITMASK")},
  "math_recheck": {_recheck_json_snippet("MATH")}
}}

algorithm_scores 에 반드시 포함해야 하는 태그 전체 목록 ({len(schema.DEDUPED_ALGO_TAGS)}개):
{_TAGS_BLOCK}
"""


def build_user_prompt(problem: dict, chunk: list[tuple[int, str]]) -> str:
    """chunk: [(solution_index, code), ...] (같은 문제 내 1~2개)"""
    header = f"""
[문제 정보]
id: {problem['id']}
title: {problem['title']}
official_tags (참고용, 그대로 복사 금지): {problem['official_tags']}
difficulty/rating: {problem['difficulty']} / {problem['rating']}
time_limit_ms: {problem['time_limit_ms']}
memory_limit_mb: {problem['memory_limit_mb']}

[문제 설명]
{problem['description']}
"""

    solutions_block = "\n".join(
        f"\n--- solution_{idx} ---\n```\n{code}\n```\n" for idx, code in chunk
    )

    if len(chunk) == 1:
        instruction = (
            "\n[요청]\n이번 호출에는 solution 1개만 주어진다. 위 solution에 대한 분석 결과를 "
            "다음 JSON 형식 그대로 단일 객체로 출력해라 (배열 아님).\n" + _OUTPUT_FORMAT_ONE
        )
    else:
        indices = ", ".join(f"solution_{i}" for i, _ in chunk)
        instruction = f"""
[요청]
이번 호출에는 같은 문제의 solution {len(chunk)}개({indices})가 함께 주어진다.
각 solution마다 독립적으로 분석하되, compared_with_other_solutions 에는 이번에 함께 주어진
solution들끼리 비교한 내용을 적어라.

출력은 다음 JSON 형식이다:
{{ "solutions": [ <solution 1개당 아래 형식 객체>, ... 정확히 {len(chunk)}개 ] }}

solution 1개당 형식:
{_OUTPUT_FORMAT_ONE}
"""

    return header + solutions_block + instruction
