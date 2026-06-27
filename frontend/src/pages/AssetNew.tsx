import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { createAsset } from '../api/assets'

const DEPARTMENTS = [
  { department: 'Pineapple Preparation Department', section: 'Receiving', code: 'RCV' },
  { department: 'Pineapple Preparation Department', section: 'Packing Table', code: 'PCT' },
  { department: 'Solids Processing Department', section: 'Cook Room', code: 'SPC' },
  { department: 'Solids Processing Department', section: 'Crush', code: 'SPR' },
  { department: 'Tropical Products Department', section: '', code: 'TPD' },
  { department: 'Juice and Drinks', section: '', code: 'JND' },
  { department: 'Liquids Processing Department', section: '', code: 'LPD' },
  { department: 'Tetra and Flexible Packaging Department', section: 'Flexible Packaging', code: 'FPD' },
  { department: 'Tetra and Flexible Packaging Department', section: 'Tetra', code: 'TET' },
  { department: 'Packaging Operations Department', section: '', code: 'POD' },
  { department: 'Brite Warehouse Department', section: '', code: 'BWD' },
  { department: 'Can Plant Department', section: '', code: 'CPD' },
  { department: 'Utilities Department', section: 'RACCA / Instrumentation', code: 'MIR' },
  { department: 'Utilities Department', section: 'Powerplant', code: 'MPP' },
  { department: 'Research and Development Department', section: 'Fruits, Beverage, Packaging', code: 'RND' },
  { department: 'Corporate Quality Management', section: 'Food Safety, Quality and Regulatory', code: 'FSR' },
  { department: 'Corporate Quality Management', section: 'Manufacturing QA', code: 'MQA' },
]

export default function AssetNew() {
  const navigate = useNavigate()
  const [form, setForm] = useState({
    site_id: 1, asset_tag: '', equipment_name: '', model: '',
    manufacturer: '', serial_number: '', department: '', department_code: '',
    location: '', year_installed: '',
  })
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)

  const set = (k: string) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) =>
    setForm(f => ({ ...f, [k]: e.target.value }))

  const selectDept = (code: string) => {
    const d = DEPARTMENTS.find(d => d.code === code)
    if (d) setForm(f => ({ ...f, department_code: code, department: d.section ? `${d.department} — ${d.section}` : d.department }))
  }

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    setSaving(true)
    try {
      const payload = { ...form, year_installed: form.year_installed ? +form.year_installed : undefined }
      const res = await createAsset(payload)
      navigate(`/assets/${res.data.id}`)
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Error creating asset')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="max-w-2xl space-y-4">
      <h1 className="text-xl font-bold">Register New Asset</h1>
      <form onSubmit={submit} className="bg-white rounded shadow p-6 space-y-4">
        <div className="grid md:grid-cols-2 gap-4">
          {[
            { label: 'Asset Tag *', key: 'asset_tag', required: true },
            { label: 'Equipment Name *', key: 'equipment_name', required: true },
            { label: 'Model', key: 'model' },
            { label: 'Manufacturer', key: 'manufacturer' },
            { label: 'Serial Number', key: 'serial_number' },
            { label: 'Location', key: 'location' },
            { label: 'Year Installed', key: 'year_installed' },
          ].map(f => (
            <div key={f.key}>
              <label className="block text-sm font-medium text-gray-700 mb-1">{f.label}</label>
              <input value={(form as any)[f.key]} onChange={set(f.key)} required={f.required}
                className="w-full border rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-dmpi-red" />
            </div>
          ))}

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Department</label>
            <select value={form.department_code} onChange={e => selectDept(e.target.value)}
              className="w-full border rounded px-3 py-2 text-sm">
              <option value="">— Select —</option>
              {DEPARTMENTS.map(d => (
                <option key={d.code} value={d.code}>
                  [{d.code}] {d.department}{d.section ? ` — ${d.section}` : ''}
                </option>
              ))}
            </select>
          </div>
        </div>

        {error && <p className="text-red-600 text-sm">{error}</p>}
        <div className="flex gap-3">
          <button type="submit" disabled={saving}
            className="bg-dmpi-red text-white px-6 py-2 rounded text-sm hover:bg-red-700 disabled:opacity-50">
            {saving ? 'Registering…' : 'Register Asset'}
          </button>
          <button type="button" onClick={() => navigate('/assets')}
            className="px-6 py-2 rounded text-sm border hover:bg-gray-50">
            Cancel
          </button>
        </div>
      </form>
    </div>
  )
}
