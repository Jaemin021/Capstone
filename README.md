# Capstone
캡스톤 - 팀 균열

## Survey Quality Frontend

설문 문항 품질 평가 및 응답 신뢰도 분석 웹 애플리케이션 프론트엔드입니다.

## 실행

```bash
cd frontend
npm install
npm run dev
```

## 빌드

```bash
git status
npm run build
```

## 환경 변수

`.env.example`을 참고해 `.env`를 만들 수 있습니다.

```bash
VITE_API_BASE_URL=http://3.34.198.33:8000
VITE_USE_MOCK_API=false
```

백엔드가 준비되기 전에는 `VITE_USE_MOCK_API=true`로 두면 mock 데이터로 전체 화면 흐름을 확인할 수 있습니다.

## 주요 경로

| 경로 | 설명 |
| --- | --- |
| `/` | 랜딩 / 대시보드 |
| `/survey/create` | 설문지 생성 |
| `/survey/:id/edit` | 설문지 편집 |
| `/survey/:id/results` | 응답 통계 확인 |
| `/guide` | 문항 작성 가이드라인 |

## 백엔드 연동

API 연결 표와 요청/응답 타입은 `src/docs/backend-integration.md`에 정리되어 있습니다.
