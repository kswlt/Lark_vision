import { X, CalendarCheck, CalendarX2, Flag, Link2, NotebookText, User } from 'lucide-react'
import type { Task } from '../types'
import Avatar from './Avatar'
import {
  BlockedBadge,
  GroupBadge,
  OverdueBadge,
  PriorityBadge,
  RobotBadge,
  StaleBadge
} from './Badge'
import { fmtDate } from '../lib/format'

interface TaskDrawerProps {
  task: Task | null
  onClose: () => void
}

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex items-start gap-3 py-1.5 border-b border-base-700 last:border-0">
      <span className="kv-label w-20 shrink-0 pt-0.5">{label}</span>
      <div className="flex-1 text-[12px] text-gray-200 flex flex-wrap items-center gap-1.5 min-w-0">
        {children}
      </div>
    </div>
  )
}

export default function TaskDrawer({ task, onClose }: TaskDrawerProps) {
  if (!task) return null
  return (
    <div className="fixed inset-0 z-40">
      <div className="absolute inset-0 bg-black/50" onClick={onClose} />
      <div className="absolute right-0 top-0 h-full w-[440px] max-w-[92vw] bg-base-850 border-l border-base-600 shadow-2xl flex flex-col">
        <div className="flex items-center justify-between px-5 py-4 border-b border-base-600">
          <div className="flex items-center gap-2">
            <span className="num-mono text-accent-bright font-bold text-[13px]">{task.id}</span>
            <span className="text-[10px] tracking-[0.2em] text-base-400 uppercase">任务详情</span>
          </div>
          <button onClick={onClose} className="text-base-300 hover:text-gray-100">
            <X size={18} />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto px-5 py-4 space-y-4">
          <h2 className="text-[15px] leading-relaxed text-gray-100 font-medium">{task.title}</h2>

          <div className="flex items-center gap-1.5 flex-wrap">
            <GroupBadge group={task.group} />
            <RobotBadge robot={task.robot} />
            <PriorityBadge priority={task.priority} />
            {task.blocked && <BlockedBadge />}
            {task.overdue && <OverdueBadge days={task.overdueDays} />}
            {task.daysSinceUpdate !== undefined && task.daysSinceUpdate >= 3 && (
              <StaleBadge days={task.daysSinceUpdate} />
            )}
          </div>

          <div className="panel p-3">
            <Row label="组别">{task.group ?? '未指定'}</Row>
            <Row label="兵种">{task.robot ?? '未指定'}</Row>
            <Row label="负责人">
              <span className="flex items-center gap-1.5">
                <Avatar name={task.ownerName} url={task.ownerAvatarUrl} size={18} />
                {task.ownerName || '未指定'}
              </span>
            </Row>
            <Row label="计划完成">
              <Flag size={12} className="text-base-400" />
              <span className="num-mono">{task.dueDate ? fmtDate(task.dueDate) : '--'}</span>
            </Row>
            <Row label="实际完成">
              {task.actualFinishDate ? (
                <>
                  <CalendarCheck size={12} className="text-accent-bright" />
                  <span className="num-mono">{fmtDate(task.actualFinishDate)}</span>
                </>
              ) : (
                <span className="text-base-400">未完成</span>
              )}
            </Row>
            <Row label="延期情况">
              {task.overdue ? (
                <span className="flex items-center gap-1 text-red-400">
                  <CalendarX2 size={12} />
                  已延期 {task.overdueDays ?? ''} 天
                </span>
              ) : (
                <span className="text-base-400">未延期</span>
              )}
            </Row>
            <Row label="依赖">
              {task.dependency ? (
                <span className="flex items-center gap-1">
                  <Link2 size={12} className="text-base-400" />
                  {task.dependency}
                </span>
              ) : (
                <span className="text-base-400">无</span>
              )}
            </Row>
          </div>

          {task.latestUpdate && (
            <div>
              <div className="panel-title mb-1.5 flex items-center gap-1">
                <NotebookText size={11} />
                最新进展
                {task.latestUpdateTime && (
                  <span className="num-mono normal-case ml-auto">
                    {task.latestUpdateTime.replace('T', ' ').slice(0, 16)}
                  </span>
                )}
              </div>
              <div className="panel p-3 text-[12px] leading-relaxed text-gray-300 whitespace-pre-wrap">
                {task.latestUpdate}
              </div>
            </div>
          )}

          {task.history && task.history.length > 0 && (
            <div>
              <div className="panel-title mb-1.5">进展历史</div>
              <div className="panel p-3 space-y-2">
                {task.history.map((h, i) => (
                  <div key={i} className="flex gap-2 text-[11px]">
                    <span className="num-mono text-base-400 shrink-0 w-14 text-right">
                      {h.time ? h.time.replace('T', ' ').slice(5, 16) : ''}
                    </span>
                    <span className="text-gray-400">{h.text}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          <div className="flex items-center gap-1.5 text-[10px] text-base-400">
            <User size={11} />
            {task.ownerId ? `user:${task.ownerId}` : 'owner:未指定'} · 数据源：飞书任务表
          </div>
        </div>
      </div>
    </div>
  )
}
