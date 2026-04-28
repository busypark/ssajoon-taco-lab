# TACO 데이터셋 기반 알고리즘 문제 변형 실험

> **브랜치**: `exp/testcase-classification`

## 실험 환경

- **컨테이너**: Docker (Linux)
- **런타임**: Jupyter Notebook (Python 3.11)
- **LLM**: Google Gemma 4 31B IT (`gemma-4-31b-it`) via Gemini API

## 환경 변수 설정

| 변수 | 사용 노트북 |
|---|---|
| `GEMINI_API_KEY` | `6) classfy testcases.ipynb` |

```bash
export GEMINI_API_KEY=AIzaSy...
```

## 노트북 목록

| 파일 | 설명 |
|---|---|
| `1) research full_dataset.ipynb` | TACO 전체 데이터셋 탐색 및 통계 분석 |
| `2) split 3 csv.ipynb` | TACO parquet → 3개 CSV 정규화 분리 |
| `3) validate testcases.ipynb` | 솔루션 코드 실제 실행 검증 |
| `4) validate testcases.ipynb` | 실행 결과 필터링 및 유효 문제 추출 |
| `5) filter validation.ipynb` | 테스트케이스 수 기준 문제 필터링 |
| `6) classfy testcases.ipynb` | 기존 TC 유형 분류 실험 (`exp/testcase-classification`) |
