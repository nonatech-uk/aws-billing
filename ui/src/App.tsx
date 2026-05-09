import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import Shell from './components/layout/Shell'
import Summary from './pages/Summary'
import AccountDetail from './pages/AccountDetail'
import Settings from './pages/Settings'

export default function App() {
  return (
    <BrowserRouter>
      <Shell>
        <Routes>
          <Route path="/" element={<Summary />} />
          <Route path="/account/:accountId" element={<AccountDetail />} />
          <Route path="/settings" element={<Settings />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </Shell>
    </BrowserRouter>
  )
}
