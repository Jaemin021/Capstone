import { Navigate, Route, Routes } from 'react-router-dom'
import { AppShell } from './layout/AppShell'
import { GuidePage } from './pages/GuidePage'
import { PublicSurveyCompletePage } from './pages/PublicSurveyCompletePage'
import { ResultsPage } from './pages/ResultsPage'
import { SurveyRespondPage } from './pages/SurveyRespondPage'
import { SurveyEditorPage } from './pages/SurveyEditorPage'
import { SurveyListPage } from './pages/SurveyListPage'
import { SurveyQrSharePage } from './pages/SurveyQrSharePage'

function App() {
  return (
    <AppShell>
      <Routes>
        <Route path="/" element={<Navigate to="/survey/create" replace />} />
        <Route path="/surveys" element={<SurveyListPage />} />
        <Route path="/survey/create" element={<SurveyEditorPage mode="create" />} />
        <Route path="/survey/:id/edit" element={<SurveyEditorPage mode="edit" />} />
        <Route path="/survey/:id/respond" element={<SurveyRespondPage />} />
        <Route path="/public/s/:accessKey" element={<SurveyRespondPage />} />
        <Route path="/public/s/:accessKey/complete" element={<PublicSurveyCompletePage />} />
        <Route path="/public/o/:inviteKey" element={<SurveyRespondPage />} />
        <Route path="/public/o/:inviteKey/complete" element={<PublicSurveyCompletePage />} />
        <Route path="/share/qr" element={<SurveyQrSharePage />} />
        <Route path="/survey/:id/results" element={<ResultsPage />} />
        <Route path="/guide" element={<GuidePage />} />
        <Route path="*" element={<Navigate to="/survey/create" replace />} />
      </Routes>
    </AppShell>
  )
}

export default App
