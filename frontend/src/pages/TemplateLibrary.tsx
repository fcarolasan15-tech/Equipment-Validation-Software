import { useEffect, useState } from 'react'
import api from '../api/client'
import Badge from '../components/Badge'

export default function TemplateLibrary() {
  const [templates, setTemplates] = useState<any[]>([])
  const [form, setForm] = useState({ form_code: 'F-FSR-01', version: '01', title: '' })
  const [uploading, setUploading] = useState<number | null>(null)
  const [creating, setCreating] = useState(false)
  const [error, setError] = useState('')

  const load = () => api.get('/templates').then(r => setTemplates(r.data))
  useEffect(() => { load() }, [])

  const createVersion = async (e: React.FormEvent) => {
    e.preventDefault()
    setCreating(true)
    try {
      await api.post('/templates', form)
      setForm(f => ({ ...f, version: '', title: '' }))
      await load()
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Error')
    } finally { setCreating(false) }
  }

  const approve = async (id: number) => {
    await api.post(`/templates/${id}/approve`)
    await load()
  }

  const uploadFile = async (id: number, file: File) => {
    setUploading(id)
    const fd = new FormData()
    fd.append('file', file)
    try {
      await api.post(`/templates/${id}/upload-file`, fd)
      await load()
    } finally { setUploading(null) }
  }

  const FORM_CODES = ['F-FSR-01', 'F-FSR-02', 'F-FSR-03', 'F-FSR-04', 'F-FSR-05', 'F-FSR-06']

  return (
    <div className="space-y-6">
      <h1 className="text-xl font-bold">Template Library</h1>

      <div className="bg-white rounded shadow p-5">
        <h2 className="font-semibold text-gray-700 mb-3">Register New Template Version</h2>
        <form onSubmit={createVersion} className="flex gap-3 flex-wrap items-end">
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Form Code</label>
            <select value={form.form_code} onChange={e => setForm(f => ({ ...f, form_code: e.target.value }))}
              className="border rounded px-3 py-2 text-sm">
              {FORM_CODES.map(c => <option key={c}>{c}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Version</label>
            <input value={form.version} onChange={e => setForm(f => ({ ...f, version: e.target.value }))} required
              className="border rounded px-3 py-2 text-sm w-20" placeholder="01" />
          </div>
          <div className="flex-1 min-w-48">
            <label className="block text-xs font-medium text-gray-600 mb-1">Title</label>
            <input value={form.title} onChange={e => setForm(f => ({ ...f, title: e.target.value }))} required
              className="w-full border rounded px-3 py-2 text-sm" />
          </div>
          <button type="submit" disabled={creating}
            className="bg-dmpi-red text-white px-4 py-2 rounded text-sm hover:bg-red-700 disabled:opacity-50">
            Create
          </button>
        </form>
        {error && <p className="text-red-500 text-xs mt-2">{error}</p>}
      </div>

      <div className="bg-white rounded shadow overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 text-xs text-gray-500 uppercase">
            <tr>
              {['Form', 'Version', 'Title', 'Files', 'Status', 'Actions'].map(h => (
                <th key={h} className="px-4 py-2 text-left">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y">
            {templates.map(t => (
              <tr key={t.id} className="hover:bg-gray-50">
                <td className="px-4 py-3 font-mono text-xs font-medium">{t.form_code}</td>
                <td className="px-4 py-3">v{t.version}</td>
                <td className="px-4 py-3">{t.title}</td>
                <td className="px-4 py-3">
                  <span className="text-gray-500 text-xs">{t.file_count} file(s)</span>
                  <label className="ml-2 cursor-pointer text-xs text-dmpi-red hover:underline">
                    Upload
                    <input type="file" className="sr-only"
                      accept=".docx,.xlsx"
                      disabled={uploading === t.id}
                      onChange={e => e.target.files?.[0] && uploadFile(t.id, e.target.files[0])} />
                  </label>
                  {uploading === t.id && <span className="ml-1 text-xs text-gray-400">uploading…</span>}
                </td>
                <td className="px-4 py-3"><Badge value={t.status} /></td>
                <td className="px-4 py-3">
                  {t.status === 'DRAFT' && (
                    <button onClick={() => approve(t.id)}
                      className="text-xs bg-green-700 text-white px-2 py-1 rounded hover:bg-green-800">
                      Approve
                    </button>
                  )}
                  {t.status === 'APPROVED' && (
                    <span className="text-xs text-green-600">✓ Active</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
