import { Link, useLocation } from 'react-router-dom'
import { motion } from 'framer-motion'
import { Activity } from 'lucide-react'
import DarkModeToggle from '../common/DarkModeToggle'

const NAV_LINKS = [
  { to: '/',          label: 'Home' },
  { to: '/dashboard', label: 'Dashboard' },
  { to: '/settings',  label: 'Settings' },
  { to: '/help',      label: 'Help' },
]

export default function Navbar() {
  const { pathname } = useLocation()

  return (
    <nav className="sticky top-0 z-50 bg-white/80 dark:bg-slate-900/80 backdrop-blur-md border-b border-slate-200 dark:border-slate-700 shadow-sm">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo */}
          <Link to="/" className="flex items-center gap-2 group">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-primary-600 to-teal-500 flex items-center justify-center shadow-md group-hover:shadow-lg transition-shadow">
              <Activity className="w-5 h-5 text-white" />
            </div>
            <span className="text-xl font-bold text-slate-800 dark:text-white tracking-tight">
              Medi<span className="text-primary-600">core</span>
            </span>
          </Link>

          {/* Links */}
          <div className="hidden md:flex items-center gap-1">
            {NAV_LINKS.map(({ to, label }) => {
              const active = pathname === to
              return (
                <Link key={to} to={to} className="relative px-4 py-2 rounded-lg text-sm font-medium transition-colors duration-150 hover:text-primary-600 dark:hover:text-primary-400"
                  style={{ color: active ? undefined : '' }}>
                  {active && (
                    <motion.span
                      layoutId="nav-pill"
                      className="absolute inset-0 bg-primary-50 dark:bg-primary-900/40 rounded-lg"
                      transition={{ type: 'spring', stiffness: 380, damping: 30 }}
                    />
                  )}
                  <span className={`relative z-10 ${active ? 'text-primary-600 dark:text-primary-400' : 'text-slate-600 dark:text-slate-300'}`}>
                    {label}
                  </span>
                </Link>
              )
            })}
          </div>

          {/* Right actions */}
          <div className="flex items-center gap-3">
            <DarkModeToggle />
            <Link
              to="/dashboard"
              className="hidden sm:inline-flex items-center gap-1.5 px-4 py-2 rounded-lg bg-primary-600 hover:bg-primary-700 text-white text-sm font-semibold shadow-sm transition-colors"
            >
              <Activity className="w-4 h-4" />
              Dashboard
            </Link>
          </div>
        </div>
      </div>
    </nav>
  )
}
