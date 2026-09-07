import { Flag, Link2, NotebookText } from 'lucide-react'
import type { Task } from '../types'
import Avatar from './Avatar'
import { GroupBadge, OverdueBadge, PriorityBadge, RobotBadge, StaleBadge, BlockedBadge } from './Badge'
import { daysUntil, fmtDate } from '../lib/format'

interface TaskCardProps {
  task: Task
  onOpen: (task: Task) => void
}

/** 距截止越近越红、闪烁越明显：0=正常 1=≤10天 2=≤7天 3=≤3天 4=已逾期 */
function urgencyOf(task: Task): { level: number; days: number | null } {
  const days = task.dueDate ? daysUntil(task.dueDate) : null
  if (task.overdue || (days !== null && days < 0)) return { level: 4, days: days ?? -1 }
  if (days === null) return { level: 0, days: null }
  if (days <= 3) return { level: 3, days }
  if (days <= 7) return { level: 2, days }
  if (days <= 10) return { level: 1, days }
  return { level: 0, days }
}

const URGENCY_STYLE: Record<number, React.CSSProperties> = {
  0: {},
  1: { background: 'rgba(248,113,113,.05)', animation: 'rm-urgency 2.2s ease-in-out infinite' },
  2: { background: 'rgba(248,113,113,.10)', animation: 'rm-urgency 1.5s ease-in-out infinite' },
  3: { background: 'rgba(248,113,113,.18)', animation: 'rm-urgency 1.0s ease-in-out infinite' },
  4: { background: 'rgba(239,68,68,.32)', animation: 'rm-urgency 0.55s ease-in-out infinite' }
}

export default function TaskCard({ task, onOpen }: TaskCardProps) {
  const { level, days } = urgencyOf(task)
  const style = URGENCY_STYLE[level]
  return (
    <div
      onClick={() => onOpen(task)}
      style={style}
      className="panel clickable p-3 flex flex-col gap-2 hover:bg-base-800 card-lift"
    >
      <div className="flex items-center gap-2 flex-wrap">
        <span className="num-mono text-[11px] text-accent-bright font-semibold">{task.id}</span>
        <GroupBadge group={task.group} />
        <RobotBadge robot={task.robot} />
        <div className="ml-auto flex items-center gap-1.5">
          <PriorityBadge priority={task.priority} />
          {task.blocked && <BlockedBadge />}
          {task.overdue && <OverdueBadge days={task.overdueDays} />}
          {!task.overdue && task.daysSinceUpdate !== undefined && task.daysSinceUpdate >= 3 && (
            <StaleBadge days={task.daysSinceUpdate} />
          )}
        </div>
      </div>

      <p className="text-[15px] font-semibold leading-snug text-gray-100 line-clamp-2">{task.title}</p>

      {task.latestUpdate && (
        <div className="bg-base-800 rounded px-2 py-1.5 border border-base-600">
          <div className="flex items-center gap-1 text-[9px] text-base-400 tracking-[0.15em] uppercase mb-0.5">
            <NotebookText size={10} />
            最新进展
            {task.latestUpdateTime && (
              <span className="num-mono ml-auto">
                {task.latestUpdateTime.replace('T', ' ').slice(5, 16)}
              </span>
            )}
          </div>
          <p className="text-[11px] text-gray-400 leading-snug line-clamp-2">{task.latestUpdate}</p>
        </div>
      )}

      <div className="flex items-center gap-3 text-[10px] text-base-300 pt-3">
        <span className="flex items-center gap-1">
          <Avatar name={task.ownerName} url={task.ownerAvatarUrl} size={16} />
          {task.ownerName || '未指定'}
        </span>
        {level > 0 && days !== null && (
          <span
            className={`num-mono text-[14px] font-black tracking-wide ${
              level >= 3 ? 'text-red-400' : 'text-red-300'
            }`}
          >
            {days < 0 ? `逾期${-days}天` : `还剩${days}天`}
          </span>
        )}
        {task.dependency && (
          <span className="flex items-center gap-1 truncate max-w-[120px]">
            <Link2 size={11} className="text-base-400" />
            {task.dependency}
          </span>
        )}
        <span className="ml-auto flex items-center gap-1.5 num-mono text-[15px] font-bold text-gray-100">
          <Flag size={15} className="text-gray-300" />
          {task.dueDate ? fmtDate(task.dueDate) : '--'}
        </span>
      </div>
    </div>
  )
}
