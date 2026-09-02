import { useMemo } from 'react'
import { BarChart3, ClockAlert, TriangleAlert } from 'lucide-react'
import { useData } from '../store'
import Avatar from './Avatar'
import { GROUP_DOT } from './Badge'
import type { Group } from '../types'

interface MemberLoadRow {
  name: string
  group?: string
  avatarUrl?: string
  active: number
  overdue: number
  critical: number
}

/** 成员任务负载榜：谁手上在办任务多、谁延期多（替代"任务完成趋势"） */
export default function MemberLoad() {
  const { tasks } = useData()
  const rows = useMemo<MemberLoadRow[]>(() => {
    const map = new Map<string, MemberLoadRow>()
    for (const t of tasks) {
      const name = t.ownerName || '未分配'
      const key = t.ownerId || name
      if (!map.has(key)) {
        map.set(key, {
          name,
          group: t.group,
          avatarUrl: t.ownerAvatarUrl,
          active: 0,
          overdue: 0,
          critical: 0
        })
      }
      const m = map.get(key)!
      if (!t.actualFinishDate) m.active += 1
      if (t.overdue) m.overdue += 1
      if (t.priority === 'important_urgent') m.critical += 1
    }
    const arr = [...map.values()].filter((r) => r.name !== '未分配')
    arr.sort(
      (a, b) => b.active - a.active || b.overdue - a.overdue || b.critical - a.critical
    )
    return arr.slice(0, 8)
  }, [tasks])

  const max = Math.max(1, ...rows.map((r) => r.active))

  return (
    <div className="panel hud-frame px-3 py-2 flex flex-col anim-enter-slow">
      <div className="flex items-center justify-between mb-1.5">
        <span className="panel-title flex items-center gap-1">
          <BarChart3 size={11} />
          成员任务负载
        </span>
        <span className="text-[10px] text-base-400">Top 8 · 在办</span>
      </div>

      {rows.length === 0 ? (
        <div className="text-[11px] text-base-400 py-3 text-center">暂无任务</div>
      ) : (
        <div className="space-y-1">
          {rows.map((r, i) => (
            <div
              key={r.name + i}
              className="flex items-center gap-2 anim-enter"
              style={{ animationDelay: `${i * 40}ms` }}
            >
              <Avatar name={r.name} url={r.avatarUrl} size={22} />
              <div className="w-[76px] shrink-0 min-w-0">
                <div className="text-[10px] font-semibold text-gray-100 truncate leading-tight">
                  {r.name}
                </div>
                <div className="flex items-center gap-1 mt-0.5">
                  {r.group && (
                    <>
                      <span
                        className="w-1 h-1 rounded-full shrink-0"
                        style={{ background: GROUP_DOT[r.group as Group] ?? '#5a6670' }}
                      />
                      <span className="text-[8px] text-base-400">{r.group}</span>
                    </>
                  )}
                </div>
              </div>
              <div className="flex-1 h-[7px] rounded-full bg-base-700/60 overflow-hidden">
                <div
                  className="h-full rounded-full bg-accent-bright/70"
                  style={{ width: `${(r.active / max) * 100}%` }}
                />
              </div>
              <span className="num-mono text-[10px] text-gray-200 w-8 text-right shrink-0">
                {r.active}
              </span>
              <div className="flex flex-col items-end w-[56px] shrink-0 gap-0.5">
                {r.overdue > 0 && (
                  <span className="flex items-center gap-0.5 text-[9px] text-red-400">
                    <ClockAlert size={8} />
                    {r.overdue}
                  </span>
                )}
                {r.critical > 0 && (
                  <span className="flex items-center gap-0.5 text-[9px] text-amber-400">
                    <TriangleAlert size={8} />
                    {r.critical}
                  </span>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
