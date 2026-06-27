import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { listRecords } from '../api/records'
import { listProjects } from '../api/projects'
import Badge from '../components/Badge'

export default function ApprovalQueue() {
  const [items, setItems] = useState<any[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.all([listRecords(), listProjects()]).then(([recs, projs]) => {
      const projMap: Record<number, any> = {}
      projs.data.forEach((p: any) => { projMap[p.id] = p })
      const pending = recs.data.filter((r: any) => r.status === 'IN_REVIEW')
      setItems(pending.map((r: any) => ({ ...r, project: projMap[r.project_id] })))
    }).finally(() => setLoading(false))
  }, [])

  return (
    <div className="space-y-4">
      <h1 className="text-xl font-bold">Approval Queue</h1>
      {loading ? <p className="text-gray-400">Loading…</p> : items.length === 0
        ? <p className="text-gray-400 bg-white rounded shadow p-6 text-center">No records pending approval.</p>
        : (
          <div className="bg-white rounded shadow overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 text-xs text-gray-500 uppercase">
                <tr>
                  {['Project', 'Stage', 'Doc No.', 'Status', 'Action'].map(h => (
                    <th key={h} className="px-4 py-2 text-left">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y">
                {items.map(r => (
                  <tr key={r.id} className="hover:bg-gray-50">
                    <td className="px-4 py-3">
                      <div className="font-medium">{r.project?.title}</div>
                      <div className="text-xs text-gray-400">{r.project?.project_number}</div>
                    </td>
                    <td className="px-4 py-3 font-mono text-xs">{r.stage}</td>
                    <td className="px-4 py-3 text-xs">{r.document_number || '—'}</td>
                    <td className="px-4 py-3"><Badge value={r.status} /></td>
                    <td className="px-4 py-3">
                      <Link to={`/projects/${r.project_id}/records/${r.stage.toLowerCase()}`}
                        className="text-xs bg-dmpi-red text-white px-3 py-1 rounded hover:bg-red-700">
                        Review →
                      </Link>
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
