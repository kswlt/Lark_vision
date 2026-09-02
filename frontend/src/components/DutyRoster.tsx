import { CalendarDays } from 'lucide-react'
import { useData } from '../store'
import { fmtDate } from '../lib/format'

/** 值日表：今日值日 + 未来 6 天轮值（每天一人） */
export default function DutyRoster() {
  const { duty } = useData()
  if (!duty || duty.length === 0) return null
  const today = duty.find((d) => d.isToday) ?? duty[0]

  return (
    <div className="panel hud-frame flex flex-col h-full anim-enter">
      <div className="flex items-center gap-1.5 px-4 pt-3 pb-2 border-b border-base-600">
        <CalendarDays size={14} className="text-accent-bright" />
        <span className="panel-title">值日表</span>
        <span className="ml-auto text-[10px] text-base-400">每日一人</span>
      </div>

      {/* 今日值日 */}
      <div className="px-4 py-3 flex items-center gap-3">
        <div className="flex items-center justify-center w-12 h-12 rounded-full bg-accent-faint text-accent-bright text-xl font-black shrink-0 border border-accent-dim/40">
          {today.name.charAt(0)}
        </div>
        <div className="leading-tight">
          <div className="text-[10px] tracking-[0.18em] text-base-400">
            今日值日 · {fmtDate(today.date)}
          </div>
          <div className="text-2xl font-black text-gray-100 mt-0.5">{today.name}</div>
        </div>
      </div>

      {/* 未来 6 天 */}
      <div className="px-4 pb-3 grid grid-cols-3 gap-1.5">
        {duty
          .filter((d) => !d.isToday)
          .map((d) => (
            <div
              key={d.date}
              className="flex items-center gap-1.5 rounded bg-base-850 border border-base-600 px-2 py-1"
            >
              <span className="num-mono text-[10px] text-base-400 shrink-0">
                {fmtDate(d.date)}
              </span>
              <span className="text-[11px] text-gray-200 truncate">{d.name}</span>
            </div>
          ))}
      </div>
    </div>
  )
}
