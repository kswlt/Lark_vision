import { useEffect, useRef, useState } from 'react'
import { AlertTriangle, ScanFace } from 'lucide-react'
import { useData } from '../store'

/** 首页倒计时上方：今日未打卡名单（内容放得下则静止，溢出才滚动） + 今日已刷脸打卡（绿色） */
export default function UncheckedTicker() {
  const { unchecked, faceCheckin } = useData()
  const checked = faceCheckin ?? []
  const containerRef = useRef<HTMLDivElement>(null)
  const meterRef = useRef<HTMLDivElement>(null)
  const [overflow, setOverflow] = useState(false)

  // 检测内容是否超出容器宽度；放得下就不滚动，溢出才滚动
  useEffect(() => {
    const measure = () => {
      const c = containerRef.current
      const m = meterRef.current
      if (!c || !m || !unchecked?.length) return
      setOverflow(m.scrollWidth > c.clientWidth)
    }
    measure()
    const timer = setTimeout(measure, 80)
    window.addEventListener('resize', measure)
    return () => {
      clearTimeout(timer)
      window.removeEventListener('resize', measure)
    }
  }, [unchecked])

  if ((!unchecked || unchecked.length === 0) && checked.length === 0) return null
  const doubled = unchecked?.length ? [...unchecked, ...unchecked] : []
  const list = overflow && unchecked?.length ? doubled : unchecked

  return (
    <div className="flex items-center gap-3 rounded-md border-2 border-accent-dim/50 bg-white px-4 py-2.5 overflow-hidden anim-enter shadow-sm">
      {/* 未打卡滚动 */}
      <span className="shrink-0 flex items-center gap-2 pl-1">
        <AlertTriangle size={20} className="text-amber-500 pulse-soft" />
        <span className="text-[16px] font-black text-gray-800 tracking-wide">
          今日未打卡
        </span>
      </span>
      <div ref={containerRef} className="relative overflow-hidden flex-1">
        {/* 测量层：永远单份、与展示层同布局，用于判断是否溢出 */}
        <div
          ref={meterRef}
          aria-hidden
          className="invisible absolute left-0 top-0 whitespace-nowrap"
        >
          <div className="flex items-center gap-8">
            {unchecked.map((n) => (
              <span key={n} className="text-[15px] font-bold text-gray-700 whitespace-nowrap">
                {n}
              </span>
            ))}
          </div>
        </div>
        {unchecked?.length > 0 ? (
          <div className={`flex w-max items-center gap-8 ${overflow ? 'unchecked-track' : ''}`}>
            {list.map((n, i) => (
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
