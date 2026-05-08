import { NavLink, useNavigate } from 'react-router-dom'
import { LayoutDashboard, TrendingUp, FileText, Brain, LogOut, Activity } from 'lucide-react'
import { useAuth } from '../context/AuthContext'

const links = [
  { to: '/dashboard', icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/tickers',   icon: TrendingUp,      label: 'Tickers' },
  { to: '/sentiment', icon: Activity,         label: 'Sentiment' },
  { to: '/transcripts', icon: FileText,       label: 'Transcripts' },
  { to: '/training',  icon: Brain,            label: 'Training' },
]

export default function Sidebar() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  const handleLogout = () => { logout(); navigate('/login') }

  return (
    <aside className="w-64 min-h-screen flex flex-col" style={{ background: '#15293A' }}>
      {/* Logo */}
      <div className="px-6 py-7 border-b border-white/10">
        <h1 className="text-xl font-bold tracking-wide">
          <span style={{ color: '#28B098' }}>Fin</span>
          <span className="text-white">Sense</span>
        </h1>
        <p className="text-xs mt-1" style={{ color: '#456E8A' }}>Earnings Sentiment AI</p>
      </div>

      {/* Nav */}
      <nav className="flex-1 px-3 py-6 space-y-1">
        {links.map(({ to, icon: Icon, label }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              `flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium transition-all duration-200 ${
                isActive
                  ? 'text-white'
                  : 'text-[#456E8A] hover:text-white hover:bg-white/5'
              }`
            }
            style={({ isActive }) => isActive ? { background: 'linear-gradient(135deg, #14799D33, #29C39B33)', borderLeft: '3px solid #28B098' } : {}}
          >
            <Icon size={18} />
            {label}
          </NavLink>
        ))}
      </nav>

      {/* User */}
      <div className="px-4 py-5 border-t border-white/10">
        <div className="flex items-center gap-3 mb-3">
          <div className="w-8 h-8 rounded-full flex items-center justify-center text-sm font-semibold text-white btn-gradient">
            {user?.username?.[0]?.toUpperCase()}
          </div>
          <div>
            <p className="text-sm font-medium text-white">{user?.username}</p>
            <p className="text-xs truncate" style={{ color: '#456E8A' }}>{user?.email}</p>
          </div>
        </div>
        <button
          onClick={handleLogout}
          className="flex items-center gap-2 w-full px-3 py-2 rounded-lg text-sm transition-colors hover:bg-white/5"
          style={{ color: '#456E8A' }}
        >
          <LogOut size={15} /> Logout
        </button>
      </div>
    </aside>
  )
}
