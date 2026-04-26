# 백엔드 연동 정리표

프론트는 현재 `VITE_USE_MOCK_API=true` 기준으로 mock 데이터가 동작합니다. 백엔드 API가 준비되면 `.env`에서 `VITE_API_BASE_URL`을 백엔드 서버 주소로 설정하고, `VITE_USE_MOCK_API=false`로 바꾸면 `src/api/surveyApi.ts`의 Axios 호출이 사용됩니다.

## 공통 환경 변수

| 변수 | 용도 | 예시 |
| --- | --- | --- |
| `VITE_API_BASE_URL` | 백엔드 API base URL | `http://localhost:8080` |
| `VITE_USE_MOCK_API` | mock API 사용 여부 | `true` 또는 `false` |

## API 연동 표

| 화면/기능 | 프론트 호출 함수 | 엔드포인트 | 요청 | 응답 | 연결 파일 |
| --- | --- | --- | --- | --- | --- |
| 문항 품질 평가 | `evaluateItemQuality` | `POST /api/item/quality` | `{ text: string }` | `{ score: number, flaggedWords: string[], suggestion: string \| null }` | `src/api/surveyApi.ts`, `src/pages/SurveyEditorPage.tsx` |
| 전체 CITC 예측 | `predictSurveyCitc` | `POST /api/survey/citc-predict` | `{ items: { id: string, text: string }[] }` | `{ results: { id: string, citcScore: number, embeddingScore: number, llmScore: number }[] }` | `src/api/surveyApi.ts`, `src/pages/SurveyEditorPage.tsx` |
| 함정 문항 생성 | `generateTrapItem` | `POST /api/item/generate-trap` | `{ surveyContext: string, items: string[] }` | `{ trapItem: string, suggestedPosition: number }` | `src/api/surveyApi.ts`, `src/components/SettingsPanel.tsx`, `src/pages/SurveyEditorPage.tsx` |
| 역문항 생성 | `generateReverseItem` | `POST /api/item/generate-reverse` | `{ originalItem: string }` | `{ reverseItem: string }` | `src/api/surveyApi.ts`, `src/pages/SurveyEditorPage.tsx` |
| 응답 신뢰도 조회 | `getSurveyReliability` | `GET /api/survey/:id/reliability` | path param: `id` | `{ respondents: { id: string, submittedAt: string, reliabilityScore: number, timePerItem: number[], flagged: boolean, reason: string }[] }` | `src/api/surveyApi.ts`, `src/pages/ResultsPage.tsx` |
| 문항별 통계 조회 | `getSurveyItemStats` | `GET /api/survey/:id/item-stats` | path param: `id` | `{ items: { itemId: string, text: string, mean: number, variance: number, count: number, missing: number, distribution: number[] }[] }` | `src/api/surveyApi.ts`, `src/pages/ResultsPage.tsx` |

## 프론트 흐름

1. 사용자가 `/survey/create`에서 문항을 추가하거나 수정합니다.
2. `문항 평가하기` 클릭 시 `evaluateItemQuality({ text })`를 호출합니다.
3. 품질 점수가 60점 이하이고 `suggestion`이 있으면 대체 문항 모달을 표시합니다.
4. 문항이 2개 이상이면 `전체 일관성 분석` 버튼으로 `predictSurveyCitc({ items })`를 호출합니다.
5. 설문 설정 패널에서 함정 문항 생성 시 `generateTrapItem({ surveyContext, items })`를 호출합니다.
6. 선택 문항의 역문항 생성 시 `generateReverseItem({ originalItem })`를 호출합니다.
7. `/survey/:id/results` 진입 시 React Query가 신뢰도와 문항별 통계를 자동 조회합니다.

## 백엔드팀 확인 필요 사항

| 항목 | 확인 내용 |
| --- | --- |
| 인증 방식 | 토큰/세션이 필요한 경우 Axios interceptor 추가 필요 |
| `suggestedPosition` 기준 | 0 기반 index인지 1 기반 순서인지 합의 필요 |
| `citcScore` 범위 | 현재 프론트는 `0~1` 범위로 표시하고, UI에서는 `* 100`으로 점수바 처리 |
| `reliabilityScore` 범위 | 현재 프론트는 `0~100` 점수로 처리 |
| `distribution` 의미 | 배열 index가 리커트 척도 1점부터 매칭되는지 확인 필요 |
| 날짜 포맷 | `submittedAt`은 현재 문자열 표시, ISO 문자열이면 포맷 함수 추가 가능 |
