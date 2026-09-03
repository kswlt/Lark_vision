import { AlertTriangle, ScanFace } from 'lucide-react'
import { useData } from '../store'

/** 首页倒计时上方：今日未打卡名单（滚动） + 今日已刷脸打卡（绿色） */
export default function UncheckedTicker() {
  const { unchecked, faceCheckin } = useData()
  const checked = faceCheckin ?? []
  if ((!unchecked || unchecked.length === 0) && checked.length === 0) return null
  const doubled = unchecked?.length ? [...unchecked, ...unchecked] : []

  return (
    <div className="flex items-center gap-3 rounded-md border-2 border-accent-dim/50 bg-white px-4 py-2.5 overflow-hidden anim-enter shadow-sm">
      {/* 未打卡滚动 */}
      <span className="shrink-0 flex items-center gap-2 pl-1">
        <AlertTriangle size={20} className="text-amber-500 pulse-soft" />
        <span className="text-[16px] font-black text-gray-800 tracking-wide">
          今日未打卡
        </span>
      </span>
      <div className="overflow-hidden flex-1">
        {doubled.length > 0 ? (
          <div className="unchecked-track flex w-max items-center gap-8">
            {doubled.map((n, i) => (
              <span
                key={`${n}-${i}`}
                className="text-[15px] font-bold text-gray-700 whitespace-nowrap"
              >
                {n}
              </span>
            ))}
          </div>
        ) : (
          <span className="text-[15px] font-bold text-green-600 whitespace-nowrap">
            全员已打卡
          </span>
        )}
      </div>
      {/* 今日已刷脸 */}
      {checked.length > 0 && (
        <span className="shrink-0 flex items-center gap-2 rounded-md bg-green-50 border border-green-200 px-3 py-1">
          <ScanFace size={18} className="text-green-600" />
          <span className="text-[14px] font-bold text-green-700 whitespace-nowrap">
            已刷脸 {checked.length} 人：{checked.join('、')}
          </span>
        </span>
      )}
      {unchecked?.length > 0 && (
        <span className="shrink-0 num-mono text-[14px] font-black text-accent-bright pr-1">
          {unchecked.length} 人
        </span>
      )}
    </div>
  )
}
