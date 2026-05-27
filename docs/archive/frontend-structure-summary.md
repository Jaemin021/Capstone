# 프론트 구조 요약

## 큰 구조

프론트는 Vite + React + TypeScript 앱입니다.

- `src/App.tsx`: 전체 라우팅
- `src/layout/AppShell.tsx`: 관리자 화면 공통 헤더와 메뉴
- `src/pages/`: 화면 단위 페이지
- `src/components/`: 여러 페이지에서 재사용하는 UI 컴포넌트
- `src/api/`: 백엔드 API 호출 함수
- `src/types/`: 백엔드 응답과 프론트 상태 타입
- `src/store/`: Zustand 전역 상태

## 주요 화면

### 대시보드 / 설문 목록

파일: `src/pages/DashboardPage.tsx`

역할:

- 저장된 설문 목록 조회
- 응답 링크 복사
- 응답 화면 이동
- 결과 통계 화면 이동
- 새 설문 만들기 진입

백엔드 API:

- `GET /surveys/`

### 설문 만들기

파일: `src/pages/SurveyEditorPage.tsx`

역할:

- 설문 제목, 설명, construct 정보 입력
- 문항 추가, 삭제, 순서 변경
- 설문 생성
- 생성 후 응답 화면과 결과 화면으로 이동

백엔드 API:

- `POST /surveys/`
- `GET /surveys/{survey_id}`

### 응답자 화면

파일: `src/pages/SurveyRespondPage.tsx`

역할:

- 응답자가 설문 문항에 답변
- 문항별 체류 시간, 변경 횟수, 재방문 여부 등 로그 수집
- 응답 제출

백엔드 API:

- `GET /surveys/{survey_id}`
- `POST /surveys/{survey_id}/responses`

응답자 화면은 관리자 메뉴가 보이지 않도록 `AppShell`에서 분리했습니다.

### 결과 통계

파일: `src/pages/ResultsPage.tsx`

역할:

- 응답 신뢰도 요약 표시
- 문항 품질 평가 실행 및 조회
- 문항 구성 타당도 평가 실행 및 조회
- 통계 분석 실행 및 조회

백엔드 API:

- `POST /survey-evaluations/{survey_id}/quality`
- `GET /survey-evaluations/{survey_id}/quality`
- `POST /survey-evaluations/{survey_id}/construct`
- `GET /survey-evaluations/{survey_id}/construct`
- `POST /survey-evaluations/{survey_id}/statistics`
- `GET /survey-evaluations/{survey_id}/statistics`

주의:

- 문항 품질 평가와 구성 타당도 평가는 OpenAI API 키가 필요합니다.
- 통계 분석은 완료 응답이 최소 2개 이상 필요합니다.

### 작성 가이드

파일: `src/pages/GuidePage.tsx`

역할:

- 좋은 설문 문항 작성 기준 안내
- 품질 평가 결과 해석 기준 안내

## API 레이어

파일: `src/api/http.ts`

- Axios 기본 설정
- `VITE_API_BASE_URL`을 사용해 백엔드 주소 결정
- 평가 API가 오래 걸릴 수 있어 timeout은 180초로 설정

파일: `src/api/surveyApi.ts`

- 설문 생성/조회/목록
- 응답 제출
- 품질 평가
- 구성 타당도 평가
- 통계 분석
- mock API 모드 처리

## 상태 관리

파일: `src/store/surveyStore.ts`

- 설문 편집 중인 문항 목록
- 설문 설정
- 선택된 문항

파일: `src/store/toastStore.ts`

- 성공, 실패, 안내 메시지 toast 관리

## 실제 운영 흐름

1. 관리자가 대시보드에서 설문을 생성합니다.
2. 생성된 설문이 저장된 설문 목록에 표시됩니다.
3. 관리자는 응답 링크를 복사해 응답자에게 공유합니다.
4. 응답자는 응답자 화면에서 설문을 제출합니다.
5. 관리자는 설문 목록에서 결과 통계로 이동합니다.
6. 응답이 2개 이상이면 통계 분석을 실행합니다.
7. 문항 품질 평가와 구성 타당도 평가는 OpenAI API를 사용해 실행합니다.
