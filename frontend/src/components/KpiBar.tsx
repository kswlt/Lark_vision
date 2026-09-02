import { useCountUp } from '../lib/useCountUp'

interface KpiBarProps {
  counts: {
    total: number
    overdue: number
    critical: number
    blocked: number
    stale: number
    dueSoon: number
  } | null
}

interface KpiItem {
  key: 'total' | 'overdue' | 'critical' | 'blocked' | 'stale' | 'dueSoon'
  label: string
  color: string
}

const ITEMS: KpiItem[] = [
  { key: 'total', label: '任务', color: 'text-gray-200' },
  { key: 'overdue', label: '已延期', color: 'text-red-400' },
  { key: 'critical', label: '重要紧急', color: 'text-amber-400' },
  { key: 'blocked', label: '阻塞', color: 'text-red-400' },
  { key: 'stale', label: '久未更新', color: 'text-amber-400' },
  { key: 'dueSoon', label: '近期截止', color: 'text-accent-bright' }
]

function KpiCell({ item, value, delay }: { item: KpiItem; value: number; delay: number }) {
  const v = useCountUp(value)
  return (
    <div
      className="panel p-2.5 flex flex-col items-center justify-center gap-1 anim-enter"
      style={{ animationDelay: `${delay}ms` }}
    >
      <span className={`num-mono text-4xl font-bold leading-none ${item.color}`}>
        {String(v).padStart(2, '0')}
      </span>
      <span className="text-[10px] tracking-[0.2em] text-base-300 mt-1">{item.label}</span>
    </div>
  )
}

export default function KpiBar({ counts }: KpiBarProps) {
  if (!counts) return null
  return (
    <div className="flex-1 grid grid-cols-3 sm:grid-cols-6 gap-3">
      {ITEMS.map((item, i) => (
        <KpiCell key={item.key} item={item} value={counts[item.key]} delay={i * 60} />
      ))}
    </div>
  )
}
