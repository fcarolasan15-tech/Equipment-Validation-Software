import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { createProject } from '../api/projects'
import { listAssets, getRecommendedScope } from '../api/assets'

const SCOPE_OPTIONS = ['REQUIRED', 'OPTIONAL', 'NOT_REQUIRED']

export default function ProjectNew() {
  const navigate = useNavigate()
  const [assets, setAssets] = useState<any[]>([])
  const [form, setForm] = useState({
    title: '', asset_id: '', site_id: 1,
    scope_iq: 'REQUIRED', scope_oq: 'REQUIRED', scope_pq: 'REQUIRED',
    scope_justification: '', notes: '',
  })
  const [scopeHint, setScopeHint] = useState<any>(null)
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    listAssets().then(r => setAssets(r.data))
  }, [])

  const set = (k: string) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) =>
    setForm(f => ({ ...f, [k]: e.target.value }))

  const onAssetChange = async (assetId: string) => {
    setForm(f => ({ ...f, asset_id: assetId }))
    if (!assetId) return
    try {
      const r = await getRecommendedScope(+assetId)
      if (r.data.recommended_scope) {
        setScopeHint(r.data)
        setForm(f => ({
          ...f,
          scope_iq: r.data.recommended_scope.iq,
          scope_oq: r.data.recommended_scope.oq,
          scope_pq: r.data.recommended_scope.pq,
        }))
      }
    } catch { setScopeHint(null) }
  }

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    setSaving(true)
    try {
      const payload = { ...form, asset_id: +form.asset_id }
      const res = await createProject(payload)
      navigate(`/projects/${res.data.id}`)
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Error creating project')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="max-w-2xl space-y-4">
      <h1 className="text-xl font-bold">New Validation Project</h1>
      <form onSubmit={submit} className="bg-white rounded shadow p-6 space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Project Title *</label>
          <input value={form.title} onChange={set('title')} required
            className="w-full border rounded px-3 py-2 text-sm focus:ring-2 focus:ring-dmpi-red focus:outline-none" />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Asset *</label>
          <select value={form.asset_id} onChange={e => onAssetChange(e.target.value)} required
            className="w-full border rounded px-3 py-2 text-sm">
            <option value="">— Select Asset —</option>
            {assets.map(a => (
              <option key={a.id} value={a.id}>[{a.asset_tag}] {a.equipment_name}</option>
            ))}
          </select>
        </div>

        {scopeHint && (
          <div className="p-3 bg-blue-50 rounded text-xs text-blue-700">
            <strong>Auto-suggested scope</strong> based on Risk Level: <strong>{scopeHint.risk_level}</strong>,
            URS Impact: <strong>{scopeHint.urs_impact}</strong>, Score: <strong>{scopeHint.risk_score}</strong>
          </div>
        )}

        <div className="grid grid-cols-3 gap-4">
          {(['scope_iq', 'scope_oq', 'scope_pq'] as const).map(k => (
            <div key={k}>
              <label className="block text-sm font-medium text-gray-700 mb-1">{k.replace('scope_', '').toUpperCase()} Scope</label>
              <select value={form[k]} onChange={set(k)}
                className="w-full border rounded px-3 py-2 text-sm">
                {SCOPE_OPTIONS.map(o => <option key={o}>{o}</option>)}
              </select>
            </div>
          ))}
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Scope Justification</label>
          <textarea value={form.scope_justification} onChange={set('scope_justification')} rows={2}
            className="w-full border rounded px-3 py-2 text-sm focus:ring-2 focus:ring-dmpi-red focus:outline-none" />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Notes</label>
          <textarea value={form.notes} onChange={set('notes')} rows={2}
            className="w-full border rounded px-3 py-2 text-sm focus:ring-2 focus:ring-dmpi-red focus:outline-none" />
        </div>

        {error && <p className="text-red-600 text-sm">{error}</p>}
        <div className="flex gap-3">
          <button type="submit" disabled={saving}
            className="bg-dmpi-red text-white px-6 py-2 rounded text-sm hover:bg-red-700 disabled:opacity-50">
            {saving ? 'Creating…' : 'Create Project'}
          </button>
          <button type="button" onClick={() => navigate('/projects')}
            className="px-6 py-2 rounded text-sm border hover:bg-gray-50">Cancel</button>
        </div>
      </form>
    </div>
  )
}
