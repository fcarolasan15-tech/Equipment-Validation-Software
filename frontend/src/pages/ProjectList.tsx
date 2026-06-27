import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { listProjects } from '../api/projects'
import Badge from '../components/Badge'
import StagePipeline from '../components/StagePipeline'

export default function ProjectList() {
  const [projects, setProjects] = useState<any[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    listProjects().then(r => setProjects(r.data)).finally(() => setLoading(false))
  }, [])

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold">Validation Projects</h1>
        <Link to="/projects/new" className="bg-dmpi-red text-white text-sm px-4 py-2 rounded hover:bg-red-700">
          + New Project
        </Link>
      </div>

      {loading ? <p className="text-gray-400">Loading…</p> : (
        <div className="bg-white rounded shadow overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-xs text-gray-500 uppercase">
              <tr>
                {['Project No.', 'Title', 'Current Stage', 'Status', ''].map(h => (
                  <th key={h} className="px-4 py-2 text-left">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y">
              {projects.map(p => (
                <tr key={p.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 font-mono text-xs font-medium text-dmpi-red">{p.project_number}</td>
                  <td className="px-4 py-3">{p.title}</td>
                  <td className="px-4 py-3"><StagePipeline current={p.current_stage} /></td>
                  <td className="px-4 py-3"><Badge value={p.status} /></td>
                  <td className="px-4 py-3">
                    <Link to={`/projects/${p.id}`} className="text-dmpi-red text-xs hover:underline">Open</Link>
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
