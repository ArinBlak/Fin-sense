import { useState, type FormEvent } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import loginHero from '../assets/image.png'

export default function Login() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const submit = async (e: FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      await login(email, password)
      navigate('/dashboard')
    } catch {
      setError('Invalid credentials. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex" style={{ background: '#081F30' }}>
      {/* Left panel — image */}
      <div className="hidden lg:flex lg:w-1/2 relative overflow-hidden">
        <img
          src={loginHero}
          alt="FinSense"
          className="absolute inset-0 w-full h-full object-cover"
        />
        <div className="absolute inset-0" style={{ background: 'linear-gradient(135deg, rgba(8,31,48,0.45) 0%, rgba(40,176,152,0.18) 100%)' }} />
        <div className="relative z-10 flex flex-col justify-end p-12">
          <h2 className="text-4xl font-bold text-white leading-tight">
            Decode what earnings calls<br />
            <span style={{ color: '#28B098' }}>really mean.</span>
          </h2>
          <p className="mt-3 text-sm" style={{ color: 'rgba(255,255,255,0.6)' }}>
            FinBERT-powered sentiment analysis on earnings transcripts.
          </p>
        </div>
      </div>

      {/* Right panel — login form */}
      <div className="flex flex-1 items-center justify-center px-6 py-12">
        <div className="w-full max-w-md">
          <div className="mb-10">
            <h1 className="text-3xl font-bold">
              <span style={{ color: '#28B098' }}>Fin</span>Sense
            </h1>
            <p className="mt-2 text-sm" style={{ color: '#456E8A' }}>Earnings Sentiment Analysis Platform</p>
          </div>

          <div className="rounded-2xl p-8" style={{ background: '#15293A', border: '1px solid rgba(255,255,255,0.06)' }}>
            <h2 className="text-xl font-semibold mb-6 text-white">Sign in</h2>

            {error && (
              <div className="mb-4 px-4 py-3 rounded-lg text-sm text-red-300" style={{ background: 'rgba(239,68,68,0.1)' }}>
                {error}
              </div>
            )}

            <form onSubmit={submit} className="space-y-5">
              <div>
                <label className="block text-sm font-medium mb-2" style={{ color: '#456E8A' }}>Email</label>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                  className="w-full px-4 py-3 rounded-xl text-white text-sm outline-none transition-all"
                  style={{ background: '#214055', border: '1px solid rgba(255,255,255,0.08)' }}
                  placeholder="you@example.com"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-2" style={{ color: '#456E8A' }}>Password</label>
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  className="w-full px-4 py-3 rounded-xl text-white text-sm outline-none transition-all"
                  style={{ background: '#214055', border: '1px solid rgba(255,255,255,0.08)' }}
                  placeholder="••••••••"
                />
              </div>
              <button
                type="submit"
                disabled={loading}
                className="btn-gradient w-full py-3 rounded-xl text-white font-semibold text-sm transition-opacity disabled:opacity-60"
              >
                {loading ? 'Signing in...' : 'Sign In'}
              </button>
            </form>

            <p className="mt-6 text-center text-sm" style={{ color: '#456E8A' }}>
              Don't have an account?{' '}
              <Link to="/register" style={{ color: '#28B098' }} className="font-medium hover:underline">
                Register
              </Link>
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
