import { useState, useRef, useEffect } from 'react'
import { Sparkles, RotateCw } from 'lucide-react'
import { useData } from '../store'

/** 幸运转盘：从本周打卡成员中随机抽取一人 */
export default function LuckyWheel() {
  const { worktimeWeek } = useData()
  const names = worktimeWeek.slice(0, 12).map((p) => p.userName || '未命名')
  const [angle, setAngle] = useState(0)
  const [spinning, setSpinning] = useState(false)
  const [result, setResult] = useState<string | null>(null)
  const spinRef = useRef<number>(0)

  const count = Math.max(names.length, 2)
  const segAngle = 360 / count

  // 扇形颜色（低饱和，配合深色主题）
  const COLORS = [
    '#3b82f6', '#6366f1', '#8b5cf6', '#a855f7',
    '#06b6d4', '#0ea5e9', '#14b8a6', '#10b981',
    '#f59e0b', '#f97316', '#ef4444', '#ec4899',
  ]

  const spin = () => {
    if (spinning || names.length === 0) return
    setSpinning(true)
    setResult(null)
    // 随机旋转 5-8 圈 + 随机角度
    const extra = 360 * (5 + Math.floor(Math.random() * 4))
    const target = angle + extra + Math.random() * 360
    spinRef.current = target
    setAngle(target)
    // 动画结束后计算结果
    setTimeout(() => {
      const normalized = ((target % 360) + 360) % 360
      // 指针在顶部（12点方向），扇形从顶部开始顺时针排列
      const idx = Math.floor((360 - normalized) / segAngle) % count
      setResult(names[idx])
      setSpinning(false)
    }, 4200)
  }

  // 生成扇形路径
  const sectorPath = (i: number) => {
    const start = (i * segAngle - 90) * (Math.PI / 180)
    const end = ((i + 1) * segAngle - 90) * (Math.PI / 180)
    const r = 80
    const cx = 100, cy = 100
    const x1 = cx + r * Math.cos(start)
    const y1 = cy + r * Math.sin(start)
    const x2 = cx + r * Math.cos(end)
    const y2 = cy + r * Math.sin(end)
    const large = segAngle > 180 ? 1 : 0
    return `M ${cx} ${cy} L ${x1} ${y1} A ${r} ${r} 0 ${large} 1 ${x2} ${y2} Z`
  }

  // 扇形文字位置
  const textPos = (i: number) => {
    const mid = ((i + 0.5) * segAngle - 90) * (Math.PI / 180)
    const r = 52
    return {
      x: 100 + r * Math.cos(mid),
      y: 100 + r * Math.sin(mid),
      rotate: (i + 0.5) * segAngle,
    }
  }

  return (
    <div className="panel hud-frame px-3 py-1.5 flex flex-col items-center anim-enter-slow">
      <div className="flex items-center gap-1.5 mb-1 w-full">
        <Sparkles size={11} className="text-accent-bright" />
        <span className="panel-title">幸运转盘</span>
      </div>

      <div className="relative w-full max-w-[140px] aspect-square">
        {/* 指针（固定在顶部） */}
        <div className="absolute left-1/2 -translate-x-1/2 -top-0.5 z-10">
          <div
            className="w-0 h-0"
            style={{
              borderLeft: '6px solid transparent',
              borderRight: '6px solid transparent',
              borderTop: '10px solid #f59e0b',
              filter: 'drop-shadow(0 1px 2px rgba(0,0,0,0.5))',
            }}
          />
        </div>

        {/* 转盘 */}
        <svg
          viewBox="0 0 200 200"
          className="w-full h-full"
          style={{
            transform: `rotate(${angle}deg)`,
            transition: spinning ? 'transform 4s cubic-bezier(0.17, 0.67, 0.12, 0.99)' : 'none',
          }}
        >
          {/* 外圈 */}
          <circle cx="100" cy="100" r="92" fill="none" stroke="rgba(255,255,255,0.15)" strokeWidth="3" />
          {/* 扇形（无文字） */}
          {names.map((name, i) => (
            <path key={i} d={sectorPath(i)} fill={COLORS[i % COLORS.length]} fillOpacity="0.75" stroke="rgba(0,0,0,0.3)" strokeWidth="0.5" />
          ))}
          {/* 中心圆 */}
          <circle cx="100" cy="100" r="18" fill="#1a1d23" stroke="rgba(255,255,255,0.2)" strokeWidth="2" />
        </svg>
      </div>

      {/* 结果显示 */}
      <div className="mt-1 h-4 text-center">
        {result ? (
          <span className="text-[12px] font-black text-amber-400 tick-pop">
            🎉 {result}
          </span>
        ) : (
          <span className="text-[9px] text-base-400">
            {spinning ? '旋转中…' : '点击抽取'}
          </span>
        )}
      </div>

      {/* 开始按钮 */}
      <button
        onClick={spin}
        disabled={spinning || names.length === 0}
        className="mt-0.5 flex items-center gap-1 px-2.5 py-0.5 rounded-md bg-accent-faint text-accent-bright text-[10px] font-bold border border-accent-dim/40 hover:bg-accent-faint/80 transition-colors disabled:opacity-40 disabled:cursor-not-allowed clickable"
      >
        <RotateCw size={10} className={spinning ? 'animate-spin' : ''} />
        {spinning ? '抽取中' : '开始'}
      </button>
    </div>
  )
}
