"""
codeforces-noImage-excludeUnder3Tags_with20Solutions.csv 를 prompt_v1.txt 규칙대로
gemma-4-31b-it (Google AI Studio, 다중 API 키 로테이션) 으로 분류해서
algorithm_solution_score_matrix.xlsx 양식(ALL_ALGORITHM_SCORE + BROAD_TAG_RECHECK_SCORE)으로 저장한다.

사용법:
  python classify_solutions.py --batch-size 1 --start-idx 1 --end-idx 33
  python classify_solutions.py --batch-size 2 --start-idx 1 --end-idx 33

같은 --batch-size 로 재실행하면 체크포인트 CSV에 이미 있는 problem_solution_key는 건너뛰고 이어서 진행한다.
"""

import argparse
import csv
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import openpyxl

import schema
import prompts
from gemini_client import KeyPool, call_gemini_json, load_keys

csv.field_size_limit(2**31 - 1)

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parent
DEFAULT_INPUT = PROJECT_DIR / "source" / "codeforces-noImage-excludeUnder3Tags_with20Solutions.csv"
DEFAULT_KEYS_FILE = PROJECT_DIR / "env" / "api keys.txt"
DEFAULT_OUTPUT_DIR = PROJECT_DIR / "output"


# ---------------------------------------------------------------------------
# 결정론적으로 계산 가능한 필드 (LLM에게 묻지 않음)
# ---------------------------------------------------------------------------

def detect_language(code: str) -> str:
    if "#include" in code or "using namespace std" in code:
        return "C++"
    if "public class" in code or "import java" in code:
        return "Java"
    if "def " in code or "import sys" in code or "print(" in code:
        return "Python"
    return "UNKNOWN"


def solution_length(code: str) -> int:
    return code.count("\n") + 1


def is_selected(solution_index: int, selected_submission_index: str) -> bool:
    try:
        return solution_index == int(selected_submission_index)
    except (TypeError, ValueError):
        return False


# ---------------------------------------------------------------------------
# CSV 로딩 / 청크 분할
# ---------------------------------------------------------------------------

