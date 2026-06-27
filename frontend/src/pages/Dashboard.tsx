import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { listProjects } from '../api/projects'
import { listAssets } from '../api/assets'
import Badge from '../components/Badge'
import StagePipeline from '../components/StagePipeline'

export default function Dashboard() {
  const [projects, setProjects] = useState<any[]>([])
  const [assets, setAssets] = useState<any[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.all([listProjects(), listAssets()]).then(([p, a]) => {
      setProjects(p.data)
      setAssets(a.data)
    }).finally(() => setLoading(false))
  }, [])

  const active = projects.filter(p => p.status === 'ACTIVE')
  const completed = projects.filter(p => p.status === 'COMPLETED')
  const highRisk = assets.filter(a => a.risk_level === 'HIGH')

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-800">Validation Dashboard</h1>
        <p className="text-sm text-gray-500">Del Monte Philippines Inc. — Equipment Validation Management</p>
      </div>

      {loading ? <p className="text-gray-400">Loading…</p> : (
        <>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {[
              { label: 'Active Projects', value: active.length, color: 'border-l-blue-500' },
              { label: 'Completed', value: completed.length, color: 'border-l-green-500' },
              { label: 'Total Assets', value: assets.length, color: 'border-l-gray-400' },
              { label: 'High Risk Assets', value: highRisk.length, color: 'border-l-red-500' },
            ].map(s => (
              <div key={s.label} className={`bg-white rounded shadow p-4 border-l-4 ${s.color}`}>
                <div className="text-2xl font-bold">{s.value}</div>
                <div className="text-xs text-gray-500 mt-1">{s.label}</div>
              </div>
            ))}
          </div>

          <div className="bg-white rounded shadow overflow-hidden">
            <div className="px-4 py-3 border-b flex items-center justify-between">
              <h2 className="font-semibold text-gray-700">Active Projects</h2>
              <Link to="/projects/new" className="text-xs bg-dmpi-red text-white px-3 py-1 rounded hover:bg-red-700">
                + New Project
              </Link>
            </div>
            {active.length === 0
              ? <p className="text-gray-400 text-sm p-4">No active projects.</p>
              : (
                <table className="w-full text-sm">
                  <thead className="bg-gray-50 text-xs text-gray-500 uppercase">
                    <tr>
                      {['#', 'Title', 'Stage', 'Status'].map(h => (
                        <th key={h} className="px-4 py-2 text-left">{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="divide-y">
                    {active.map(p => (
                      <tr key={p.id} className="hover:bg-gray-50">
                        <td className="px-4 py-3">
                          <Link to={`/projects/${p.id}`} className="text-dmpi-red font-mono font-medium">
                            {p.project_number}
                          </Link>
                        </td>
                        <td className="px-4 py-3">{p.title}</td>
                        <td className="px-4 py-3">
                          <StagePipeline current={p.current_stage} />
                        </td>
                        <td className="px-4 py-3"><Badge value={p.status} /></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
          </div>
        </>
      )}
    </div>
  )
}
