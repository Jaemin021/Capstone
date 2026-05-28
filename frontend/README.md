# Frontend README

설문 생성/응답/결과 분석 UI를 제공하는 React 프론트엔드입니다.

## 목차

- [프로젝트 소개](#프로젝트-소개)
- [주요 기능](#주요-기능)
- [기술 스택](#기술-스택)
- [빠른 시작](#빠른-시작)
- [폴더 구조](#폴더-구조)
- [핵심 로직](#핵심-로직)
- [환경 변수](#환경-변수)
- [배포](#배포)
- [트러블슈팅](#트러블슈팅)

## 프로젝트 소개

프론트엔드는 설문 제작자와 응답자 모두를 위한 UI를 제공합니다.

- 제작자: 설문 생성/수정/복제/삭제, 공개 링크 생성
- 응답자: 내부/공개/1회용 링크 설문 응답
- 분석자: 신뢰도/품질/구성도/통계 결과 확인 및 CSV 다운로드

## 주요 기능

| 기능 | 설명 |
| --- | --- |
| 설문 편집기 | 문항 추가, 옵션 편집, 역문항/함정문항 보조 흐름 |
| 설문 목록 | 설문 조회, 복제, 삭제, 공개 링크 생성 |
| 응답 페이지 | 문항 단위 응답, 로그 수집, 모바일 정책 적용 |
| 결과 페이지 | 신뢰도 상태, quality/construct/statistics 결과 시각화 |
| 공용 링크 | 공개 링크 및 1회용 링크 응답 지원 |

## 기술 스택

| 영역 | 기술 |
| --- | --- |
| Core | React 19, TypeScript |
| Build | Vite |
| Routing | React Router |
| Data Fetch | Axios, TanStack Query |
| State | Zustand |
| UI | TailwindCSS, Lucide React, Recharts |

## 빠른 시작

### 사전 요구사항

- Node.js 20+
- 실행 중인 백엔드 API (`http://127.0.0.1:8010`)

### 설치 및 실행

```bash
cd frontend
npm install
copy .env.example .env.local
npm run dev
```

기본 접속 주소: `http://127.0.0.1:5173`

### 빌드

```bash
npm run build
```

## 폴더 구조

```text
frontend/
├─ src/
│  ├─ api/
│  │  ├─ http.ts              # Axios 인스턴스 및 mock/real API 스위치
│  │  ├─ surveyApi.ts         # 설문/응답/평가 API 함수
│  │  └─ mock/surveyMock.ts   # 목업 응답 데이터
│  ├─ pages/                  # 라우트 페이지
│  ├─ components/             # 재사용 컴포넌트
│  ├─ store/                  # 전역 상태
│  ├─ types/                  # 타입 정의
│  ├─ App.tsx                 # 라우팅 구성
│  └─ main.tsx                # 앱 진입점
├─ public/
├─ .env.example
└─ index.html
```

## 핵심 로직

### 1) API 연결

- `src/api/http.ts`
  - `VITE_API_BASE_URL`로 Axios `baseURL` 설정
  - `VITE_USE_MOCK_API` 값에 따라 mock/real API 사용 결정

### 2) 설문/응답 API 집약

- `src/api/surveyApi.ts`
  - 설문 CRUD
  - 공개 링크/1회용 링크 생성 및 조회
  - 응답 제출 및 결과 조회
  - quality/construct/statistics 평가 호출
  - CSV 다운로드 처리

### 3) 응답 로그 수집

- `src/pages/SurveyRespondPage.tsx`
  - 문항 체류시간
  - 첫 선택/마지막 선택 시각
  - 변경 횟수, 재방문 횟수
  - 오프라인 이벤트 및 연결 복구 이벤트

### 4) 결과 분석 시각화

- `src/pages/ResultsPage.tsx`
  - 신뢰도 분포/상태 표시
  - quality/construct/statistics 실행 및 결과 표시
  - 실패 시 에러 메시지 정규화

## 환경 변수

`.env.example`을 기준으로 `.env.local`을 생성해 사용합니다.

| 변수명 | 설명 | 예시 |
| --- | --- | --- |
| `VITE_API_BASE_URL` | 백엔드 API 주소 | `http://127.0.0.1:8010` |
| `VITE_USE_MOCK_API` | 목업 API 사용 여부 | `false` |
| `VITE_PUBLIC_APP_ORIGIN` | 공개 링크 도메인 기준값 | `http://127.0.0.1:5173` |
| `VITE_REQUIRE_MOBILE_RESPOND` | 모바일 응답 강제 여부 | `false` |

## 배포

- 프론트 호스팅: AWS Amplify
- 운영 URL: `https://main.d1hl9ud7cc5tjf.amplifyapp.com`

Amplify에서 `main` 브랜치 빌드 시, 환경변수는 Amplify 콘솔의 값을 사용합니다.

## 트러블슈팅

### `Network Error` 또는 CORS 오류

1. 백엔드 `FRONTEND_ORIGINS`에 Amplify 도메인이 포함됐는지 확인
2. API Gateway preflight(OPTIONS) 설정 확인
3. `VITE_API_BASE_URL`이 실제 접근 가능한 엔드포인트인지 확인