def load_problems(csv_path: Path) -> list[dict]:
    with open(csv_path, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def valid_solutions(problem: dict) -> list[tuple[int, str]]:
    out = []
    for i in range(1, 21):
        code = (problem.get(f"solution_{i}") or "").strip()
        if code:
            out.append((i, code))
    return out


def make_chunks(solutions: list[tuple[int, str]], batch_size: int) -> list[list[tuple[int, str]]]:
    return [solutions[i:i + batch_size] for i in range(0, len(solutions), batch_size)]


# ---------------------------------------------------------------------------
# 응답 -> 시트 행 변환
# ---------------------------------------------------------------------------

def normalize_algo_scores(raw: dict) -> dict:
    """LLM이 준 120개 태그 점수를 158컬럼 스키마(중복 태그 포함)에 매핑."""
    scores = {}
    for tag in schema.ALGO_TAGS:  # 122개, HEAP_GREEDY/BITMASK_DP 중복 포함
        try:
            scores[tag] = int(raw.get(tag, 0))
        except (TypeError, ValueError):
            scores[tag] = 0
    return scores


def build_score_row(problem: dict, solution_index: int, code: str, sol: dict) -> dict:
    key = f"{problem['id']}_solution_{solution_index}"
    row = {
        "problem_solution_key": key,
        "no": problem["no"], "source": problem["source"], "id": problem["id"],
        "title": problem["title"], "rating": problem["rating"], "difficulty": problem["difficulty"],
        "official_tags": problem["official_tags"], "time_limit_ms": problem["time_limit_ms"],
        "memory_limit_mb": problem["memory_limit_mb"], "testcase_count": problem["testcase_count"],
        "checker_status": problem["checker_status"], "selected_language": problem["selected_language"],
        "selected_submission_index": problem["selected_submission_index"],
        "description": problem["description"], "source_url": problem["source_url"],
        "solution_column": f"solution_{solution_index}", "solution_index": solution_index,
        "is_selected_solution": is_selected(solution_index, problem["selected_submission_index"]),
        "solution_valid": True,
        "solution_language": detect_language(code),
        "solution_length": solution_length(code),
        "solution_summary": sol.get("solution_summary", ""),
        "primary_algorithm": sol.get("primary_algorithm", "UNKNOWN"),
        "primary_score": normalize_algo_scores(sol.get("algorithm_scores", {})).get(sol.get("primary_algorithm", ""), 0),
        "secondary_algorithms": " | ".join(sol.get("secondary_algorithms", []) or []),
        "is_composite": sol.get("is_composite", False),
        "composite_algorithm": " | ".join(sol.get("composite_algorithm", []) or []) or "NONE",
        "top_3_algorithms": " | ".join(
            f"{t.get('tag')}:{t.get('score')}" for t in (sol.get("top_3_algorithms") or [])
        ),
        "code_evidence": sol.get("code_evidence", ""),
        "time_complexity_reasoning": sol.get("time_complexity_reasoning", ""),
        "classification_reason": sol.get("classification_reason", ""),
        "rejected_candidates": sol.get("rejected_candidates", ""),
        "confidence": sol.get("confidence", "LOW"),
        "uncertain_points": sol.get("uncertain_points", ""),
        "compared_with_other_solutions": sol.get("compared_with_other_solutions", ""),
    }
    row.update(normalize_algo_scores(sol.get("algorithm_scores", {})))
    return row


def build_recheck_rows(problem: dict, solution_index: int, sol: dict) -> list[dict]:
    algo_scores = normalize_algo_scores(sol.get("algorithm_scores", {}))
    primary = sol.get("primary_algorithm", "")
    key = f"{problem['id']}_solution_{solution_index}"
    rows = []
    field_map = {"GREEDY": "greedy_recheck", "DP": "dp_recheck", "BITMASK": "bitmask_recheck", "MATH": "math_recheck"}

    for broad_tag in schema.BROAD_TAGS:
        broad_score = algo_scores.get(broad_tag, 0)
        qualifies = (primary == broad_tag) or (broad_score >= 60)
        if not qualifies:
            continue

        recheck = sol.get(field_map[broad_tag]) or {}
        candidate_scores = recheck.get("candidate_scores", {}) or {}
        best_candidate, best_score = None, -1
        for c in schema.BROAD_TAG_CANDIDATES[broad_tag]:
            try:
                v = int(candidate_scores.get(c, 0))
            except (TypeError, ValueError):
                v = 0
            if v > best_score:
                best_candidate, best_score = c, v

        row = {
            "problem_solution_key": key, "id": problem["id"], "title": problem["title"],
            "solution_column": f"solution_{solution_index}", "solution_index": solution_index,
            "source_broad_tag": broad_tag, "source_broad_score": broad_score,
            "recheck_best_candidate": best_candidate, "recheck_best_score": max(best_score, 0),
            "recheck_decision": recheck.get("recheck_decision", "KEEP_ORIGINAL"),
            "recheck_reason": recheck.get("recheck_reason", ""),
        }
        for c in schema.RECHECK_CANDIDATE_UNION:
            row[c] = candidate_scores.get(c, "") if c in schema.BROAD_TAG_CANDIDATES[broad_tag] else ""
        rows.append(row)

    return rows


# ---------------------------------------------------------------------------
# 체크포인트 CSV
# ---------------------------------------------------------------------------

class Checkpoint:
    def __init__(self, score_path: Path, recheck_path: Path):
        self.score_path = score_path
        self.recheck_path = recheck_path
        self._lock = __import__("threading").Lock()
        self.done_keys: set[str] = set()
        if score_path.exists():
            with open(score_path, encoding="utf-8-sig", newline="") as f:
                for r in csv.DictReader(f):
                    self.done_keys.add(r["problem_solution_key"])
        self._ensure_header(score_path, schema.ALL_SCORE_COLUMNS)
        self._ensure_header(recheck_path, schema.RECHECK_COLUMNS)

    @staticmethod
    def _ensure_header(path: Path, columns: list[str]):
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, "w", encoding="utf-8-sig", newline="") as f:
                csv.DictWriter(f, fieldnames=columns).writeheader()

    def is_done(self, key: str) -> bool:
        return key in self.done_keys

    def append(self, score_rows: list[dict], recheck_rows: list[dict]):
        with self._lock:
            with open(self.score_path, "a", encoding="utf-8-sig", newline="") as f:
                w = csv.DictWriter(f, fieldnames=schema.ALL_SCORE_COLUMNS)
                for row in score_rows:
                    w.writerow(row)
                    self.done_keys.add(row["problem_solution_key"])
            if recheck_rows:
                with open(self.recheck_path, "a", encoding="utf-8-sig", newline="") as f:
                    w = csv.DictWriter(f, fieldnames=schema.RECHECK_COLUMNS)
                    for row in recheck_rows:
                        w.writerow(row)


# ---------------------------------------------------------------------------
# 청크 처리
# ---------------------------------------------------------------------------

