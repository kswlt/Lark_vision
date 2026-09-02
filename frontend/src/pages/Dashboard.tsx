import { useEffect, useMemo, useState } from 'react'
import { useData } from '../store'
import CountdownRow from '../components/CountdownRow'
import KpiBar from '../components/KpiBar'
import MatrixTable from '../components/MatrixTable'
import Leaderboard from '../components/Leaderboard'
import SuperUrgent from '../components/SuperUrgent'
import TaskDrawer from '../components/TaskDrawer'
import TaskFeed from '../components/TaskFeed'
import { RobotBadge } from '../components/Badge'
import { fmtDate } from '../lib/format'
import { daysUntil } from '../lib/format'
import { seasonMilestones } from '../config/season'
import type { Milestone, Task } from '../types'

export default function Dashboard() {
  const { dashboard, tasks, loading } = useData()
  const [selected, setSelected] = useState<Task | null>(null)

  const timeline = useMemo(() => dashboard?.timeline ?? [], [dashboard])
  const milestones = useMemo<Milestone[]>(
    () =>
      seasonMilestones.map((m) => ({
        id: m.id,
        name: m.name,
        date: m.date,
        daysLeft: daysUntil(m.date),
        overdue: daysUntil(m.date) < 0,
        note: m.note
      })),
    []
  )

  return (
    <div className="p-5 space-y-4 max-w-[1500px]">
      {loading && tasks.length === 0 && (
        <div className="text-[11px] text-base-400 num-mono pulse-soft">加载中…</div>
      )}

      <CountdownRow milestones={milestones} />

      <div className="grid grid-cols-1 md:grid-cols-5 gap-4 items-stretch">
        <div className="md:col-span-2">
          <Leaderboard />
        </div>
        <div className="md:col-span-3 flex flex-col">
          <KpiBar counts={dashboard?.counts ?? null} />
        </div>
      </div>

      {/* 任务动态：合并为一条横贯全宽的长条，40 条横向滚动 */}
      <TaskFeed onOpen={setSelected} feed={tasks.slice(0, 40)} />

      {/* 超级紧急（左） + 未来 7 天（右） */}
      <div className="grid grid-cols-1 xl:grid-cols-5 gap-4 items-start">
        <div className="xl:col-span-2">
          <SuperUrgent onOpen={setSelected} />
        </div>
        <div className="xl:col-span-3 anim-enter-slow" style={{ animationDelay: '100ms' }}>
          <div className="panel-title mb-2">未来 7 天</div>
          <div className="panel p-3 grid grid-cols-1 md:grid-cols-2 gap-x-6 gap-y-1.5">
            {timeline.length === 0 && (
              <div className="text-[12px] text-base-400 py-3">未来 7 天无到期任务</div>
            )}
            {timeline.map((t, i) => (
              <button
                key={t.id}
                onClick={() => setSelected(t)}
                className="flex items-center gap-3 px-2 py-1 rounded hover:bg-base-800 text-left clickable anim-enter"
                style={{ animationDelay: `${i * 50}ms` }}
              >
                <span className="num-mono text-[11px] text-base-300 w-12 shrink-0">
                  {t.dueDate ? fmtDate(t.dueDate) : '--'}
                </span>
                <span className="flex-1 text-[12px] text-gray-300 truncate">{t.title}</span>
                <RobotBadge robot={t.robot} />
                {t.overdue && <span className="text-[10px] text-red-400 shrink-0 pulse-soft">已延期</span>}
              </button>
            ))}
          </div>
        </div>
      </div>

      <div className="anim-enter-slow" style={{ animationDelay: '140ms' }}>
        <div className="panel-title mb-2">组别 × 兵种矩阵</div>
        <MatrixTable matrix={dashboard?.matrix ?? []} />
      </div>

      <TaskDrawer task={selected} onClose={() => setSelected(null)} />
    </div>
  )
}
