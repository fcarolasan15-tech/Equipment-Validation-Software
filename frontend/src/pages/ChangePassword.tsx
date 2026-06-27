import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { changePassword } from '../api/auth'

export default function ChangePassword() {
  const [current, setCurrent] = useState('')
  const [next, setNext] = useState('')
  const [confirm, setConfirm] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (next !== confirm) { setError('Passwords do not match'); return }
    if (next.length < 8) { setError('Password must be at least 8 characters'); return }
    setLoading(true)
    try {
      await changePassword(current, next)
      navigate('/dashboard')
    } catch {
      setError('Current password incorrect')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="bg-white shadow-lg rounded-lg p-8 w-full max-w-md">
        <h2 className="text-lg font-bold mb-2">Change Password Required</h2>
        <p className="text-sm text-gray-500 mb-6">
          Your account requires a password change before continuing.
        </p>
        <form onSubmit={handleSubmit} className="space-y-4">
          {(['Current Password', 'New Password', 'Confirm New Password'] as const).map((label, i) => {
            const vals = [current, next, confirm]
            const sets = [setCurrent, setNext, setConfirm]
            return (
              <div key={label}>
                <label className="block text-sm font-medium text-gray-700 mb-1">{label}</label>
                <input type="password" value={vals[i]} onChange={e => sets[i](e.target.value)} required
                  className="w-full border rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-dmpi-red" />
              </div>
            )
          })}
          {error && <p className="text-red-600 text-sm">{error}</p>}
          <button type="submit" disabled={loading}
            className="w-full bg-dmpi-red text-white py-2 rounded font-medium text-sm hover:bg-red-700 disabled:opacity-50">
            {loading ? 'Saving…' : 'Set New Password'}
          </button>
        </form>
      </div>
    </div>
  )
}
