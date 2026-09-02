import { AlertTriangle } from 'lucide-react'
import { useData } from '../store'

/** 首页倒计时上方：今日未打卡名单，红底醒目横向滚动 */
export default function UncheckedTicker() {
  const { unchecked } = useData()
  if (!unchecked || unchecked.length === 0) return null
  const doubled = [...unchecked, ...unchecked]

  return (
    <div className="flex items-center gap-3 rounded-md border border-gray-800/90 bg-gray-900/95 px-3 py-2 overflow-hidden anim-enter">
      <span className="shrink-0 flex items-center gap-1.5 pl-1">
        <AlertTriangle size={17} className="text-gray-200 pulse-soft" />
        <span className="text-[14px] font-black text-gray-50 tracking-wide">
          今日未打卡
        </span>
      </span>
      <div className="overflow-hidden flex-1">
        <div className="unchecked-track flex w-max items-center gap-8">
          {doubled.map((n, i) => (
            <span
              key={`${n}-${i}`}
              className="text-[13px] font-bold text-gray-100 whitespace-nowrap"
            >
              {n}
            </span>
          ))}
        </div>
      </div>
      <span className="shrink-0 num-mono text-[12px] font-bold text-gray-300 pr-1">
        {unchecked.length} 人
      </span>
    </div>
  )
}
