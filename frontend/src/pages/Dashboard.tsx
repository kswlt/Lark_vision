import { useEffect, useMemo, useState } from 'react'
import { useData } from '../store'
import CountdownRow from '../components/CountdownRow'
import DutyRoster from '../components/DutyRoster'
import MatrixTable from '../components/MatrixTable'
import Leaderboard from '../components/Leaderboard'
import SuperUrgent from '../components/SuperUrgent'
import TaskDrawer from '../components/TaskDrawer'
import TaskFeed from '../components/TaskFeed'
import UncheckedTicker from '../components/UncheckedTicker'
import CameraPanel from '../components/CameraPanel'
import { RobotBadge } from '../components/Badge'
import { fmtDate } from '../lib/format'
import { daysUntil } from '../lib/format'
import { seasonMilestones } from '../config/season'
import type { Milestone, Task } from '../types'

export default function Dashboard() {
  const { dashboard, tasks, loading } = useData()
  const [selected, setSelected] = useState<Task | null>(null)

  // 过滤掉已停滞 / 已完成的任务（只展示进行中的安排）
  const activeTasks = useMemo(
    () =>
      tasks.filter((t) => {
        const s = t.status || ''
        if (s.includes('完成') || s.includes('停滞') || s.includes('停止')) return false
        return true
      }),
    [tasks]
  )
  const timeline = useMemo(() => (dashboard?.timeline ?? []).filter((t) => activeTasks.includes(t)), [dashboard, activeTasks])

  // 任务动态：按"活跃度"排序（有最新进展 > 紧急 > 延期 > 未完成 > 表格顺序），
  // 让飞书里刚更新/推进的任务浮到动态前部，而不是固定取表格前 40 条。
  const feed = useMemo(() => {
    const score = (t: Task, i: number): number => {
      let s = 0
      if (t.latestUpdate) s += 100 // 有最新进展：正在推进
      if (t.priority === 'super_urgent' || t.priority === 'important_urgent') s += 40
      if (t.overdue) s += 20
      if (t.blocked) s += 10
      if (!t.actualFinishDate) s += 10
      return s + (activeTasks.length - i) / 1e6 // 保持表格顺序稳定兜底
    }
    return activeTasks
      .map((t, i) => ({ t, i }))
      .sort((a, b) => score(b.t, b.i) - score(a.t, a.i))
      .map((x) => x.t)
      .slice(0, 40)
  }, [activeTasks])
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

      {/* 今日未打卡名单：倒计时上方，黑色醒目滚动 */}
      <UncheckedTicker />

      <CountdownRow milestones={milestones} />

      {/* 任务动态：页面主角，横贯全宽，40 条横向滚动（按活跃度排序） */}
      <TaskFeed onOpen={setSelected} feed={feed} />

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

      <div className="grid grid-cols-1 md:grid-cols-6 gap-4 items-stretch">
        <div className="md:col-span-2">
          <Leaderboard />
        </div>
        <div className="md:col-span-2 flex flex-col">
          <DutyRoster />
        </div>
        {/* 人脸识别摄像头：放在今日值日右侧 */}
        <div className="md:col-span-2 flex flex-col">
          <CameraPanel />
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
