import { Clock, Flag, Link2, NotebookText } from 'lucide-react'
import type { Task } from '../types'
import Avatar from './Avatar'
import { GroupBadge, OverdueBadge, PriorityBadge, RobotBadge, StaleBadge, BlockedBadge } from './Badge'
import { fmtAgo, fmtDate } from '../lib/format'

interface TaskCardProps {
  task: Task
  onOpen: (task: Task) => void
}

export default function TaskCard({ task, onOpen }: TaskCardProps) {
  return (
    <div
      onClick={() => onOpen(task)}
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

      <p className="text-[13px] leading-snug text-gray-200 line-clamp-2">{task.title}</p>

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

      <div className="flex items-center gap-3 text-[10px] text-base-300 pt-0.5">
        <span className="flex items-center gap-1">
          <Avatar name={task.ownerName} url={task.ownerAvatarUrl} size={16} />
          {task.ownerName || '未指定'}
        </span>
        <span className="flex items-center gap-1 num-mono">
          <Flag size={11} className="text-base-400" />
          {task.dueDate ? fmtDate(task.dueDate) : '--'}
        </span>
        {task.dependency && (
          <span className="flex items-center gap-1 truncate max-w-[120px]">
            <Link2 size={11} className="text-base-400" />
            {task.dependency}
          </span>
        )}
        <span className="ml-auto flex items-center gap-1 num-mono text-base-300">
          <Clock size={11} />
          {task.daysSinceUpdate === undefined ? '--' : fmtAgo(task.daysSinceUpdate)}
        </span>
      </div>
    </div>
  )
}
