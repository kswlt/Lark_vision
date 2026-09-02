import { useMemo, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { useData } from '../store'
import TaskCard from '../components/TaskCard'
import TaskDrawer from '../components/TaskDrawer'
import { GROUP_DOT } from '../components/Badge'
import { ROBOTS } from '../config/constants'
import type { Group, Robot, Task } from '../types'

export default function Groups() {
  const { groups, tasks } = useData()
  const [params, setParams] = useSearchParams()
  const [selectedGroup, setSelectedGroup] = useState<Group>(
    (params.get('group') as Group) || '算法'
  )
  const [robot, setRobot] = useState<Robot | ''>('')
  const [selected, setSelected] = useState<Task | null>(null)

  const groupTasks = useMemo(() => {
    let list = tasks.filter((t) => t.group === selectedGroup)
    if (robot) list = list.filter((t) => t.robot === robot)
    return list
  }, [tasks, selectedGroup, robot])

  const active = groups.find((g) => g.group === selectedGroup)

  return (
    <div className="p-5 flex gap-4 max-w-[1400px]">
      <div className="w-56 shrink-0 space-y-1.5">
        <h1 className="text-lg font-bold tracking-[0.15em] text-gray-100 mb-3">组别</h1>
        {groups.map((g) => {
          const isActive = g.group === selectedGroup
          return (
            <button
              key={g.group}
              onClick={() => {
                setSelectedGroup(g.group)
                setRobot('')
              }}
              className={`w-full text-left panel p-3 clickable ${
                isActive ? 'border-accent-dim bg-accent-faint' : ''
              }`}
            >
              <div className="flex items-center gap-2">
                <span className="w-2 h-2 rounded-full" style={{ background: GROUP_DOT[g.group] }} />
                <span className="text-[13px] font-semibold text-gray-100">{g.group}</span>
                <span className="ml-auto num-mono text-[10px] text-base-400">{g.total} 任务</span>
              </div>
              <div className="mt-1.5 flex gap-2 text-[10px] num-mono">
                <span className={g.overdue ? 'text-red-400' : 'text-base-400'}>
                  {g.overdue} 已延期
                </span>
                <span className="text-base-400">{g.critical} 重要紧急</span>
                <span className={g.blocked ? 'text-red-400' : 'text-base-400'}>
                  {g.blocked} 阻塞
                </span>
                <span className={g.stale ? 'text-amber-400' : 'text-base-400'}>
                  {g.stale} 久未更新
                </span>
              </div>
            </button>
          )
        })}
      </div>

      <div className="flex-1 min-w-0">
        <div className="flex items-center justify-between mb-3 flex-wrap gap-2">
          <h2 className="text-[15px] font-semibold text-gray-100">
            {selectedGroup}
            <span className="ml-2 num-mono text-[11px] text-base-400 font-normal">
              {groupTasks.length} 任务
            </span>
          </h2>
          <div className="flex items-center gap-1 flex-wrap">
            <button
              onClick={() => setRobot('')}
              className={`px-2 py-1 rounded text-[11px] border ${
                !robot ? 'bg-accent-faint text-accent-bright border-accent-dim' : 'border-base-600 text-base-300'
              }`}
            >
              全部
            </button>
            {ROBOTS.map((r) => (
              <button
                key={r}
                onClick={() => setRobot(robot === r ? '' : r)}
                className={`px-2 py-1 rounded text-[11px] border ${
                  robot === r
                    ? 'bg-accent-faint text-accent-bright border-accent-dim'
                    : 'border-base-600 text-base-300'
                }`}
              >
                {r}
              </button>
            ))}
          </div>
        </div>

        {active && (
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-3">
            <Stat label="总任务" value={active.total} />
            <Stat label="已延期" value={active.overdue} danger={active.overdue > 0} />
            <Stat label="重要紧急" value={active.critical} warn={active.critical > 0} />
            <Stat label="阻塞" value={active.blocked} danger={active.blocked > 0} />
          </div>
        )}

        <div className="grid grid-cols-1 md:grid-cols-2 2xl:grid-cols-3 gap-3">
          {groupTasks.map((t) => (
            <TaskCard key={t.id} task={t} onOpen={setSelected} />
          ))}
        </div>
        {groupTasks.length === 0 && (
          <div className="panel p-8 text-center text-[12px] text-base-400">该组暂无任务</div>
        )}
      </div>

      <TaskDrawer task={selected} onClose={() => setSelected(null)} />
    </div>
  )
}

function Stat({ label, value, danger, warn }: { label: string; value: number; danger?: boolean; warn?: boolean }) {
  return (
    <div className="panel p-3">
      <div className={`num-mono text-2xl font-bold ${danger ? 'text-red-400' : warn ? 'text-amber-400' : 'text-gray-200'}`}>
        {String(value).padStart(2, '0')}
      </div>
      <div className="text-[9px] tracking-[0.2em] text-base-300">{label}</div>
    </div>
  )
}
