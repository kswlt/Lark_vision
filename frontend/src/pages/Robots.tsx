import { useMemo, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { useData } from '../store'
import TaskCard from '../components/TaskCard'
import TaskDrawer from '../components/TaskDrawer'
import { GROUPS, ROBOTS } from '../config/constants'
import type { Group, Task } from '../types'

const STATS = [
  { key: 'total', label: '总数' },
  { key: 'done', label: '已完成' },
  { key: 'overdue', label: '已延期' },
  { key: 'critical', label: '重要紧急' },
  { key: 'blocked', label: '阻塞' },
  { key: 'stale', label: '久未更新' },
  { key: 'dueSoon', label: '近期截止' }
] as const

export default function Robots() {
  const { robots, tasks } = useData()
  const [params, setParams] = useSearchParams()
  const [selectedRobot, setSelectedRobot] = useState<string>((params.get('robot') as string) || '重装')
  const [group, setGroup] = useState<Group | ''>('')
  const [selected, setSelected] = useState<Task | null>(null)

  const robotTasks = useMemo(() => {
    let list = selectedRobot === 'none' ? tasks.filter((t) => !t.robot) : tasks.filter((t) => t.robot === selectedRobot)
    if (group) list = list.filter((t) => t.group === group)
    return list
  }, [tasks, selectedRobot, group])

  const active = robots.find((r) => r.robot === selectedRobot)

  return (
    <div className="p-5 space-y-4 max-w-[1400px]">
      <h1 className="text-lg font-bold tracking-[0.15em] text-gray-100">兵种</h1>

      <div className="grid grid-cols-2 sm:grid-cols-3 xl:grid-cols-4 gap-2.5">
        {ROBOTS.map((r) => (
          <button
            key={r}
            onClick={() => {
              setSelectedRobot(r)
              setGroup('')
            }}
            className={`panel p-3 text-left clickable ${
              selectedRobot === r ? 'border-accent-dim bg-accent-faint' : ''
            }`}
          >
            <div className="flex items-center justify-between">
              <span className="text-[13px] font-semibold text-gray-100">{r}</span>
              <BotIcon />
            </div>
            <div className="mt-1 num-mono text-[10px] text-base-400">
              {robots.find((x) => x.robot === r)?.total ?? 0} 任务
            </div>
          </button>
        ))}
        <button
          onClick={() => {
            setSelectedRobot('none')
            setGroup('')
          }}
          className={`panel p-3 text-left clickable ${selectedRobot === 'none' ? 'border-accent-dim bg-accent-faint' : ''}`}
        >
          <span className="text-[13px] font-semibold text-gray-400">未指定</span>
          <div className="mt-1 num-mono text-[10px] text-base-400">
            {robots.find((x) => x.robot === 'none')?.total ?? 0} 任务
          </div>
        </button>
      </div>

      {active && (
        <div className="grid grid-cols-2 sm:grid-cols-4 xl:grid-cols-7 gap-2.5">
          {STATS.map(({ key, label }) => {
            const v = active[key]
            const danger = key === 'overdue' || key === 'blocked'
            const warn = key === 'stale' || key === 'critical'
            return (
              <div key={key} className="panel p-3 flex flex-col items-center justify-center">
                <span
                  className={`num-mono text-2xl font-bold ${
                    danger && v > 0 ? 'text-red-400' : warn && v > 0 ? 'text-amber-400' : 'text-gray-200'
                  }`}
                >
                  {String(v).padStart(2, '0')}
                </span>
                <span className="text-[9px] tracking-[0.2em] text-base-300">{label}</span>
              </div>
            )
          })}
        </div>
      )}

      <div className="flex items-center justify-between flex-wrap gap-2">
        <h2 className="text-[15px] font-semibold text-gray-100">
          {selectedRobot === 'none' ? '未指定' : selectedRobot}
          <span className="ml-2 num-mono text-[11px] text-base-400 font-normal">
            {robotTasks.length} 任务
          </span>
        </h2>
        <div className="flex items-center gap-1 flex-wrap">
          <button
            onClick={() => setGroup('')}
            className={`px-2 py-1 rounded text-[11px] border ${
              !group ? 'bg-accent-faint text-accent-bright border-accent-dim' : 'border-base-600 text-base-300'
            }`}
          >
            全部组别
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

      <div className="grid grid-cols-1 md:grid-cols-2 2xl:grid-cols-3 gap-3">
        {robotTasks.map((t) => (
          <TaskCard key={t.id} task={t} onOpen={setSelected} />
        ))}
      </div>
      {robotTasks.length === 0 && (
        <div className="panel p-8 text-center text-[12px] text-base-400">该兵种暂无任务</div>
      )}

      <TaskDrawer task={selected} onClose={() => setSelected(null)} />
    </div>
  )
}

function BotIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#3fb6b6" strokeWidth="1.8">
      <rect x="4" y="7" width="16" height="12" rx="2" />
      <circle cx="9" cy="12" r="1.2" fill="#3fb6b6" stroke="none" />
      <circle cx="15" cy="12" r="1.2" fill="#3fb6b6" stroke="none" />
      <path d="M12 3 v4 M9 3 h6" strokeLinecap="round" />
    </svg>
  )
}
