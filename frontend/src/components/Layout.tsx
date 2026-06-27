import { Link, useNavigate, useLocation } from 'react-router-dom'
import logo from '../assets/dmpi_logo.png'

const NAV = [
  { to: '/dashboard', label: 'Dashboard' },
  { to: '/assets', label: 'Assets' },
  { to: '/projects', label: 'Projects' },
  { to: '/templates', label: 'Templates' },
  { to: '/approvals', label: 'Approvals' },
]

export default function Layout({ children }: { children: React.ReactNode }) {
  const navigate = useNavigate()
  const loc = useLocation()

  const logout = () => {
    localStorage.removeItem('evs_token')
    navigate('/login')
  }

  return (
    <div className="min-h-screen flex flex-col">
      <header className="bg-dmpi-red text-white shadow-md">
        <div className="max-w-7xl mx-auto flex items-center justify-between px-4 py-2">
          <div className="flex items-center gap-3">
            <img src={logo} alt="DMPI Logo" className="h-10 w-auto bg-white rounded p-0.5" />
            <div>
              <div className="font-bold text-sm">Del Monte Philippines Inc.</div>
              <div className="text-xs opacity-80">Equipment Validation Software</div>
            </div>
          </div>
          <nav className="hidden md:flex gap-1">
            {NAV.map(n => (
              <Link key={n.to} to={n.to}
                className={`px-3 py-1.5 rounded text-sm font-medium transition-colors
                  ${loc.pathname.startsWith(n.to) ? 'bg-white text-dmpi-red' : 'hover:bg-red-700'}`}>
                {n.label}
              </Link>
            ))}
          </nav>
          <button onClick={logout}
            className="text-xs px-3 py-1.5 border border-white/40 rounded hover:bg-red-700 transition-colors">
            Sign Out
          </button>
        </div>
      </header>

      <main className="flex-1 max-w-7xl mx-auto w-full px-4 py-6">
        {children}
      </main>

      <footer className="bg-gray-100 border-t text-xs text-gray-500 text-center py-2">
        DMPI Equipment Validation Software — Controlled document management system
      </footer>
    </div>
  )
}
