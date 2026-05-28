# Backend README

설문 저장, 응답 로그 feature 계산, 문항 평가를 제공하는 FastAPI 백엔드입니다.

## 목차

- [프로젝트 소개](#프로젝트-소개)
- [주요 기능](#주요-기능)
- [기술 스택](#기술-스택)
- [빠른 시작](#빠른-시작)
- [폴더 구조](#폴더-구조)
- [핵심 로직](#핵심-로직)
- [데이터 모델](#데이터-모델)
- [핵심 API](#핵심-api)
- [환경 변수](#환경-변수)
- [배포](#배포)

## 프로젝트 소개

백엔드는 설문 도메인의 전체 서버 로직을 담당합니다.

- 설문/문항/옵션 관리
- 응답 및 응답 로그 저장
- 로그 기반 feature 계산 및 신뢰도 산출
- 품질/구성도/통계 평가 API 제공
- CSV 다운로드 API 제공

## 주요 기능

| 기능 | 설명 |
| --- | --- |
| 설문 CRUD | 설문 생성/수정/복제/삭제 |
| 공개 응답 | 공개 링크, 1회용 링크, 디바이스 중복 방지 |
| 응답 처리 | 응답/로그 저장, 파생 feature 계산 |
| 품질 평가 | 사전 규칙 + LLM 기반 문항 품질 판별 |
| 구성도 평가 | 임베딩/LLM 기반 구성도 평가 |
| 통계 평가 | 문항 통계값 계산 및 집계 |

## 기술 스택

| 영역 | 기술 |
| --- | --- |
| API | FastAPI, Uvicorn |
| ORM | SQLAlchemy |
| Validation | Pydantic |
| DB | SQLite |
| AI | OpenAI API |

## 빠른 시작

### 사전 요구사항

- Python 3.11+

### 설치 및 실행

```bash
cd backend
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
copy survey\backend\.env.example survey\backend\.env
cd survey\backend
..\..\.venv\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8010
```

확인 URL:

- Health: `http://127.0.0.1:8010/health`
- Swagger: `http://127.0.0.1:8010/docs`

## 폴더 구조

```text
backend/
├─ requirements.txt
└─ survey/backend/
   ├─ main.py                     # FastAPI 앱, CORS, 헬스체크
   ├─ database.py                 # DB 엔진/세션
   ├─ models.py                   # SQLAlchemy 모델
   ├─ schemas.py                  # Pydantic 스키마
   ├─ routers/
   │  ├─ surveys.py               # 설문/응답/CSV 라우터
   │  └─ survey_evaluations.py    # quality/construct/statistics 라우터
   └─ services/                   # 평가/feature 계산/LLM 호출 서비스
```

## 핵심 로직

### 1) 앱 초기화와 CORS

- `main.py`
  - `FRONTEND_ORIGINS`를 읽어 허용 Origin 동적 구성
  - `CORSMiddleware`로 브라우저 요청 허용
  - `/health`에서 런타임 상태와 허용 origin 확인 가능

### 2) 설문/응답 도메인 처리

- `routers/surveys.py`
  - 설문 CRUD
  - 공개 링크 생성 및 공개 응답 처리
  - 응답 저장 후 log/content/relation/population feature 계산
  - 신뢰도 분포 및 CSV 다운로드 제공

### 3) 평가 처리

- `routers/survey_evaluations.py`
  - quality 평가: 규칙 + LLM + 재시도/폴백
  - construct 평가: 임베딩/LLM 기반 평가
  - statistics 평가: 응답 행렬 기반 통계 계산

## 데이터 모델

주요 테이블(모델):

| 모델 | 용도 |
| --- | --- |
| `Survey` | 설문 메타 정보 |
| `SurveyItem` / `SurveyItemOption` | 문항 및 선택지 |
| `Response` / `ResponseAnswer` | 응답 본문 |
| `ResponseLog` / `ResponseItemLog` / `ConnectionEvent` | 응답 행동 로그 |
| `ResponseFeature` | 계산된 feature 및 신뢰도 관련 값 |
| `ItemQualityEvaluation` | 품질 평가 결과 |
| `ConstructEvaluation` | 구성도 평가 결과 |
| `SurveyStatisticalEvaluation` | 통계 평가 결과 |

## 핵심 API

| 기능 | 메서드 | 엔드포인트 |
| --- | --- | --- |
| 설문 목록 조회 | GET | `/surveys/` |
| 설문 생성 | POST | `/surveys/` |
| 설문 조회 | GET | `/surveys/{survey_id}` |
| 설문 수정 | PUT/PATCH | `/surveys/{survey_id}` |
| 설문 삭제 | DELETE | `/surveys/{survey_id}` |
| 응답 제출 | POST | `/surveys/{survey_id}/responses` |
| 공개 링크 생성 | POST | `/surveys/{survey_id}/public-link` |
| 공개 설문 조회 | GET | `/surveys/public/{access_key}` |
| 품질 평가 | POST/GET | `/survey-evaluations/{survey_id}/quality` |
| 구성도 평가 | POST/GET | `/survey-evaluations/{survey_id}/construct` |
| 통계 평가 | POST/GET | `/survey-evaluations/{survey_id}/statistics` |

## 환경 변수

| 변수명 | 설명 |
| --- | --- |
| `OPENAI_API_KEY` | OpenAI API 키 |
| `OPENAI_MODEL` | 품질/문항 처리 모델 |
| `OPENAI_EMBEDDING_MODEL` | 임베딩 모델 |
| `FRONTEND_ORIGINS` | CORS 허용 프론트 도메인 목록(콤마 구분) |

예시:

```env
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4.1-mini
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
FRONTEND_ORIGINS=https://main.d1hl9ud7cc5tjf.amplifyapp.com,http://127.0.0.1:5173
```

## 배포

- 애플리케이션 서버: EC2
- 외부 엔드포인트: API Gateway
- 운영 점검: `/health`, `/docs`
