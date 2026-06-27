import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { listAssets } from '../api/assets'
import Badge from '../components/Badge'

export default function AssetList() {
  const [assets, setAssets] = useState<any[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    listAssets().then(r => setAssets(r.data)).finally(() => setLoading(false))
  }, [])

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold">Asset Register</h1>
        <Link to="/assets/new" className="bg-dmpi-red text-white text-sm px-4 py-2 rounded hover:bg-red-700">
          + Register Asset
        </Link>
      </div>

      {loading ? <p className="text-gray-400">Loading…</p> : (
        <div className="bg-white rounded shadow overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-xs text-gray-500 uppercase">
              <tr>
                {['Tag', 'Equipment Name', 'Department', 'Risk Score', 'Risk Level', 'URS Impact', ''].map(h => (
                  <th key={h} className="px-4 py-2 text-left">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y">
              {assets.map(a => (
                <tr key={a.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 font-mono text-xs">{a.asset_tag}</td>
                  <td className="px-4 py-3 font-medium">{a.equipment_name}</td>
                  <td className="px-4 py-3 text-gray-500">{a.department_code || '—'}</td>
                  <td className="px-4 py-3">{a.risk_score ?? '—'}</td>
                  <td className="px-4 py-3">{a.risk_level ? <Badge value={a.risk_level} /> : '—'}</td>
                  <td className="px-4 py-3">{a.urs_impact ? <Badge value={a.urs_impact} /> : '—'}</td>
                  <td className="px-4 py-3">
                    <Link to={`/assets/${a.id}`} className="text-dmpi-red text-xs hover:underline">View</Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
