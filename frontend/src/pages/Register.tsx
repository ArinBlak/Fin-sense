import { useState, type FormEvent } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

export default function Register() {
  const { register } = useAuth()
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const submit = async (e: FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      await register(email, username, password)
      navigate('/dashboard')
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Registration failed.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center px-4" style={{ background: '#081F30' }}>
      <div className="w-full max-w-md">
        <div className="text-center mb-10">
          <h1 className="text-3xl font-bold">
            <span style={{ color: '#28B098' }}>Fin</span>Sense
          </h1>
          <p className="mt-2 text-sm" style={{ color: '#456E8A' }}>Earnings Sentiment Analysis Platform</p>
        </div>

        <div className="rounded-2xl p-8" style={{ background: '#15293A', border: '1px solid rgba(255,255,255,0.06)' }}>
          <h2 className="text-xl font-semibold mb-6 text-white">Create account</h2>

          {error && (
            <div className="mb-4 px-4 py-3 rounded-lg text-sm text-red-300" style={{ background: 'rgba(239,68,68,0.1)' }}>
              {error}
            </div>
          )}

          <form onSubmit={submit} className="space-y-5">
            {[
              { label: 'Email', type: 'email', value: email, set: setEmail, ph: 'you@example.com' },
              { label: 'Username', type: 'text', value: username, set: setUsername, ph: 'yourname' },
              { label: 'Password', type: 'password', value: password, set: setPassword, ph: '••••••••' },
            ].map(({ label, type, value, set, ph }) => (
              <div key={label}>
                <label className="block text-sm font-medium mb-2" style={{ color: '#456E8A' }}>{label}</label>
                <input
                  type={type}
                  value={value}
                  onChange={(e) => set(e.target.value)}
                  required
                  className="w-full px-4 py-3 rounded-xl text-white text-sm outline-none"
                  style={{ background: '#214055', border: '1px solid rgba(255,255,255,0.08)' }}
                  placeholder={ph}
                />
              </div>
            ))}
            <button
              type="submit"
              disabled={loading}
              className="btn-gradient w-full py-3 rounded-xl text-white font-semibold text-sm disabled:opacity-60"
            >
              {loading ? 'Creating account...' : 'Create Account'}
            </button>
          </form>

          <p className="mt-6 text-center text-sm" style={{ color: '#456E8A' }}>
            Already have an account?{' '}
            <Link to="/login" style={{ color: '#28B098' }} className="font-medium hover:underline">
              Sign in
            </Link>
          </p>
        </div>
      </div>
    </div>
  )
}
