import { CalendarDays } from 'lucide-react'
import { useData } from '../store'
import { fmtDate } from '../lib/format'

/** 值日表：仅显示当日值日一人 */
export default function DutyRoster() {
  const { duty } = useData()
  if (!duty || duty.length === 0) return null
  const today = duty.find((d) => d.isToday) ?? duty[0]

  return (
    <div className="panel hud-frame flex items-center gap-3 px-4 py-2 anim-enter">
      <div className="flex items-center gap-1.5 shrink-0">
        <CalendarDays size={14} className="text-accent-bright" />
        <span className="panel-title">今日值日</span>
      </div>

      <div className="flex items-center gap-2 shrink-0">
        <div className="flex items-center justify-center w-8 h-8 rounded-full bg-accent-faint text-accent-bright text-base font-black shrink-0 border border-accent-dim/40">
          {today.name.charAt(0)}
        </div>
        <div className="leading-tight">
          <span className="text-lg font-black text-gray-100">{today.name}</span>
          <span className="ml-2 num-mono text-[10px] text-base-400">
            {fmtDate(today.date)}
          </span>
        </div>
      </div>
    </div>
  )
}
