# Frontend README

React + Vite + TypeScript 기반 설문 프론트엔드입니다.

## 목차

- [프로젝트 소개](#프로젝트-소개)
- [기술 스택](#기술-스택)
- [빠른 시작](#빠른-시작)
- [환경변수](#환경변수)
- [주요 라우트](#주요-라우트)
- [백엔드 연동 API](#백엔드-연동-api)
- [배포 체크리스트](#배포-체크리스트)

## 프로젝트 소개

설문 생성/목록/응답/결과 페이지를 제공하며,
백엔드 API와 연결해 응답 데이터 분석 결과를 시각화합니다.

## 기술 스택

| 영역 | 기술 |
| --- | --- |
| UI | React, TailwindCSS |
| 빌드 도구 | Vite |
| 언어 | TypeScript |
| 상태/요청 | Zustand, TanStack Query, Axios |
| 라우팅 | React Router |

## 빠른 시작

### 사전 요구사항

- Node.js 20+ 권장
- 백엔드 서버 실행 중 (`http://127.0.0.1:8010`)

### 설치/실행

```bash
cd frontend
npm install
npm run dev
```

기본 접속:
- `http://127.0.0.1:5173`

### 빌드

```bash
cd frontend
npm run build
```

## 환경변수

로컬에서는 `frontend/.env.local` 사용 권장.

| 변수명 | 설명 | 예시 |
| --- | --- | --- |
| `VITE_API_BASE_URL` | 백엔드 API 주소 | `http://127.0.0.1:8010` |
| `VITE_USE_MOCK_API` | mock 사용 여부 (배포 시 false) | `false` |
| `VITE_PUBLIC_APP_ORIGIN` | 공개 링크/QR 기준 도메인 | `http://127.0.0.1:5173` |
| `VITE_REQUIRE_MOBILE_RESPOND` | 모바일 응답 강제 여부 | `false` |

예시:

```env
VITE_API_BASE_URL=http://127.0.0.1:8010
VITE_USE_MOCK_API=false
VITE_PUBLIC_APP_ORIGIN=http://127.0.0.1:5173
VITE_REQUIRE_MOBILE_RESPOND=false
```

## 주요 라우트

| 경로 | 설명 |
| --- | --- |
| `/survey/create` | 설문 생성 |
| `/surveys` | 설문 목록 |
| `/survey/:id/edit` | 설문 편집 |
| `/survey/:id/respond` | 내부 응답 |
| `/public/s/:accessKey` | 공개 응답 |
| `/public/o/:inviteKey` | 1회용 공개 응답 |
| `/survey/:id/results` | 결과/분석 |

## 백엔드 연동 API

| 기능 | 메서드 | 엔드포인트 |
| --- | --- | --- |
| 설문 생성 | POST | `/surveys/` |
| 설문 조회 | GET | `/surveys/{survey_id}` |
| 응답 제출 | POST | `/surveys/{survey_id}/responses` |
| 품질 평가 | POST/GET | `/survey-evaluations/{survey_id}/quality` |
| 구성도 평가 | POST/GET | `/survey-evaluations/{survey_id}/construct` |
| 통계 평가 | POST/GET | `/survey-evaluations/{survey_id}/statistics` |

## 배포 체크리스트

- [ ] `VITE_USE_MOCK_API=false`
- [ ] `VITE_API_BASE_URL`이 외부(모바일)에서 접근 가능
- [ ] `VITE_PUBLIC_APP_ORIGIN`을 실제 배포 도메인으로 설정
- [ ] `npm run build` 성공 확인
