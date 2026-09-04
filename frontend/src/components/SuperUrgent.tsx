import { useMemo } from 'react'
import { Siren, ClockAlert } from 'lucide-react'
import { useData } from '../store'
import { fmtDate } from '../lib/format'
import type { Task } from '../types'

/** 超级紧急任务：表格"重要紧急程度 = 超紧急限时"的任务，显眼高亮闪烁。
 *  若无该档数据，回退展示"重要紧急 + 已延期"的最紧急任务，保证白板有内容。 */
export default function SuperUrgent({ onOpen }: { onOpen: (t: Task) => void }) {
  const { tasks } = useData()
  const list = useMemo(() => {
    const active = tasks.filter((t) => {
      const s = t.status || ''
      if (s.includes('完成') || s.includes('停滞') || s.includes('停止')) return false
      return true
    })
    const superList = active.filter((t) => t.priority === 'super_urgent')
    if (superList.length) return superList.slice(0, 6)
    return active
      .filter((t) => t.priority === 'important_urgent' && t.overdue)
      .slice(0, 6)
  }, [tasks])

  return (
    <div className="panel hud-frame px-3 py-2 flex flex-col anim-enter-slow">
      <div className="flex items-center justify-between mb-1.5">
        <span className="flex items-center gap-1.5 text-[13px] font-black tracking-[0.14em] text-red-600">
          <Siren size={14} className="pulse-soft" />
          超级紧急
        </span>
        <span className="text-[10px] text-red-400 font-bold">{list.length} 项</span>
      </div>

      {list.length === 0 ? (
        <div className="text-[11px] text-base-400 py-3 text-center">暂无超紧急任务</div>
      ) : (
        <div className="space-y-1.5">
          {list.map((t, i) => (
            <button
              key={t.id}
              onClick={() => onOpen(t)}
              className="w-full text-left urgent-blink rounded-md border px-2.5 py-1.5 card-lift anim-enter"
              style={{ animationDelay: `${i * 60}ms` }}
            >
              <div className="flex items-center gap-2">
                <span className="num-mono text-[11px] font-bold text-red-600 shrink-0">
                  {t.id}
                </span>
                {t.overdue && (
                  <span className="flex items-center gap-0.5 text-[10px] text-red-600 font-bold shrink-0">
                    <ClockAlert size={9} />
                    已延期{t.overdueDays ?? ''}天
                  </span>
                )}
                <span className="text-[9px] text-red-500 font-bold shrink-0 ml-auto">
                  超紧急限时
                </span>
              </div>
              <span className="block text-[12px] font-semibold text-gray-800 leading-snug line-clamp-2 mt-0.5">
                {t.title}
              </span>
              <div className="mt-0.5 flex items-center gap-1 text-[10px] text-gray-500">
                <span>{t.ownerName || '未分配'}</span>
                <span>·</span>
                <span>{t.dueDate ? fmtDate(t.dueDate) : '—'}</span>
              </div>
            </button>
          ))}
        </div>
      )}
    </div>
  )
}
