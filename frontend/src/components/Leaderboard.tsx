import { useState } from 'react'
import { Crown, Timer } from 'lucide-react'
import { useData } from '../store'
import Avatar from './Avatar'
import { GROUP_DOT } from './Badge'
import type { Group } from '../types'

interface WorktimeEntry {
  userId: string
  userName?: string
  group?: string
  avatarUrl?: string | null
  weekMinutes?: number
  monthMinutes?: number
}

function splitDur(minutes: number): { h: string; m: string } {
  if (!minutes || minutes <= 0) return { h: '0', m: '00' }
  const h = Math.floor(minutes / 60)
  const m = Math.round(minutes % 60)
  return { h: String(h), m: String(m).padStart(2, '0') }
}

const RANK_STYLE = [
  {
    card: 'border-accent-dim/60 bg-accent-faint/15',
    num: 'text-accent-bright',
    chip: 'bg-accent-faint/60 text-accent-bright',
    big: true
  },
  {
    card: 'border-base-500/50',
    num: 'text-gray-200',
    chip: 'bg-base-700 text-base-300',
    big: false
  },
  {
    card: 'border-base-600',
    num: 'text-base-300',
    chip: 'bg-base-700 text-base-400',
    big: false
  }
]

/** 劳模榜：竖排全量可滚动（超过面板高度上下滚动），与 KPI 同行两列 */
export default function Leaderboard() {
  const { worktimeWeek, worktimeMonth } = useData()
  const [range, setRange] = useState<'week' | 'month'>('week')
  const full = range === 'week' ? worktimeWeek : worktimeMonth
  // 前 3 用高亮样式，第 4 名起复用普通样式
  const list = full.map((p, i) => ({ p, s: RANK_STYLE[Math.min(i, 2)] }))
  const minutesOf = (p: WorktimeEntry) =>
    range === 'week' ? p.weekMinutes ?? 0 : p.monthMinutes ?? 0

  return (
    <div className="panel hud-frame px-2.5 py-1.5 flex flex-col anim-enter-slow">
      <div className="flex items-center justify-between mb-1 shrink-0">
        <span className="panel-title flex items-center gap-1">
          <Timer size={10} />
          劳模榜 · 工时排行
        </span>
        <div className="flex text-[9px] rounded border border-base-600 overflow-hidden">
          {(['week', 'month'] as const).map((r) => (
            <button
              key={r}
              onClick={() => setRange(r)}
              className={`px-1.5 py-0.5 transition-colors ${
                range === r
                  ? 'bg-accent-faint text-accent-bright'
                  : 'text-base-400 hover:text-gray-200'
              }`}
            >
              {r === 'week' ? '本周' : '本月'}
            </button>
          ))}
        </div>
      </div>

      {list.length === 0 ? (
        <div className="text-[10px] text-base-400 py-2 text-center">
          暂无打卡数据 · 接入飞书考勤/工时表后显示
        </div>
      ) : (
        <div className="space-y-1 max-h-[300px] overflow-y-auto leader-scroll pr-1">
          {list.map(({ p, s }, i) => {
            const dur = splitDur(minutesOf(p))
            return (
              <div
                key={p.userId}
                className={`flex items-center gap-2 rounded-md border px-2 py-1 card-lift anim-enter ${s.card}`}
                style={{ animationDelay: `${Math.min(i, 8) * 60}ms` }}
              >
                {s.big && <Crown size={10} className="text-accent-bright shrink-0" />}
                <span
                  className={`num-mono text-[10px] font-bold px-1 py-0.5 rounded ${s.chip}`}
                >
                  {String(i + 1).padStart(2, '0')}
                </span>
                <Avatar name={p.userName} url={p.avatarUrl} size={20} />
                <div className="min-w-0 flex-1">
                  <div className="text-[10px] font-semibold text-gray-100 truncate leading-tight">
                    {p.userName || '未命名'}
                  </div>
                  <div className="flex items-center gap-1 mt-0.5">
                    {p.group && (
                      <>
                        <span
                          className="w-1 h-1 rounded-full shrink-0"
                          style={{ background: GROUP_DOT[p.group as Group] ?? '#5a6670' }}
                        />
                        <span className="text-[8px] text-base-300">{p.group}</span>
                      </>
                    )}
                  </div>
                </div>
                <div className="flex flex-col items-end shrink-0">
                  <div className="flex items-baseline gap-0.5">
                    <span className={`num-mono font-bold text-base leading-none ${s.num}`}>
                      {dur.h}
                    </span>
                    <span className={`num-mono text-[9px] leading-none ${s.num}`}>h</span>
                    <span className="num-mono text-[10px] text-gray-200 leading-none ml-0.5">
                      {dur.m}m
                    </span>
                  </div>
                  <span className="text-[7px] text-base-400">
                    {s.big ? '第 1 名' : `第 ${i + 1} 名`}
                  </span>
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
