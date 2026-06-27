import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { listRecords, createRecord, getRecord, updateRecordData, submitForReview,
  approveRecord, rejectRecord, renderPdf, getRenderStatus, getAuditTrail,
  listDeviations, createDeviation, closeDeviation } from '../api/records'
import api from '../api/client'
import Badge from '../components/Badge'

const STAGE_TO_FORM: Record<string, string> = {
  dq: 'F-FSR-02', protocol: 'F-FSR-01', iq: 'F-FSR-03',
  oq: 'F-FSR-04', pq: 'F-FSR-05', report: 'F-FSR-06',
}

const STAGE_LABELS: Record<string, string> = {
  dq: 'Design Qualification (F-FSR-02)',
  protocol: 'Equipment & Validation Protocol (F-FSR-01)',
  iq: 'Installation Qualification (F-FSR-03)',
  oq: 'Operational Qualification (F-FSR-04)',
  pq: 'Performance Qualification (F-FSR-05)',
  report: 'Equipment Validation Report (F-FSR-06)',
}

export default function RecordEditor() {
  const { id: projectId, stage } = useParams<{ id: string; stage: string }>()
  const navigate = useNavigate()
  const stageKey = (stage || '').toLowerCase()

  const [record, setRecord] = useState<any>(null)
  const [templates, setTemplates] = useState<any[]>([])
  const [fields, setFields] = useState<Record<string, string>>({})
  const [deviations, setDeviations] = useState<any[]>([])
  const [auditTrail, setAuditTrail] = useState<any[]>([])
  const [tab, setTab] = useState<'form' | 'deviations' | 'audit' | 'pdf'>('form')
  const [approvalPassword, setApprovalPassword] = useState('')
  const [saving, setSaving] = useState(false)
  const [renderJobId, setRenderJobId] = useState<number | null>(null)
  const [renderStatus, setRenderStatus] = useState<string>('')
  const [devForm, setDevForm] = useState({ description: '', severity: 'MINOR', root_cause: '', corrective_action: '', is_blocking: false })
  const [error, setError] = useState('')

  const formCode = STAGE_TO_FORM[stageKey]

  const load = async () => {
    const recs = await listRecords(+projectId!)
    const existing = recs.data.find((r: any) => r.stage === stageKey.toUpperCase())
    if (existing) {
      setRecord(existing)
      setFields(existing.field_data || {})
      const [dev, audit] = await Promise.all([listDeviations(existing.id), getAuditTrail(existing.id)])
      setDeviations(dev.data)
      setAuditTrail(audit.data)
    }
    const tpls = await api.get('/templates')
    setTemplates(tpls.data.filter((t: any) => t.form_code === formCode && t.status === 'APPROVED'))
  }

  useEffect(() => { load() }, [projectId, stage])

  const createNew = async () => {
    if (templates.length === 0) {
      setError(`No approved ${formCode} template found. Register and approve a template first.`)
      return
    }
    const r = await createRecord({
      project_id: +projectId!,
      template_version_id: templates[0].id,
      stage: stageKey.toUpperCase(),
    })
    setRecord(r.data)
    setFields({})
  }

  const save = async () => {
    if (!record) return
    setSaving(true)
    try {
      await updateRecordData(record.id, fields, 'Field update via form')
      await load()
    } finally { setSaving(false) }
  }

  const submit = async () => {
    if (!record) return
    await submitForReview(record.id)
    await load()
  }

  const approve = async () => {
    if (!record || !approvalPassword) return
    try {
      await approveRecord(record.id, approvalPassword, 'I approve this validation document')
      setApprovalPassword('')
      await load()
    } catch (e: any) {
      setError(e.response?.data?.detail || 'Approval failed')
    }
  }

  const reject = async () => {
    if (!record) return
    await rejectRecord(record.id)
    await load()
  }

  const startRender = async () => {
    if (!record) return
    const r = await renderPdf(record.id)
    setRenderJobId(r.data.job_id)
    setRenderStatus('PENDING')
    const poll = setInterval(async () => {
      const s = await getRenderStatus(record.id, r.data.job_id)
      setRenderStatus(s.data.status)
      if (s.data.status === 'COMPLETE' || s.data.status === 'FAILED') {
        clearInterval(poll)
        await load()
      }
    }, 2000)
  }

  const submitDev = async () => {
    if (!record) return
    await createDeviation(record.id, { ...devForm, record_id: record.id })
    setDevForm({ description: '', severity: 'MINOR', root_cause: '', corrective_action: '', is_blocking: false })
    const dev = await listDeviations(record.id)
    setDeviations(dev.data)
  }

  const closeDev = async (devId: number) => {
    if (!record) return
    await closeDeviation(record.id, devId)
    const dev = await listDeviations(record.id)
    setDeviations(dev.data)
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2 flex-wrap">
        <button onClick={() => navigate(`/projects/${projectId}`)} className="text-sm text-gray-500 hover:underline">← Project</button>
        <span className="text-gray-300">/</span>
        <h1 className="text-xl font-bold">{STAGE_LABELS[stageKey] || stageKey.toUpperCase()}</h1>
        {record && <Badge value={record.status} />}
      </div>

      {!record ? (
        <div className="bg-white rounded shadow p-6 text-center">
          <p className="text-gray-500 mb-4">No record exists for this stage yet.</p>
          {error && <p className="text-red-500 text-sm mb-3">{error}</p>}
          <button onClick={createNew}
            className="bg-dmpi-red text-white px-6 py-2 rounded text-sm hover:bg-red-700">
            Create {stageKey.toUpperCase()} Record
          </button>
        </div>
      ) : (
        <>
          <div className="flex gap-1 border-b">
            {(['form', 'deviations', 'audit', 'pdf'] as const).map(t => (
              <button key={t} onClick={() => setTab(t)}
                className={`px-4 py-2 text-sm font-medium capitalize border-b-2 transition-colors
                  ${tab === t ? 'border-dmpi-red text-dmpi-red' : 'border-transparent text-gray-500 hover:text-gray-700'}`}>
                {t}{t === 'deviations' && deviations.length > 0 ? ` (${deviations.length})` : ''}
              </button>
            ))}
          </div>

          {tab === 'form' && (
            <div className="bg-white rounded shadow p-6 space-y-4">
              <p className="text-xs text-gray-400">
                Document No.: {record.document_number || '—'} | Rev: {record.revision} | Status: {record.status}
              </p>
              <div className="space-y-3">
                {Object.keys(fields).length === 0 && (
                  <div className="grid md:grid-cols-2 gap-3">
                    {['equipment_name', 'model', 'manufacturer', 'serial_number', 'department',
                      'prepared_by', 'reviewed_by', 'approved_by', 'date', 'location'].map(k => (
                      <div key={k}>
                        <label className="block text-xs font-medium text-gray-600 mb-1 capitalize">
                          {k.replace(/_/g, ' ')}
                        </label>
                        <input value={fields[k] || ''} onChange={e => setFields(f => ({ ...f, [k]: e.target.value }))}
                          disabled={record.status === 'APPROVED'}
                          className="w-full border rounded px-3 py-2 text-sm focus:ring-2 focus:ring-dmpi-red focus:outline-none disabled:bg-gray-50" />
                      </div>
                    ))}
                  </div>
                )}
                {Object.keys(fields).length > 0 && (
                  <div className="grid md:grid-cols-2 gap-3">
                    {Object.keys(fields).map(k => (
                      <div key={k}>
                        <label className="block text-xs font-medium text-gray-600 mb-1 capitalize">
                          {k.replace(/_/g, ' ')}
                        </label>
                        <input value={fields[k] || ''} onChange={e => setFields(f => ({ ...f, [k]: e.target.value }))}
                          disabled={record.status === 'APPROVED'}
                          className="w-full border rounded px-3 py-2 text-sm focus:ring-2 focus:ring-dmpi-red focus:outline-none disabled:bg-gray-50" />
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {record.status !== 'APPROVED' && (
                <div className="flex gap-3 flex-wrap pt-2">
                  <button onClick={save} disabled={saving}
                    className="bg-gray-700 text-white px-4 py-2 rounded text-sm hover:bg-gray-800 disabled:opacity-50">
                    {saving ? 'Saving…' : 'Save Draft'}
                  </button>
                  {record.status === 'DRAFT' && (
                    <button onClick={submit}
                      className="bg-yellow-600 text-white px-4 py-2 rounded text-sm hover:bg-yellow-700">
                      Submit for Review
                    </button>
                  )}
                  {record.status === 'IN_REVIEW' && (
                    <>
                      <div className="flex items-center gap-2">
                        <input type="password" placeholder="Enter password to approve" value={approvalPassword}
                          onChange={e => setApprovalPassword(e.target.value)}
                          className="border rounded px-3 py-2 text-sm focus:ring-2 focus:ring-green-500 focus:outline-none" />
                        <button onClick={approve}
                          className="bg-green-700 text-white px-4 py-2 rounded text-sm hover:bg-green-800">
                          Approve (e-Signature)
                        </button>
                      </div>
                      <button onClick={reject}
                        className="bg-red-600 text-white px-4 py-2 rounded text-sm hover:bg-red-700">
                        Reject
                      </button>
                    </>
                  )}
                </div>
              )}
              {error && <p className="text-red-500 text-sm">{error}</p>}
            </div>
          )}

          {tab === 'deviations' && (
            <div className="space-y-4">
              <div className="bg-white rounded shadow p-4">
                <h3 className="font-semibold text-sm mb-3">Raise Deviation</h3>
                <div className="grid md:grid-cols-2 gap-3 text-sm">
                  <div className="md:col-span-2">
                    <label className="block text-xs font-medium text-gray-600 mb-1">Description *</label>
                    <textarea value={devForm.description} onChange={e => setDevForm(f => ({ ...f, description: e.target.value }))}
                      rows={2} className="w-full border rounded px-3 py-2 text-sm focus:ring-2 focus:ring-dmpi-red focus:outline-none" />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-gray-600 mb-1">Severity</label>
                    <select value={devForm.severity} onChange={e => setDevForm(f => ({ ...f, severity: e.target.value }))}
                      className="w-full border rounded px-3 py-2 text-sm">
                      {['CRITICAL', 'MAJOR', 'MINOR', 'OBSERVATION'].map(s => <option key={s}>{s}</option>)}
                    </select>
                  </div>
                  <div className="flex items-center gap-2">
                    <input type="checkbox" id="blocking" checked={devForm.is_blocking}
                      onChange={e => setDevForm(f => ({ ...f, is_blocking: e.target.checked }))} />
                    <label htmlFor="blocking" className="text-sm">Blocking (prevents PQ advance)</label>
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-gray-600 mb-1">Root Cause</label>
                    <input value={devForm.root_cause} onChange={e => setDevForm(f => ({ ...f, root_cause: e.target.value }))}
                      className="w-full border rounded px-3 py-2 text-sm" />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-gray-600 mb-1">Corrective Action</label>
                    <input value={devForm.corrective_action} onChange={e => setDevForm(f => ({ ...f, corrective_action: e.target.value }))}
                      className="w-full border rounded px-3 py-2 text-sm" />
                  </div>
                </div>
                <button onClick={submitDev} disabled={!devForm.description}
                  className="mt-3 bg-dmpi-red text-white px-4 py-2 rounded text-sm hover:bg-red-700 disabled:opacity-50">
                  Raise Deviation
                </button>
              </div>

              <div className="bg-white rounded shadow overflow-hidden">
                <table className="w-full text-sm">
                  <thead className="bg-gray-50 text-xs text-gray-500 uppercase">
                    <tr>
                      {['#', 'Description', 'Severity', 'Status', 'Action'].map(h => (
                        <th key={h} className="px-4 py-2 text-left">{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="divide-y">
                    {deviations.map((d: any) => (
                      <tr key={d.id}>
                        <td className="px-4 py-3 font-mono text-xs">{d.deviation_number}</td>
                        <td className="px-4 py-3">{d.description}</td>
                        <td className="px-4 py-3"><Badge value={d.severity} /></td>
                        <td className="px-4 py-3"><Badge value={d.status} /></td>
                        <td className="px-4 py-3">
                          {d.status !== 'CLOSED' && (
                            <button onClick={() => closeDev(d.id)}
                              className="text-xs text-green-700 hover:underline">Close</button>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {tab === 'audit' && (
            <div className="bg-white rounded shadow overflow-hidden">
              <table className="w-full text-sm">
                <thead className="bg-gray-50 text-xs text-gray-500 uppercase">
                  <tr>
                    {['Timestamp', 'Event', 'User', 'Description'].map(h => (
                      <th key={h} className="px-4 py-2 text-left">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {auditTrail.map((e: any) => (
                    <tr key={e.id}>
                      <td className="px-4 py-3 text-xs text-gray-500">
                        {new Date(e.created_at).toLocaleString()}
                      </td>
                      <td className="px-4 py-3 font-mono text-xs">{e.event_type}</td>
                      <td className="px-4 py-3 text-xs">{e.user_id}</td>
                      <td className="px-4 py-3 text-xs text-gray-500">{e.description}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {tab === 'pdf' && (
            <div className="bg-white rounded shadow p-6 space-y-4">
              <div className="bg-yellow-50 border border-yellow-200 rounded p-3 text-xs text-yellow-800">
                ⚠️ <strong>Printed copies are uncontrolled</strong> unless released by document control.
              </div>
              <div className="flex gap-3">
                <button onClick={startRender}
                  className="bg-gray-700 text-white px-4 py-2 rounded text-sm hover:bg-gray-800">
                  Generate PDF
                </button>
                {record.current_pdf_path && (
                  <a href={`/api/records/${record.id}/download-pdf`} target="_blank" rel="noreferrer"
                    className="bg-dmpi-red text-white px-4 py-2 rounded text-sm hover:bg-red-700">
                    Download PDF
                  </a>
                )}
              </div>
              {renderStatus && (
                <p className="text-sm text-gray-500">Render status: <Badge value={renderStatus} /></p>
              )}
              {record.current_pdf_hash && (
                <p className="text-xs text-gray-400 font-mono">PDF SHA-256: {record.current_pdf_hash}</p>
              )}
            </div>
          )}
        </>
      )}
    </div>
  )
}
