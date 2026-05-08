import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider } from './context/AuthContext'
import Layout from './components/Layout'
import Login from './pages/Login'
import Register from './pages/Register'
import Dashboard from './pages/Dashboard'
import Tickers from './pages/Tickers'
import Sentiment from './pages/Sentiment'
import Transcripts from './pages/Transcripts'
import Training from './pages/Training'

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/login"    element={<Login />} />
          <Route path="/register" element={<Register />} />
          <Route element={<Layout />}>
            <Route path="/dashboard"   element={<Dashboard />} />
            <Route path="/tickers"     element={<Tickers />} />
            <Route path="/sentiment"   element={<Sentiment />} />
            <Route path="/transcripts" element={<Transcripts />} />
            <Route path="/training"    element={<Training />} />
          </Route>
          <Route path="*" element={<Navigate to="/dashboard" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  )
}
