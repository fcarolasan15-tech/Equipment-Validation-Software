import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { listRecords, createRecord, updateRecordData,
  submitForReview, signReview, approveRecord, rejectRecord,
  renderPdf, getRenderStatus, getAuditTrail, getSignatures,
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

const DEFAULT_FIELDS = [
  'equipment_name', 'model', 'manufacturer', 'serial_number',
  'department', 'location', 'date', 'document_number', 'revision',
]

interface Sig {
  role: string
  user_full_name: string
  meaning: string
  signed_at: string
}

function SignatureBlock({
  role, label, meaning: defaultMeaning, sig, active, onSign, disabled
}: {
  role: string
  label: string
  meaning: string
  sig?: Sig
  active: boolean
  onSign: (password: string, meaning: string) => Promise<void>
  disabled?: boolean
}) {
  const [pw, setPw] = useState('')
  const [meaning, setMeaning] = useState(defaultMeaning)
  const [loading, setLoading] = useState(false)
  const [err, setErr] = useState('')

  const handle = async () => {
    if (!pw) return
    setLoading(true)
    setErr('')
    try {
      await onSign(pw, meaning)
      setPw('')
    } catch (e: any) {
      setErr(e.response?.data?.detail || 'Signature failed')
    } finally { setLoading(false) }
  }

  return (
    <div className={`border rounded p-4 space-y-2 ${sig ? 'border-green-300 bg-green-50' : active ? 'border-dmpi-red bg-red-50' : 'border-gray-200 bg-gray-50'}`}>
      <div className="flex items-center gap-2">
        <span className={`text-xs font-bold uppercase tracking-wide ${sig ? 'text-green-700' : active ? 'text-dmpi-red' : 'text-gray-400'}`}>
          {sig ? '✓ ' : ''}{label}
        </span>
        {!sig && !active && <span className="text-xs text-gray-400">(pending prior step)</span>}
      </div>

      {sig ? (
        <div className="text-xs space-y-0.5">
          <p><span className="font-medium">Signed by:</span> {sig.user_full_name}</p>
          <p><span className="font-medium">Date/Time:</span> {new Date(sig.signed_at).toLocaleString()}</p>
          <p><span className="font-medium">Meaning:</span> {sig.meaning}</p>
          <p className="text-green-600 font-medium">Password verified ✓</p>
        </div>
      ) : active && !disabled ? (
        <div className="space-y-2">
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Signature Meaning</label>
            <input value={meaning} onChange={e => setMeaning(e.target.value)}
              className="w-full border rounded px-3 py-1.5 text-xs focus:ring-2 focus:ring-dmpi-red focus:outline-none" />
          </div>
          <div className="flex gap-2 items-center">
            <input type="password" placeholder="Enter your password" value={pw}
              onChange={e => setPw(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && handle()}
              className="flex-1 border rounded px-3 py-1.5 text-sm focus:ring-2 focus:ring-dmpi-red focus:outline-none" />
            <button onClick={handle} disabled={!pw || loading}
              className="bg-dmpi-red text-white px-3 py-1.5 rounded text-xs font-medium hover:bg-red-700 disabled:opacity-50 whitespace-nowrap">
              {loading ? 'Signing…' : 'Sign'}
            </button>
          </div>
          {err && <p className="text-red-600 text-xs">{err}</p>}
        </div>
      ) : null}
    </div>
  )
}

export default function RecordEditor() {
  const { id: projectId, stage } = useParams<{ id: string; stage: string }>()
  const navigate = useNavigate()
  const stageKey = (stage || '').toLowerCase()

  const [record, setRecord] = useState<any>(null)
  const [templates, setTemplates] = useState<any[]>([])
  const [fields, setFields] = useState<Record<string, string>>({})
  const [signatures, setSignatures] = useState<Sig[]>([])
  const [deviations, setDeviations] = useState<any[]>([])
  const [auditTrail, setAuditTrail] = useState<any[]>([])
  const [tab, setTab] = useState<'form' | 'signatures' | 'deviations' | 'audit' | 'pdf'>('form')
  const [saving, setSaving] = useState(false)
  const [renderJobId, setRenderJobId] = useState<number | null>(null)
  const [renderStatus, setRenderStatus] = useState<string>('')
  const [devForm, setDevForm] = useState({ description: '', severity: 'MINOR', root_cause: '', corrective_action: '', is_blocking: false })
  const [error, setError] = useState('')
  const [newField, setNewField] = useState('')

  const formCode = STAGE_TO_FORM[stageKey]

  const load = async () => {
    const recs = await listRecords(+projectId!)
    const existing = recs.data.find((r: any) => r.stage === stageKey.toUpperCase())
    if (existing) {
      setRecord(existing)
      setFields(existing.field_data || {})
      const [dev, audit, sigs] = await Promise.all([
        listDeviations(existing.id),
        getAuditTrail(existing.id),
        getSignatures(existing.id),
      ])
      setDeviations(dev.data)
      setAuditTrail(audit.data)
      setSignatures(sigs.data)
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
    setFields(DEFAULT_FIELDS.reduce((acc, k) => ({ ...acc, [k]: '' }), {}))
  }

  const save = async () => {
    if (!record) return
    setSaving(true)
    try {
      await updateRecordData(record.id, fields, 'Field update via form')
      await load()
    } finally { setSaving(false) }
  }

  const addField = () => {
    const key = newField.trim().toLowerCase().replace(/\s+/g, '_')
    if (!key || key in fields) return
    setFields(f => ({ ...f, [key]: '' }))
    setNewField('')
  }

  const removeField = (key: string) => {
    setFields(f => { const n = { ...f }; delete n[key]; return n })
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

  const sigFor = (role: string) => signatures.find(s => s.role === role)
  const hasPrepared = !!sigFor('PREPARED_BY')
  const hasReviewed = !!sigFor('REVIEWED_BY')
  const isApproved = record?.status === 'APPROVED'
  const isEditable = record && record.status !== 'APPROVED' && record.status !== 'IN_REVIEW'

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
          <div className="flex gap-1 border-b overflow-x-auto">
            {(['form', 'signatures', 'deviations', 'audit', 'pdf'] as const).map(t => (
              <button key={t} onClick={() => setTab(t)}
                className={`px-4 py-2 text-sm font-medium capitalize whitespace-nowrap border-b-2 transition-colors
                  ${tab === t ? 'border-dmpi-red text-dmpi-red' : 'border-transparent text-gray-500 hover:text-gray-700'}`}>
                {t === 'signatures' ? `Signatures (${signatures.length}/3)` :
                 t === 'deviations' && deviations.length > 0 ? `deviations (${deviations.length})` : t}
              </button>
            ))}
          </div>

          {tab === 'form' && (
            <div className="bg-white rounded shadow p-6 space-y-4">
              <div className="flex items-center justify-between flex-wrap gap-2">
                <p className="text-xs text-gray-400">
                  Doc No.: {record.document_number || '—'} | Rev: {record.revision} | Status: {record.status}
                </p>
                {record && (
                  <a href={`/api/records/${record.id}/download-filled`}
                    className="text-xs text-dmpi-red border border-dmpi-red px-3 py-1 rounded hover:bg-red-50">
                    ⬇ Download Filled Document
                  </a>
                )}
              </div>

              <div className="grid md:grid-cols-2 gap-3">
                {Object.keys(fields).map(k => (
                  <div key={k} className="relative group">
                    <label className="block text-xs font-medium text-gray-600 mb-1 capitalize">
                      {k.replace(/_/g, ' ')}
                    </label>
                    <div className="flex gap-1">
                      <input value={fields[k] || ''} onChange={e => setFields(f => ({ ...f, [k]: e.target.value }))}
                        disabled={!isEditable}
                        className="flex-1 border rounded px-3 py-2 text-sm focus:ring-2 focus:ring-dmpi-red focus:outline-none disabled:bg-gray-50" />
                      {isEditable && (
                        <button onClick={() => removeField(k)}
                          className="text-gray-300 hover:text-red-500 px-1 text-xs opacity-0 group-hover:opacity-100 transition-opacity">✕</button>
                      )}
                    </div>
                  </div>
                ))}
              </div>

              {isEditable && (
                <div className="flex gap-2 items-center border-t pt-3">
                  <input value={newField} onChange={e => setNewField(e.target.value)}
                    onKeyDown={e => e.key === 'Enter' && addField()}
                    placeholder="Add field name…"
                    className="border rounded px-3 py-1.5 text-sm focus:ring-2 focus:ring-dmpi-red focus:outline-none" />
                  <button onClick={addField}
                    className="text-xs border border-dmpi-red text-dmpi-red px-3 py-1.5 rounded hover:bg-red-50">+ Add Field</button>
                </div>
              )}

              {error && <p className="text-red-500 text-sm">{error}</p>}

              {isEditable && (
                <div className="flex gap-3 flex-wrap pt-2 border-t">
                  <button onClick={save} disabled={saving}
                    className="bg-gray-700 text-white px-4 py-2 rounded text-sm hover:bg-gray-800 disabled:opacity-50">
                    {saving ? 'Saving…' : 'Save Draft'}
                  </button>
                </div>
              )}
            </div>
          )}

          {tab === 'signatures' && (
            <div className="space-y-3">
              <div className="bg-blue-50 border border-blue-200 rounded p-3 text-xs text-blue-800">
                <strong>Electronic Signature Workflow</strong> — Three parties must sign in sequence before this document is approved.
                Each signature requires password re-entry and is permanently recorded in the audit trail (21 CFR Part 11).
              </div>

              <SignatureBlock
                role="PREPARED_BY"
                label="1. Prepared By (Author)"
                meaning="I confirm this document is complete and ready for review"
                sig={sigFor('PREPARED_BY')}
                active={record.status === 'DRAFT'}
                disabled={isApproved}
                onSign={async (pw, meaning) => {
                  await submitForReview(record.id, pw, meaning)
                  await load()
                }}
              />

              <SignatureBlock
                role="REVIEWED_BY"
                label="2. Reviewed By (Technical/QA)"
                meaning="I have reviewed this document and confirm its technical accuracy"
                sig={sigFor('REVIEWED_BY')}
                active={record.status === 'IN_REVIEW' && hasPrepared && !hasReviewed}
                disabled={isApproved}
                onSign={async (pw, meaning) => {
                  await signReview(record.id, pw, meaning)
                  await load()
                }}
              />

              <SignatureBlock
                role="APPROVED_BY"
                label="3. Approved By (QA Manager)"
                meaning="I approve this validation document"
                sig={sigFor('APPROVED_BY')}
                active={record.status === 'IN_REVIEW' && hasReviewed && !isApproved}
                disabled={isApproved}
                onSign={async (pw, meaning) => {
                  await approveRecord(record.id, pw, meaning)
                  await load()
                }}
              />

              {record.status === 'IN_REVIEW' && !isApproved && (
                <div className="pt-2">
                  <button onClick={reject}
                    className="bg-red-600 text-white px-4 py-2 rounded text-sm hover:bg-red-700">
                    Reject Document
                  </button>
                </div>
              )}
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
                  <div className="flex items-center gap-2 pt-4">
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
                    {deviations.length === 0 && (
                      <tr><td colSpan={5} className="px-4 py-6 text-center text-gray-400 text-sm">No deviations raised</td></tr>
                    )}
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
                      <td className="px-4 py-3 text-xs text-gray-500">{new Date(e.created_at).toLocaleString()}</td>
                      <td className="px-4 py-3 font-mono text-xs">{e.event_type}</td>
                      <td className="px-4 py-3 text-xs">{e.user_id}</td>
                      <td className="px-4 py-3 text-xs text-gray-500">{e.description}</td>
                    </tr>
                  ))}
                  {auditTrail.length === 0 && (
                    <tr><td colSpan={4} className="px-4 py-6 text-center text-gray-400 text-sm">No audit events</td></tr>
                  )}
                </tbody>
              </table>
            </div>
          )}

          {tab === 'pdf' && (
            <div className="bg-white rounded shadow p-6 space-y-4">
              <div className="bg-yellow-50 border border-yellow-200 rounded p-3 text-xs text-yellow-800">
                ⚠️ <strong>Printed copies are uncontrolled</strong> unless released by document control.
              </div>
              <div className="flex gap-3 flex-wrap">
                <button onClick={startRender}
                  className="bg-gray-700 text-white px-4 py-2 rounded text-sm hover:bg-gray-800">
                  Generate PDF
                </button>
                {record.current_pdf_path && (
                  <>
                    <a href={`/api/records/${record.id}/download-pdf`} target="_blank" rel="noreferrer"
                      className="bg-dmpi-red text-white px-4 py-2 rounded text-sm hover:bg-red-700">
                      ⬇ Download PDF
                    </a>
                    <button
                      onClick={() => {
                        const win = window.open(`/api/records/${record.id}/download-pdf`, '_blank')
                        win?.addEventListener('load', () => win.print())
                      }}
                      className="border border-gray-400 text-gray-700 px-4 py-2 rounded text-sm hover:bg-gray-50">
                      🖨 Print PDF
                    </button>
                  </>
                )}
              </div>
              {renderStatus && (
                <p className="text-sm text-gray-500">Render status: <Badge value={renderStatus} /></p>
              )}
              {record.current_pdf_hash && (
                <p className="text-xs text-gray-400 font-mono">SHA-256: {record.current_pdf_hash}</p>
              )}
            </div>
          )}
        </>
      )}
    </div>
  )
}
