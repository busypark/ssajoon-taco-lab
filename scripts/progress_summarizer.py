"""stdin으로 classify_solutions.py의 JSON 라인 로그를 받아서,
chunk_done 이벤트 N개가 쌓일 때마다 요약 1줄을 stdout에 찍는다 (Monitor용).
done/에러(Traceback 등)는 즉시 그대로 통과시킨다.

사용법: tail -f -n +1 <log> | python progress_summarizer.py --every 10
"""
import argparse
import json
import sys

ap = argparse.ArgumentParser()
ap.add_argument("--every", type=int, default=10)
args = ap.parse_args()

buf = []
for line in sys.stdin:
    line = line.rstrip("\n")
    if not line:
        continue

    try:
        data = json.loads(line)
    except json.JSONDecodeError:
        # Traceback 등 JSON이 아닌 줄은 즉시 통과
        print(line, flush=True)
        continue

    event = data.get("event")

    if event == "chunk_done":
        buf.append(data)
        if len(buf) >= args.every:
            ok_n = sum(1 for d in buf if d["ok"])
            avg_s = sum(d["call_elapsed_s"] for d in buf) / len(buf)
            last = buf[-1]
            fails = [d for d in buf if not d["ok"]]
            fail_str = "" if not fails else " | fails: " + ", ".join(
                f"{d['problem_id']}#{d['solution_indices']}" for d in fails
            )
            print(
                f"progress {last['progress']} | last {len(buf)}: {ok_n}/{len(buf)} ok, "
                f"avg {avg_s:.0f}s/call | overall {last['ok_so_far']} | "
                f"elapsed {last['total_elapsed_s']/60:.1f}min{fail_str}",
                flush=True,
            )
            buf = []
    elif event == "done":
        print(f"DONE: {json.dumps(data, ensure_ascii=False)}", flush=True)
    elif event == "start":
        print(f"START: {json.dumps(data, ensure_ascii=False)}", flush=True)
    else:
        print(line, flush=True)
