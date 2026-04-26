import { Navigate, Route, Routes } from 'react-router-dom'
import { AppShell } from './layout/AppShell'
import { DashboardPage } from './pages/DashboardPage'
import { GuidePage } from './pages/GuidePage'
import { ResultsPage } from './pages/ResultsPage'
import { SurveyEditorPage } from './pages/SurveyEditorPage'

function App() {
  return (
    <AppShell>
      <Routes>
        <Route path="/" element={<DashboardPage />} />
        <Route path="/survey/create" element={<SurveyEditorPage mode="create" />} />
        <Route path="/survey/:id/edit" element={<SurveyEditorPage mode="edit" />} />
        <Route path="/survey/:id/results" element={<ResultsPage />} />
        <Route path="/guide" element={<GuidePage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </AppShell>
  )
}

export default App
