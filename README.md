# Capstone Survey Platform

응답 로그 기반 신뢰도 분석과 문항 품질 평가를 제공하는 설문 플랫폼입니다.

## 목차

- [프로젝트 소개](#프로젝트-소개)
- [주요 기능](#주요-기능)
- [기술 스택](#기술-스택)
- [빠른 시작](#빠른-시작)
- [저장소 구조](#저장소-구조)
- [아키텍처 개요](#아키텍처-개요)
- [핵심 API](#핵심-api)
- [환경 변수](#환경-변수)
- [배포 정보](#배포-정보)
- [문서 안내](#문서-안내)

## 프로젝트 소개

Capstone Survey Platform은 다음을 목표로 합니다.

- 설문 생성부터 응답 수집, 결과 분석까지 하나의 흐름 제공
- 단순 점수 집계가 아닌 응답 행동 로그 기반 신뢰도 분석
- 문항 품질(quality), 구성도(construct), 통계(statistics) 평가 자동화

## 주요 기능

| 기능 | 설명 |
| --- | --- |
| 설문 생성/편집 | 관리자 화면에서 문항 생성, 수정, 복제 |
| 응답 수집 | 내부 링크, 공개 링크, 1회용 공개 링크 응답 |
| 응답 로그 분석 | 체류 시간, 변경 횟수, 재방문, 오프라인 이벤트 수집 |
| 신뢰도 분석 | 응답 행동 feature를 기반으로 신뢰도 점수/상태 산출 |
| 문항 평가 | quality, construct, statistics 평가 결과 제공 |
| 결과 내보내기 | 응답 feature CSV, 문항 평가 CSV 다운로드 |

## 기술 스택

| 영역 | 기술 |
| --- | --- |
| Frontend | React 19, Vite, TypeScript, TailwindCSS, TanStack Query, Zustand |
| Backend | FastAPI, SQLAlchemy, Pydantic, Uvicorn |
| Database | SQLite |
| AI | OpenAI API |
| Deploy | AWS Amplify (Frontend), EC2 + API Gateway (Backend) |

## 빠른 시작

### 1) 저장소 클론

```bash
git clone https://github.com/Jaemin021/Capstone.git
cd Capstone
```

### 2) 백엔드 실행

```bash
cd backend
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
copy survey\backend\.env.example survey\backend\.env
cd survey\backend
..\..\.venv\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8010
```

### 3) 프론트엔드 실행

```bash
cd frontend
npm install
copy .env.example .env.local
npm run dev
```

- Frontend: `http://127.0.0.1:5173`
- Backend: `http://127.0.0.1:8010`
- Swagger: `http://127.0.0.1:8010/docs`

## 저장소 구조

```text
Capstone/
├─ frontend/
│  ├─ src/
│  │  ├─ api/                  # API 클라이언트 및 호출 함수
│  │  ├─ pages/                # 설문 생성/응답/결과 페이지
│  │  ├─ components/           # 재사용 UI 컴포넌트
│  │  ├─ store/                # Zustand 상태 저장소
│  │  ├─ types/                # 공통 타입 정의
│  │  └─ main.tsx              # 프론트 진입점
│  ├─ public/
│  ├─ .env.example
│  └─ README.md
├─ backend/
│  ├─ survey/backend/
│  │  ├─ main.py               # FastAPI 앱 진입점, CORS 설정
│  │  ├─ routers/              # surveys, survey-evaluations 라우터
│  │  ├─ services/             # 품질/구성도/통계/feature 계산 서비스
│  │  ├─ models.py             # SQLAlchemy 모델
│  │  └─ schemas.py            # 요청/응답 스키마
│  ├─ requirements.txt
│  └─ README.md
├─ docs/
│  └─ archive/                 # 과거 작업/참고 문서 보관
└─ README.md
```

## 아키텍처 개요

### 프론트엔드

- `frontend/src/api/http.ts`에서 `VITE_API_BASE_URL` 기반 Axios 인스턴스 생성
- `frontend/src/api/surveyApi.ts`에서 설문/응답/평가 API 호출 통합
- `frontend/src/pages/SurveyRespondPage.tsx`에서 응답 로그(시간, 변경, 재방문, 오프라인) 수집
- `frontend/src/pages/ResultsPage.tsx`에서 신뢰도 및 quality/construct/statistics 결과 시각화

### 백엔드

- `backend/survey/backend/main.py`에서 FastAPI 앱 구성, CORS/헬스체크 제공
- `routers/surveys.py`에서 설문 CRUD, 공개 링크, 응답 저장, CSV 다운로드 처리
- `routers/survey_evaluations.py`에서 quality/construct/statistics 평가 API 제공
- `services/*`에서 OpenAI 호출, 임베딩, 품질 점수화, 통계 계산 로직 수행

### 데이터 흐름

1. 프론트에서 설문 생성 요청 (`POST /surveys/`)
2. 응답자가 설문 제출 (`POST /surveys/{survey_id}/responses`)
3. 백엔드가 응답/로그를 저장하고 feature 계산
4. 프론트 결과 페이지에서 평가 API 호출
5. 백엔드가 quality/construct/statistics 결과 저장 후 반환
6. 프론트에서 차트/배지/표 형태로 시각화

## 핵심 API

| 기능 | 메서드 | 엔드포인트 |
| --- | --- | --- |
| 설문 목록 조회 | GET | `/surveys/` |
| 설문 생성 | POST | `/surveys/` |
| 설문 복제 | POST | `/surveys/{survey_id}/duplicate` |
| 설문 수정 | PUT/PATCH | `/surveys/{survey_id}` |
| 설문 삭제 | DELETE | `/surveys/{survey_id}` |
| 공개 링크 생성 | POST | `/surveys/{survey_id}/public-link` |
| 공개 설문 조회 | GET | `/surveys/public/{access_key}` |
| 응답 제출 | POST | `/surveys/{survey_id}/responses` |
| 품질 평가 | POST/GET | `/survey-evaluations/{survey_id}/quality` |
| 구성도 평가 | POST/GET | `/survey-evaluations/{survey_id}/construct` |
| 통계 평가 | POST/GET | `/survey-evaluations/{survey_id}/statistics` |

## 환경 변수

### Frontend

| 변수명 | 설명 |
| --- | --- |
| `VITE_API_BASE_URL` | 백엔드 API 기본 주소 |
| `VITE_USE_MOCK_API` | 목업 API 사용 여부 |
| `VITE_PUBLIC_APP_ORIGIN` | 공개 링크 생성 기준 도메인 |
| `VITE_REQUIRE_MOBILE_RESPOND` | 모바일 응답 강제 여부 |

### Backend

| 변수명 | 설명 |
| --- | --- |
| `OPENAI_API_KEY` | OpenAI API 키 |
| `OPENAI_MODEL` | 품질/문항 처리용 모델 |
| `OPENAI_EMBEDDING_MODEL` | 임베딩 모델 |
| `FRONTEND_ORIGINS` | CORS 허용 프론트 도메인 목록(콤마 구분) |

## 배포 정보

- 프론트엔드: `https://main.d1hl9ud7cc5tjf.amplifyapp.com`
- 백엔드 API: `https://e827jde79k.execute-api.ap-northeast-2.amazonaws.com`

## 문서 안내

| 문서 | 설명 |
| --- | --- |
| [frontend/README.md](frontend/README.md) | 프론트 실행/구조/핵심 로직 |
| [backend/README.md](backend/README.md) | 백엔드 실행/구조/API 로직 |
| [docs/README.md](docs/README.md) | 문서 인덱스 및 archive 요약 |
| [docs/archive/frontend-architecture-summary.md](docs/archive/frontend-architecture-summary.md) | 프론트 구조 보조 설명 |
| [docs/archive/feature-scoring-reference.md](docs/archive/feature-scoring-reference.md) | feature/점수 산식 상세 |
| [docs/archive/experiment-plan.md](docs/archive/experiment-plan.md) | 실험 설계 및 기록 |
