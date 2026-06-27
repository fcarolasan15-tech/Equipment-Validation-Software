import { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { getAsset, updateRisk, getRecommendedScope } from '../api/assets'
import Badge from '../components/Badge'

const METRICS = [
  { key: 'metric_food_safety', label: 'Food Safety / HACCP', conforming: 'Non-CCP/OPRP, Quality, Regulatory', nonconforming: 'CCP / OPRP, Quality, Regulatory' },
  { key: 'metric_downtime', label: 'Machine Downtime', conforming: 'Monthly unscheduled DT < 1200 min', nonconforming: 'Monthly unscheduled DT ≥ 1200 min' },
  { key: 'metric_age', label: 'Age Profile', conforming: '< 10 years in service', nonconforming: '≥ 10 years in service' },
  { key: 'metric_pm_conformance', label: 'PM Plan Conformance', conforming: '100% conformance to PM Plan', nonconforming: '< 100% or no conformance' },
  { key: 'metric_calibration', label: 'Calibration Status', conforming: 'All critical sensors calibrated (or N/A)', nonconforming: 'Past calibration due > 30 days' },
  { key: 'metric_validation_status', label: 'Validation Status', conforming: 'Validated (Thermal or DQ) or N/A', nonconforming: 'Not yet validated' },
  { key: 'metric_spare_parts', label: 'Spare Parts Availability', conforming: 'Critical spares on-site / storeroom', nonconforming: 'Lead time > 7 days' },
  { key: 'metric_safety_systems', label: 'Safety Systems', conforming: 'LOTO / guards / emergency-stop functional', nonconforming: 'Missing or malfunctioning' },
]

const URS_IMPACT_OPTIONS = ['DIRECT', 'INDIRECT', 'SAFETY', 'NONE']

export default function AssetDetail() {
  const { id } = useParams<{ id: string }>()
  const [asset, setAsset] = useState<any>(null)
  const [scope, setScope] = useState<any>(null)
  const [metrics, setMetrics] = useState<Record<string, number>>({})
  const [ursImpact, setUrsImpact] = useState('')
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    if (!id) return
    getAsset(+id).then(r => {
      setAsset(r.data)
      const m: Record<string, number> = {}
      METRICS.forEach(({ key }) => { m[key] = r.data[key] ?? 1 })
      setMetrics(m)
      setUrsImpact(r.data.urs_impact || 'DIRECT')
    })
    getRecommendedScope(+id).then(r => setScope(r.data)).catch(() => {})
  }, [id])

  const save = async () => {
    setSaving(true)
    try {
      await updateRisk(+id!, { ...metrics, urs_impact: ursImpact })
      const [a, s] = await Promise.all([getAsset(+id!), getRecommendedScope(+id!)])
      setAsset(a.data)
      setScope(s.data)
    } finally {
      setSaving(false)
    }
  }

  if (!asset) return <p className="text-gray-400">Loading…</p>

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-2">
        <Link to="/assets" className="text-sm text-gray-500 hover:underline">← Assets</Link>
        <span className="text-gray-300">/</span>
        <h1 className="text-xl font-bold">{asset.equipment_name}</h1>
        <span className="font-mono text-xs bg-gray-100 px-2 py-0.5 rounded">{asset.asset_tag}</span>
      </div>

      <div className="grid md:grid-cols-2 gap-6">
        <div className="bg-white rounded shadow p-4 space-y-2 text-sm">
          <h2 className="font-semibold text-gray-700 mb-3">Asset Details</h2>
          {[
            ['Model', asset.model], ['Manufacturer', asset.manufacturer],
            ['Serial No.', asset.serial_number], ['Department', asset.department],
            ['Location', asset.location], ['Year Installed', asset.year_installed],
          ].map(([l, v]) => (
            <div key={l as string} className="flex justify-between border-b pb-1">
              <span className="text-gray-500">{l}</span>
              <span className="font-medium">{v || '—'}</span>
            </div>
          ))}
        </div>

        <div className="bg-white rounded shadow p-4 space-y-2 text-sm">
          <h2 className="font-semibold text-gray-700 mb-3">Risk Summary</h2>
          <div className="flex justify-between items-center">
            <span className="text-gray-500">Risk Score</span>
            <span className="text-2xl font-bold">{asset.risk_score}</span>
          </div>
          <div className="flex justify-between items-center">
            <span className="text-gray-500">Risk Level</span>
            {asset.risk_level ? <Badge value={asset.risk_level} /> : <span className="text-gray-400">—</span>}
          </div>
          <div className="flex justify-between items-center">
            <span className="text-gray-500">URS Impact</span>
            {asset.urs_impact ? <Badge value={asset.urs_impact} /> : <span className="text-gray-400">—</span>}
          </div>
          {scope?.recommended_scope && (
            <div className="mt-3 p-3 bg-blue-50 rounded text-xs space-y-1">
              <div className="font-semibold text-blue-700">Recommended Qualification Scope</div>
              {['iq', 'oq', 'pq'].map(s => (
                <div key={s} className="flex justify-between">
                  <span className="uppercase font-medium">{s}</span>
                  <Badge value={scope.recommended_scope[s]} />
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      <div className="bg-white rounded shadow p-4">
        <h2 className="font-semibold text-gray-700 mb-4">Risk Assessment — 8 Metrics</h2>
        <p className="text-xs text-gray-400 mb-4">Score 1 = Conforming, 2 = Non-Conforming. Risk Score = product of all 8 metrics (range: 1–256)</p>

        <div className="space-y-3">
          {METRICS.map(m => (
            <div key={m.key} className="border rounded p-3">
              <div className="font-medium text-sm mb-2">{m.label}</div>
              <div className="flex gap-4 text-xs">
                <label className={`flex items-center gap-1.5 cursor-pointer px-2 py-1 rounded
                  ${metrics[m.key] === 1 ? 'bg-green-100 text-green-800 ring-1 ring-green-400' : 'text-gray-500 hover:bg-gray-50'}`}>
                  <input type="radio" name={m.key} value={1} checked={metrics[m.key] === 1}
                    onChange={() => setMetrics(prev => ({ ...prev, [m.key]: 1 }))} className="sr-only" />
                  <span>✓ Conforming — {m.conforming}</span>
                </label>
                <label className={`flex items-center gap-1.5 cursor-pointer px-2 py-1 rounded
                  ${metrics[m.key] === 2 ? 'bg-red-100 text-red-800 ring-1 ring-red-400' : 'text-gray-500 hover:bg-gray-50'}`}>
                  <input type="radio" name={m.key} value={2} checked={metrics[m.key] === 2}
                    onChange={() => setMetrics(prev => ({ ...prev, [m.key]: 2 }))} className="sr-only" />
                  <span>✗ Non-Conforming — {m.nonconforming}</span>
                </label>
              </div>
            </div>
          ))}
        </div>

        <div className="mt-4 flex items-center gap-4">
          <div>
            <label className="text-sm font-medium text-gray-700 mr-2">URS Impact:</label>
            <select value={ursImpact} onChange={e => setUrsImpact(e.target.value)}
              className="border rounded px-2 py-1 text-sm">
              {URS_IMPACT_OPTIONS.map(o => <option key={o}>{o}</option>)}
            </select>
          </div>
          <button onClick={save} disabled={saving}
            className="bg-dmpi-red text-white px-4 py-2 rounded text-sm hover:bg-red-700 disabled:opacity-50">
            {saving ? 'Saving…' : 'Save Risk Assessment'}
          </button>
        </div>
      </div>
    </div>
  )
}
