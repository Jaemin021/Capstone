# Backend README

FastAPI + SQLAlchemy 기반 설문 백엔드입니다.

## 목차

- [프로젝트 소개](#프로젝트-소개)
- [기술 스택](#기술-스택)
- [빠른 시작](#빠른-시작)
- [환경변수](#환경변수)
- [헬스체크와 Swagger](#헬스체크와-swagger)
- [데이터베이스](#데이터베이스)
- [핵심 API](#핵심-api)
- [배포 체크리스트](#배포-체크리스트)

## 프로젝트 소개

설문 데이터 저장, 응답 로그 feature 계산,
품질/구성도/통계 평가 API를 제공합니다.

## 기술 스택

| 영역 | 기술 |
| --- | --- |
| API 서버 | FastAPI |
| ORM | SQLAlchemy |
| 스키마/검증 | Pydantic |
| DB | SQLite |
| AI 연동 | OpenAI API |

## 빠른 시작

### 1) 가상환경 및 의존성 설치

```bash
cd backend
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

### 2) 환경변수 파일 생성

```bash
copy survey\backend\.env.example survey\backend\.env
```

### 3) 서버 실행

```bash
cd backend\survey\backend
..\..\.venv\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8010
```

## 환경변수

주요 변수:

| 변수명 | 설명 |
| --- | --- |
| `OPENAI_API_KEY` | OpenAI 호출 키 |
| `OPENAI_MODEL` | 채팅 모델명 |
| `OPENAI_EMBEDDING_MODEL` | 임베딩 모델명 |
| `FRONTEND_ORIGINS` | CORS 허용 프론트 도메인 목록(콤마 구분) |

## 헬스체크와 Swagger

- 헬스체크: `GET /health`
  - 서버 상태, OpenAI 키 설정 여부, CORS 허용 목록을 확인합니다.
- Swagger: `GET /docs`
  - 브라우저에서 API 목록/스키마/테스트를 확인할 수 있습니다.

로컬 주소:
- 헬스체크: `http://127.0.0.1:8010/health`
- Swagger: `http://127.0.0.1:8010/docs`

## 데이터베이스

- 엔진: `sqlite:///./survey_v2.db`
- 일반 실행 기준 DB 파일 위치: `backend/survey/backend/survey_v2.db`

주의:
- DB 경로는 서버 실행 위치(working directory)에 따라 달라질 수 있습니다.

## 핵심 API

| 기능 | 메서드 | 엔드포인트 |
| --- | --- | --- |
| 설문 생성 | POST | `/surveys/` |
| 설문 조회 | GET | `/surveys/{survey_id}` |
| 응답 제출 | POST | `/surveys/{survey_id}/responses` |
| 품질 평가 | POST/GET | `/survey-evaluations/{survey_id}/quality` |
| 구성도 평가 | POST/GET | `/survey-evaluations/{survey_id}/construct` |
| 통계 평가 | POST/GET | `/survey-evaluations/{survey_id}/statistics` |

## 배포 체크리스트

- [ ] `OPENAI_API_KEY` 설정
- [ ] `FRONTEND_ORIGINS`에 실제 프론트 도메인 반영
- [ ] 서비스 재시작 후 `/health` 확인
- [ ] `/docs`에서 주요 API 동작 확인