def process_chunk(problem: dict, chunk: list[tuple[int, str]], pool: KeyPool):
    user_prompt = prompts.build_user_prompt(problem, chunk)
    data, meta = call_gemini_json(pool, prompts.SYSTEM_INSTRUCTION, user_prompt)

    result = {
        "problem_id": problem["id"], "solution_indices": [i for i, _ in chunk],
        "elapsed_s": round(meta["elapsed_s"], 1), "attempts": meta["attempts"],
        "ok": data is not None, "error": meta["error"],
    }

    if data is None:
        return [], [], result

    if len(chunk) == 1:
        sols = [data]
    else:
        sols = data.get("solutions", [])

    score_rows, recheck_rows = [], []
    code_by_index = dict(chunk)
    for sol in sols:
        try:
            idx = int(sol.get("solution_index"))
        except (TypeError, ValueError):
            continue
        if idx not in code_by_index:
            continue
        score_rows.append(build_score_row(problem, idx, code_by_index[idx], sol))
        recheck_rows.extend(build_recheck_rows(problem, idx, sol))

    result["ok"] = result["ok"] and len(score_rows) == len(chunk)
    if len(score_rows) != len(chunk):
        result["error"] = (result["error"] or "") + f" | parsed {len(score_rows)}/{len(chunk)} solutions"

    return score_rows, recheck_rows, result


# ---------------------------------------------------------------------------
# xlsx 조립
# ---------------------------------------------------------------------------

def assemble_xlsx(score_csv: Path, recheck_csv: Path, out_path: Path):
    wb = openpyxl.Workbook()
    ws1 = wb.active
    ws1.title = "ALL_ALGORITHM_SCORE"
    ws1.append(schema.ALL_SCORE_COLUMNS)
    with open(score_csv, encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            ws1.append([row.get(c, "") for c in schema.ALL_SCORE_COLUMNS])

    ws2 = wb.create_sheet("BROAD_TAG_RECHECK_SCORE")
    ws2.append(schema.RECHECK_COLUMNS)
    if recheck_csv.exists():
        with open(recheck_csv, encoding="utf-8-sig", newline="") as f:
            for row in csv.DictReader(f):
                ws2.append([row.get(c, "") for c in schema.RECHECK_COLUMNS])

    out_path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(out_path)


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--batch-size", type=int, choices=[1, 2], required=True)
    ap.add_argument("--start-idx", type=int, default=1, help="problems.csv 위에서부터 1-based 시작 위치")
    ap.add_argument("--end-idx", type=int, default=None, help="problems.csv 위에서부터 1-based 끝 위치(포함)")
    ap.add_argument("--workers", type=int, default=9)
    ap.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    ap.add_argument("--keys-file", type=Path, default=DEFAULT_KEYS_FILE)
    ap.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = ap.parse_args()

    problems = load_problems(args.input)
    end_idx = args.end_idx or len(problems)
    problems = problems[args.start_idx - 1:end_idx]

    keys = load_keys(str(args.keys_file))
    pool = KeyPool(keys)

    tag = f"batch{args.batch_size}"
    ckpt = Checkpoint(
        args.output_dir / f"{tag}_score.csv",
        args.output_dir / f"{tag}_recheck.csv",
    )

    all_chunks = []
    for problem in problems:
        sols = valid_solutions(problem)
        for chunk in make_chunks(sols, args.batch_size):
            key0 = f"{problem['id']}_solution_{chunk[0][0]}"
            if ckpt.is_done(key0):
                continue
            all_chunks.append((problem, chunk))

    total = len(all_chunks)
    print(json.dumps({"event": "start", "batch_size": args.batch_size, "total_chunks": total,
                       "n_problems": len(problems), "workers": args.workers}), flush=True)

    if total == 0:
        print(json.dumps({"event": "done", "reason": "nothing_to_do"}), flush=True)
        assemble_xlsx(ckpt.score_path, ckpt.recheck_path,
                      args.output_dir / f"algorithm_solution_score_matrix.{tag}.xlsx")
        return

    done_count = 0
    ok_count = 0
    t0 = time.time()

    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futures = {ex.submit(process_chunk, problem, chunk, pool): (problem, chunk)
                   for problem, chunk in all_chunks}
        for fut in as_completed(futures):
            score_rows, recheck_rows, result = fut.result()
            ckpt.append(score_rows, recheck_rows)
            done_count += 1
            ok_count += 1 if result["ok"] else 0
            elapsed_total = round(time.time() - t0, 1)
            print(json.dumps({
                "event": "chunk_done", "problem_id": result["problem_id"],
                "solution_indices": result["solution_indices"], "ok": result["ok"],
                "error": result["error"], "attempts": result["attempts"],
                "call_elapsed_s": result["elapsed_s"],
                "progress": f"{done_count}/{total}", "ok_so_far": f"{ok_count}/{done_count}",
                "total_elapsed_s": elapsed_total,
            }), flush=True)

    assemble_xlsx(ckpt.score_path, ckpt.recheck_path,
                  args.output_dir / f"algorithm_solution_score_matrix.{tag}.xlsx")
    print(json.dumps({"event": "done", "total": total, "ok": ok_count,
                       "total_elapsed_s": round(time.time() - t0, 1)}), flush=True)


if __name__ == "__main__":
    main()
