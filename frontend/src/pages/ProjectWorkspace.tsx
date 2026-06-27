import { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { getProject, advanceStage, getStageGates } from '../api/projects'
import { listRecords, createRecord } from '../api/records'
import Badge from '../components/Badge'
import StagePipeline from '../components/StagePipeline'

const STAGE_FORMS: Record<string, { label: string; form_code: string }> = {
  DQ: { label: 'Design Qualification Workbook', form_code: 'F-FSR-02' },
  PROTOCOL: { label: 'Equipment & Validation Protocol (F-FSR-01)', form_code: 'F-FSR-01' },
  IQ: { label: 'Installation Qualification (F-FSR-03)', form_code: 'F-FSR-03' },
  OQ: { label: 'Operational Qualification (F-FSR-04)', form_code: 'F-FSR-04' },
  PQ: { label: 'Performance Qualification (F-FSR-05)', form_code: 'F-FSR-05' },
  REPORT: { label: 'Equipment Validation Report (F-FSR-06)', form_code: 'F-FSR-06' },
}

export default function ProjectWorkspace() {
  const { id } = useParams<{ id: string }>()
  const [project, setProject] = useState<any>(null)
  const [records, setRecords] = useState<any[]>([])
  const [gates, setGates] = useState<any[]>([])
  const [advancing, setAdvancing] = useState(false)
  const [error, setError] = useState('')

  const load = () => {
    if (!id) return
    Promise.all([getProject(+id), listRecords(+id), getStageGates(+id)]).then(([p, r, g]) => {
      setProject(p.data)
      setRecords(r.data)
      setGates(g.data)
    })
  }

  useEffect(() => { load() }, [id])

  const advance = async (stage: string) => {
    setAdvancing(true)
    setError('')
    try {
      await advanceStage(+id!, stage)
      load()
    } catch (e: any) {
      setError(e.response?.data?.detail || 'Cannot advance stage')
    } finally {
      setAdvancing(false)
    }
  }

  if (!project) return <p className="text-gray-400">Loading…</p>

  const stageRecords = (stage: string) => records.filter(r => r.stage === stage)

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-2 flex-wrap">
        <Link to="/projects" className="text-sm text-gray-500 hover:underline">← Projects</Link>
        <span className="text-gray-300">/</span>
        <h1 className="text-xl font-bold">{project.title}</h1>
        <span className="font-mono text-xs bg-gray-100 px-2 py-0.5 rounded">{project.project_number}</span>
        <Badge value={project.status} />
      </div>

      <div className="bg-white rounded shadow p-4">
        <h2 className="text-sm font-semibold text-gray-600 mb-3">Stage Pipeline</h2>
        <StagePipeline current={project.current_stage} />
        <div className="mt-3 flex items-center gap-3">
          {gates.map((g: any) => (
            <div key={g.next_stage} className="flex items-center gap-2">
              <button
                onClick={() => advance(g.next_stage)}
                disabled={!g.can_advance || advancing}
                className="text-sm px-4 py-1.5 rounded bg-dmpi-green text-white disabled:opacity-40 disabled:cursor-not-allowed hover:bg-green-700">
                Advance to {g.next_stage} →
              </button>
              {!g.can_advance && g.reason && (
                <span className="text-xs text-red-500">{g.reason}</span>
              )}
            </div>
          ))}
          {error && <span className="text-xs text-red-500">{error}</span>}
        </div>
      </div>

      <div className="grid md:grid-cols-3 gap-3 text-sm">
        <div className="bg-white rounded shadow p-3">
          <div className="text-gray-500 text-xs mb-1">Qualification Scope</div>
          {['IQ', 'OQ', 'PQ'].map(s => (
            <div key={s} className="flex justify-between py-0.5">
              <span className="font-medium">{s}</span>
              <Badge value={(project as any)[`scope_${s.toLowerCase()}`]} />
            </div>
          ))}
        </div>
        <div className="bg-white rounded shadow p-3 col-span-2">
          <div className="text-gray-500 text-xs mb-1">Notes</div>
          <p className="text-sm text-gray-700">{project.notes || 'No notes'}</p>
        </div>
      </div>

      <div className="space-y-3">
        {Object.entries(STAGE_FORMS).map(([stage, info]) => {
          const recs = stageRecords(stage)
          const isCurrentOrPast = ['DQ','PROTOCOL','IQ','OQ','PQ','REPORT','RELEASED'].indexOf(project.current_stage) >=
            ['DQ','PROTOCOL','IQ','OQ','PQ','REPORT','RELEASED'].indexOf(stage)
          return (
            <div key={stage} className={`bg-white rounded shadow ${!isCurrentOrPast ? 'opacity-50' : ''}`}>
              <div className="px-4 py-3 border-b flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="font-mono text-xs bg-gray-100 px-1.5 py-0.5 rounded">{stage}</span>
                  <span className="font-semibold text-sm">{info.label}</span>
                </div>
                {isCurrentOrPast && (
                  <Link to={`/projects/${id}/records/${stage.toLowerCase()}`}
                    className="text-xs text-dmpi-red hover:underline">
                    {recs.length > 0 ? 'Open Record →' : 'Create Record →'}
                  </Link>
                )}
              </div>
              {recs.length > 0 ? (
                <div className="px-4 py-2 text-xs text-gray-500 flex gap-4">
                  <span>Rev: {recs[0].revision}</span>
                  <Badge value={recs[0].status} />
                  {recs[0].approved_at && <span>Approved: {new Date(recs[0].approved_at).toLocaleDateString()}</span>}
                </div>
              ) : isCurrentOrPast ? (
                <div className="px-4 py-2 text-xs text-gray-400">No record yet — click to create</div>
              ) : (
                <div className="px-4 py-2 text-xs text-gray-300">Locked — complete prior stages first</div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
