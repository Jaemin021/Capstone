# Backend Integration

The frontend can still run with mock helpers, but the local integration target is now the FastAPI backend in `backend/`.

## Local Environment

Create `frontend/.env.local`:

```env
VITE_API_BASE_URL=http://127.0.0.1:8010
VITE_USE_MOCK_API=false
```

`frontend/.env.local` is ignored by git.

## Main Backend APIs

| Flow | Method | Endpoint | Frontend file |
| --- | --- | --- | --- |
| Create survey | `POST` | `/surveys/` | `src/pages/SurveyEditorPage.tsx`, `src/api/surveyApi.ts` |
| Get survey | `GET` | `/surveys/{survey_id}` | `src/pages/SurveyRespondPage.tsx`, `src/pages/ResultsPage.tsx` |
| Submit response logs | `POST` | `/surveys/{survey_id}/responses` | `src/pages/SurveyRespondPage.tsx` |
| Evaluate item quality | `POST` | `/survey-evaluations/{survey_id}/quality` | `src/pages/ResultsPage.tsx` |
| Get item quality | `GET` | `/survey-evaluations/{survey_id}/quality` | `src/pages/ResultsPage.tsx` |
| Evaluate construct | `POST` | `/survey-evaluations/{survey_id}/construct` | `src/pages/ResultsPage.tsx` |
| Get construct | `GET` | `/survey-evaluations/{survey_id}/construct` | `src/pages/ResultsPage.tsx` |
| Run statistics | `POST` | `/survey-evaluations/{survey_id}/statistics` | `src/pages/ResultsPage.tsx` |
| Get statistics | `GET` | `/survey-evaluations/{survey_id}/statistics` | `src/pages/ResultsPage.tsx` |

## Implemented Frontend Flow

1. Create a survey at `/survey/create`.
2. Click `설문 생성`.
3. Open `/survey/{survey_id}/respond`.
4. Answer one item per screen.
5. The response UI records item timing, change counts, revisit counts, touch counts, and online/offline events.
6. On submit, the frontend sends `answers + log` to `POST /surveys/{survey_id}/responses`.
7. The backend returns feature data and a reliability summary.
8. `/survey/{survey_id}/results` shows the response summary and lets the user run quality, construct, and statistics evaluations.

## Notes

- `selected_option_order` must be the backend option order, not the option label.
- `item_id` must come from the backend survey response.
- Timing values are sent in milliseconds.
- Construct and quality evaluation need a real `OPENAI_API_KEY`; local smoke tests can use a dummy key only for create/get/response flows.
