import { useMemo } from 'react'
import { Flag, Radio } from 'lucide-react'
import { useData } from '../store'
import { GroupBadge, RobotBadge } from './Badge'
import { fmtDate } from '../lib/format'
import type { Task } from '../types'

function statusOf(t: Task): { label: string; cls: string } | null {
  if (t.blocked) return { label: '阻塞', cls: 'text-red-400' }
  if (t.overdue) return { label: `已延期${t.overdueDays ?? ''}天`, cls: 'text-red-400' }
  if (t.priority === 'important_urgent') return { label: '重要紧急', cls: 'text-amber-400' }
  if (t.daysSinceUpdate !== undefined && t.daysSinceUpdate >= 3)
    return { label: `${t.daysSinceUpdate}日未更新`, cls: 'text-amber-400' }
  return null
}

/** 首页任务动态：从右向左横向自动滚动的任务卡片流（样式贴近任务中心卡片） */
export default function TaskFeed({
  onOpen,
  feed,
  title
}: {
  onOpen: (t: Task) => void
  feed?: Task[]
  title?: string
}) {
  const { tasks } = useData()
  // 传入 feed 时不再截断（供首页合并成一长条）；未传入时默认取前 20 条
  const items = useMemo(
    () => (feed !== undefined ? feed : tasks.slice(0, 20)),
    [feed, tasks]
  )
  if (items.length === 0) return null
  const doubled = [...items, ...items]

  return (
    <div className="panel hud-frame flex flex-col anim-enter-slow">
      <div className="flex items-center gap-1.5 px-4 pt-3 pb-2 border-b border-base-600">
        <Radio size={13} className="text-accent-bright pulse-soft" />
        <span className="panel-title">{title ?? '任务动态'}</span>
        <span className="ml-auto num-mono text-[10px] text-base-400">{items.length} 条</span>
      </div>
      <div className="overflow-hidden px-3 py-2.5">
        <div className="ticker-h-track">
          {doubled.map((t, i) => {
            const st = statusOf(t)
            return (
              <button
                key={t.id + '-' + i}
                onClick={() => onOpen(t)}
                className="w-[300px] shrink-0 text-left flex flex-col gap-1.5 rounded-md border border-base-600 bg-base-850 px-3 py-2.5 hover:border-accent-dim/70 hover:bg-base-800 clickable anim-enter"
              >
                <div className="flex items-center gap-2">
                  <span className="num-mono text-[11px] text-accent-bright font-semibold shrink-0">
                    {t.id}
                  </span>
                  <GroupBadge group={t.group} />
                  <RobotBadge robot={t.robot} />
                  {st && (
                    <span className={`ml-auto text-[10px] shrink-0 ${st.cls}`}>{st.label}</span>
                  )}
                </div>
                <span className="text-[14px] text-gray-200 leading-snug line-clamp-2 font-medium">
                  {t.title}
                </span>
                {t.latestUpdate && (
                  <span className="text-[12px] text-base-300 leading-snug line-clamp-1 truncate">
                    最新：{t.latestUpdate}
                  </span>
                )}
                <div className="mt-auto flex items-center gap-1.5 pt-1">
                  <span className="truncate font-semibold text-gray-100 text-[14px]">{t.ownerName || '未分配'}</span>
                  <span className="text-base-400 text-[12px]">·</span>
                  <span className="flex items-center gap-0.5 shrink-0 text-[12px] text-base-300">
                    <Flag size={12} />
                    {t.dueDate ? fmtDate(t.dueDate) : '—'}
                  </span>
                </div>
              </button>
            )
          })}
        </div>
      </div>
    </div>
  )
}
