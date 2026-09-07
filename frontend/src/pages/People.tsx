import { useMemo, useState } from 'react'
import { X } from 'lucide-react'
import { useData } from '../store'
import Avatar from '../components/Avatar'
import TaskCard from '../components/TaskCard'
import TaskDrawer from '../components/TaskDrawer'
import { GROUP_DOT } from '../components/Badge'
import { daysUntil, fmtDuration, isTaskActive } from '../lib/format'
import type { Group, PeopleSummary, Task } from '../types'
import { GROUPS } from '../config/constants'

export default function People() {
  const { people, tasks } = useData()
  const [group, setGroup] = useState<Group | ''>('')
  const [selectedPerson, setSelectedPerson] = useState<PeopleSummary | null>(null)
  const [selectedTask, setSelectedTask] = useState<Task | null>(null)

  const list = useMemo(
    () => (group ? people.filter((p) => p.group === group) : people),
    [people, group]
  )

  // 选中人员的正在进行任务，按剩余时间升序
  const personTasks = useMemo(() => {
    if (!selectedPerson) return []
    return tasks
      .filter((t) => t.ownerName === selectedPerson.userName && isTaskActive(t))
      .sort((a, b) => {
        const da = a.dueDate ? daysUntil(a.dueDate) : 9999
        const db = b.dueDate ? daysUntil(b.dueDate) : 9999
        return da - db
      })
  }, [tasks, selectedPerson])

  return (
    <div className="p-5 space-y-4 max-w-[1400px]">
      <div className="flex items-center justify-between flex-wrap gap-2">
        <h1 className="text-lg font-bold tracking-[0.15em] text-gray-100">成员</h1>
        <div className="flex items-center gap-1 flex-wrap">
          <button
            onClick={() => setGroup('')}
            className={`px-2 py-1 rounded text-[11px] border ${
              !group ? 'bg-accent-faint text-accent-bright border-accent-dim' : 'border-base-600 text-base-300'
            }`}
          >
            全部
          </button>
          {GROUPS.map((g) => (
            <button
              key={g}
              onClick={() => setGroup(group === g ? '' : g)}
              className={`px-2 py-1 rounded text-[11px] border ${
                group === g ? 'bg-accent-faint text-accent-bright border-accent-dim' : 'border-base-600 text-base-300'
              }`}
            >
              {g}
            </button>
          ))}
        </div>
      </div>

      {list.length === 0 && (
        <div className="panel p-8 text-center text-[12px] text-base-400">
          暂无人员数据（接入飞书考勤后显示）
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
        {list.map((p) => (
          <div
            key={p.userId}
            onClick={() => setSelectedPerson(p)}
            className="panel p-4 flex items-center gap-3 clickable hover:bg-base-800 transition-colors"
          >
            <Avatar name={p.userName} url={p.avatarUrl} size={40} />
            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-2">
                <span className="text-[13px] font-semibold text-gray-100 truncate">{p.userName}</span>
                {p.group && (
                  <span className="flex items-center gap-1 text-[10px] text-base-300">
                    <span className="w-1.5 h-1.5 rounded-full" style={{ background: GROUP_DOT[p.group as Group] }} />
                    {p.group}
                  </span>
                )}
              </div>
              <div className="mt-1.5 grid grid-cols-2 gap-x-4 gap-y-1">
                <div>
                  <div className="kv-label">本周工时</div>
                  <div className="num-mono text-[13px] text-gray-200">{fmtDuration(p.weekMinutes)}</div>
                </div>
                <div>
                  <div className="kv-label">本月工时</div>
                  <div className="num-mono text-[13px] text-gray-200">{fmtDuration(p.monthMinutes)}</div>
                </div>
                <div>
                  <div className="kv-label">当前任务</div>
                  <div className="num-mono text-[13px] text-accent-bright font-semibold">{p.activeTasks}</div>
                </div>
                <div>
                  <div className="kv-label">延期任务</div>
                  <div
                    className={`num-mono text-[13px] ${p.overdueTasks > 0 ? 'text-red-400' : 'text-gray-200'}`}
                  >
                    {p.overdueTasks}
                  </div>
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* 人员任务模态框 */}
      {selectedPerson && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div className="absolute inset-0 bg-black/60" onClick={() => setSelectedPerson(null)} />
          <div className="relative panel w-full max-w-4xl max-h-[85vh] flex flex-col bg-base-900 border border-base-600 rounded-lg shadow-2xl">
            <div className="flex items-center gap-3 p-4 border-b border-base-600">
              <Avatar name={selectedPerson.userName} url={selectedPerson.avatarUrl} size={36} />
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="text-[15px] font-bold text-gray-100">{selectedPerson.userName}</span>
                  {selectedPerson.group && (
                    <span className="flex items-center gap-1 text-[11px] text-base-300">
                      <span
                        className="w-1.5 h-1.5 rounded-full"
                        style={{ background: GROUP_DOT[selectedPerson.group as Group] }}
                      />
                      {selectedPerson.group}
                    </span>
                  )}
                </div>
                <div className="text-[11px] text-base-400 mt-0.5">
                  本周 {fmtDuration(selectedPerson.weekMinutes)} · 本月 {fmtDuration(selectedPerson.monthMinutes)} · 正在进行 {personTasks.length} 项
                </div>
              </div>
              <button
                onClick={() => setSelectedPerson(null)}
                className="p-1.5 rounded text-base-300 hover:text-gray-100 hover:bg-base-700 clickable"
              >
                <X size={18} />
              </button>
            </div>
            <div className="flex-1 overflow-y-auto p-4">
              {personTasks.length === 0 ? (
                <div className="text-center text-[13px] text-base-400 py-12">
                  该成员当前没有正在进行的任务
                </div>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  {personTasks.map((t) => (
                    <TaskCard key={t.id} task={t} onOpen={setSelectedTask} />
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      <TaskDrawer task={selectedTask} onClose={() => setSelectedTask(null)} />
    </div>
  )
}
