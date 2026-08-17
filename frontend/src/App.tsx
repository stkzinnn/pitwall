import { Route, Routes } from 'react-router-dom'
import { AppLayout } from './components/AppLayout'
import { RaceSelectionPage } from './pages/RaceSelectionPage'
import { ResultsPage } from './pages/ResultsPage'
import { StrategyBuilderPage } from './pages/StrategyBuilderPage'
import { ROUTES } from './routes/paths'

export default function App() {
  return (
    <Routes>
      <Route element={<AppLayout />}>
        <Route path={ROUTES.raceSelection} element={<RaceSelectionPage />} />
        <Route path={ROUTES.raceResults} element={<ResultsPage />} />
        <Route path={ROUTES.strategyBuilder} element={<StrategyBuilderPage />} />
      </Route>
    </Routes>
  )
}
