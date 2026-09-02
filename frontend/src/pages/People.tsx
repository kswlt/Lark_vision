import { useMemo, useState } from 'react'
import { useData } from '../store'
import Avatar from '../components/Avatar'
import { GROUP_DOT } from '../components/Badge'
import { fmtDuration } from '../lib/format'
import type { Group } from '../types'
import { GROUPS } from '../config/constants'

export default function People() {
  const { people } = useData()
  const [group, setGroup] = useState<Group | ''>('')

  const list = useMemo(
    () => (group ? people.filter((p) => p.group === group) : people),
    [people, group]
  )

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
          <div key={p.userId} className="panel p-4 flex items-center gap-3">
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
                  <div className="num-mono text-[13px] text-gray-200">{p.activeTasks}</div>
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
    </div>
  )
}
