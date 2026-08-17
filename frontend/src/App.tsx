import { Route, Routes } from 'react-router-dom'
import { AppLayout } from './components/AppLayout'
import { RaceSelectionPage } from './pages/RaceSelectionPage'
import { ROUTES } from './routes/paths'

export default function App() {
  return (
    <Routes>
      <Route element={<AppLayout />}>
        <Route path={ROUTES.raceSelection} element={<RaceSelectionPage />} />
      </Route>
    </Routes>
  )
}
