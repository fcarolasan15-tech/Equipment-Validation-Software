const STATUS_COLORS: Record<string, string> = {
  DRAFT: 'bg-gray-100 text-gray-700',
  IN_REVIEW: 'bg-yellow-100 text-yellow-800',
  APPROVED: 'bg-green-100 text-green-800',
  REJECTED: 'bg-red-100 text-red-700',
  ACTIVE: 'bg-blue-100 text-blue-800',
  RELEASED: 'bg-purple-100 text-purple-800',
  OPEN: 'bg-red-100 text-red-700',
  CLOSED: 'bg-green-100 text-green-800',
  LOW: 'bg-green-100 text-green-800',
  MEDIUM: 'bg-yellow-100 text-yellow-800',
  HIGH: 'bg-red-100 text-red-700',
  PASS: 'bg-green-100 text-green-700',
  FAIL: 'bg-red-100 text-red-700',
  PENDING: 'bg-gray-100 text-gray-600',
  NA: 'bg-gray-100 text-gray-500',
  CRITICAL: 'bg-red-200 text-red-900 font-bold',
  MAJOR: 'bg-orange-100 text-orange-800',
  MINOR: 'bg-yellow-100 text-yellow-800',
  OBSERVATION: 'bg-blue-100 text-blue-700',
}

export default function Badge({ value }: { value: string }) {
  const cls = STATUS_COLORS[value] ?? 'bg-gray-100 text-gray-700'
  return (
    <span className={`inline-block px-2 py-0.5 rounded text-xs font-medium ${cls}`}>
      {value}
    </span>
  )
}
