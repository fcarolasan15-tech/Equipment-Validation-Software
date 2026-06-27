const STAGES = ['INITIATION', 'DQ', 'PROTOCOL', 'IQ', 'OQ', 'PQ', 'REPORT', 'RELEASED']

export default function StagePipeline({ current }: { current: string }) {
  const idx = STAGES.indexOf(current)
  return (
    <div className="flex items-center gap-0 flex-wrap">
      {STAGES.map((s, i) => {
        const done = i < idx
        const active = i === idx
        return (
          <div key={s} className="flex items-center">
            <div className={`px-2 py-1 text-xs font-semibold rounded
              ${active ? 'bg-dmpi-red text-white' : done ? 'bg-green-600 text-white' : 'bg-gray-200 text-gray-500'}`}>
              {s}
            </div>
            {i < STAGES.length - 1 && (
              <div className={`w-4 h-0.5 ${i < idx ? 'bg-green-600' : 'bg-gray-300'}`} />
            )}
          </div>
        )
      })}
    </div>
  )
}
