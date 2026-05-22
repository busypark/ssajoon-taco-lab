# TACO 데이터셋 기반 알고리즘 문제 변형 실험

## 실험 환경

- **컨테이너**: Docker (Linux)
- **런타임**: Jupyter Notebook (Python 3.11)
- **LLM**: Google Gemma 4 31B IT (`gemma-4-31b-it`) via Gemini API

## 환경 변수 설정

### 단일 키

| 변수 | 사용 노트북 |
|---|---|
| `GEMINI_API_KEY` | `7) generate problems.ipynb`, `9) generate inputs.ipynb`, `10) classify algorithms.ipynb`, `11) classify by solution.ipynb`, `12) classify by solution.ipynb` |

```bash
export GEMINI_API_KEY=AIzaSy...
```

### 다중 키 (`16) testcase rangeVal.ipynb`)

멀티프로세스 구조로 API 키 17개를 큐로 분배합니다.

```bash
export GEMINI_API_KEY_1=AIzaSy...
export GEMINI_API_KEY_2=AIzaSy...
# ... (GEMINI_API_KEY_17까지)
```

## 노트북 목록

| 파일 | 설명 |
|---|---|
| `1) research full_dataset.ipynb` | TACO 전체 데이터셋 탐색 및 통계 분석 |
| `2) split 3 csv.ipynb` | TACO parquet → 3개 CSV 정규화 분리 |
| `3) validate testcases.ipynb` | 솔루션 코드 실제 실행 검증 |
| `4) validate testcases.ipynb` | 실행 결과 필터링 및 유효 문제 추출 |
| `5) filter validation.ipynb` | 테스트케이스 수 기준 문제 필터링 |
| `7) generate problems.ipynb` | SSAFY 테마 문제 변환 (Gemma) |
| `8) concat problems.ipynb` | 분산 변환 결과 합산 및 품질 검증 |
| `9) generate inputs.ipynb` | 합성 테스트케이스 50개 생성 (Gemma) |
| `10) classify algorithms.ipynb` | 문제 설명 기반 알고리즘 분류 |
| `11) classify by solution.ipynb` | 솔루션 코드 기반 알고리즘 분류 (분산 워커 A) |
| `12) classify by solution.ipynb` | 솔루션 코드 기반 알고리즘 분류 (분산 워커 B) |
| `13) concat cls by sol.ipynb` | 솔루션-알고리즘 분류 결과 합산 |
| `14) extract codeforces.ipynb` | codeforce 키워드 포함 문제 탐지 및 분리 |
| `15) overwrite, time, memory.ipynb` | 시간/메모리 제한 파싱 및 TC 전처리 |
| `16) testcase rangeVal.ipynb` | LLM 기반 TC 입력 범위 검증 |
