"""old/16) testcase rangeVal.ipynb 의 멀티키 큐 + 쿨다운 패턴을 재사용하되,
API 호출이 I/O-bound(콜 1회 ~85초, 대부분 네트워크/생성 대기)라
ProcessPoolExecutor 대신 ThreadPoolExecutor + queue.Queue 키 풀로 단순화했다.
(Windows에서 멀티프로세스로 google.genai 클라이언트를 pickling하는 오버헤드/불안정성을 피하기 위함.
문제가 생기면 여기만 ProcessPoolExecutor로 되돌리면 된다.)
"""

import json
import queue
import re
import threading
import time

from google import genai
from google.genai import types

MAX_RETRIES = 3
RETRY_DELAY_S = 5
KEY_WAIT_TIMEOUT_S = 30
KEY_COOLDOWN_S = 20
MODEL_NAME = "gemma-4-31b-it"

_JSON_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)


def load_keys(keys_file: str) -> list[str]:
    with open(keys_file, encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]


class KeyPool:
    def __init__(self, keys: list[str]):
        self._queue: queue.Queue[str] = queue.Queue()
        for k in keys:
            self._queue.put(k)
        self._lock = threading.Lock()
        self._clients: dict[str, genai.Client] = {}

    def _client_for(self, key: str) -> genai.Client:
        with self._lock:
            if key not in self._clients:
                self._clients[key] = genai.Client(api_key=key)
            return self._clients[key]

    def acquire(self, timeout_s: float = KEY_WAIT_TIMEOUT_S) -> tuple[str, genai.Client] | None:
        try:
            key = self._queue.get(timeout=timeout_s)
        except queue.Empty:
            return None
        return key, self._client_for(key)

    def release(self, key: str, cooldown_s: float = 0.0):
        if cooldown_s > 0:
            threading.Timer(cooldown_s, self._queue.put, args=(key,)).start()
        else:
            self._queue.put(key)


def _strip_json_fence(text: str) -> str:
    return _JSON_FENCE_RE.sub("", text.strip())


def call_gemini_json(pool: KeyPool, system_instruction: str, user_prompt: str,
                      max_retries: int = MAX_RETRIES) -> tuple[dict | None, dict]:
    """반환: (parsed_json_or_None, meta) — meta에는 attempts, elapsed_s, error 등 기록."""
    meta = {"attempts": 0, "elapsed_s": 0.0, "error": None}
    t_start = time.time()

    for attempt in range(1, max_retries + 1):
        meta["attempts"] = attempt
        acquired = pool.acquire()
        if acquired is None:
            meta["error"] = "KEY_WAIT_TIMEOUT"
            time.sleep(RETRY_DELAY_S)
            continue
        key, client = acquired

        try:
            resp = client.models.generate_content(
                model=MODEL_NAME,
                contents=user_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    response_mime_type="application/json",
                ),
            )
            pool.release(key)
            text = _strip_json_fence(resp.text or "")
            data = json.loads(text)
            meta["elapsed_s"] = time.time() - t_start
            meta["error"] = None
            return data, meta

        except json.JSONDecodeError as e:
            pool.release(key)
            meta["error"] = f"JSON_DECODE_ERROR: {e}"
            time.sleep(RETRY_DELAY_S)
            continue

        except Exception as e:
            msg = str(e)
            is_rate_limit = "RESOURCE_EXHAUSTED" in msg or "429" in msg or "quota" in msg.lower()
            pool.release(key, cooldown_s=KEY_COOLDOWN_S if is_rate_limit else 0.0)
            meta["error"] = f"{type(e).__name__}: {msg[:300]}"
            time.sleep(RETRY_DELAY_S)
            continue

    meta["elapsed_s"] = time.time() - t_start
    return None, meta
