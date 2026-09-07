import { useEffect, useMemo, useRef, useState } from 'react'
import { Flag, Radio, ClockAlert } from 'lucide-react'
import { useData } from '../store'
import { fmtDate, daysUntil } from '../lib/format'
import type { Task } from '../types'

/** 自动滚动速度 px/s（缓慢） */
const AUTO_SPEED = 26

function statusOf(t: Task): { label: string; cls: string } | null {
  if (t.blocked) return { label: '阻塞', cls: 'text-red-400' }
  if (t.overdue) return { label: `已延期${t.overdueDays ?? ''}天`, cls: 'text-red-400' }
  if (t.priority === 'important_urgent') return { label: '重要紧急', cls: 'text-amber-400' }
  if (t.daysSinceUpdate !== undefined && t.daysSinceUpdate >= 3)
    return { label: `${t.daysSinceUpdate}日未更新`, cls: 'text-amber-400' }
  return null
}

/** 首页任务动态：从右向左自动滚动 + 可自由左右拖拽（按住拖动暂停，松手恢复） */
export default function TaskFeed({
  onOpen,
  feed,
  title
}: {
  onOpen: (t: Task) => void
  feed?: Task[]
  title?: string
}) {
  const { tasks } = useData()
  const viewportRef = useRef<HTMLDivElement>(null)
  const dragState = useRef({ active: false, startX: 0, startScroll: 0, moved: false })
  const [dragging, setDragging] = useState(false)

  // 传入 feed 时不再截断（供首页合并成一长条）；未传入时默认取前 20 条
  const items = useMemo(
    () => (feed !== undefined ? feed : tasks.slice(0, 20)),
    [feed, tasks]
  )
  const doubled = [...items, ...items]

  // 自动滚动循环（无缝：滚到一半回卷）
  useEffect(() => {
    let raf = 0
    let last = performance.now()
    const loop = (now: number) => {
      const el = viewportRef.current
      if (el) {
        const dt = (now - last) / 1000
        last = now
        const half = el.scrollWidth / 2
        const canScroll = half > el.clientWidth
        if (!dragState.current.active && canScroll) {
          el.scrollLeft += AUTO_SPEED * dt
          if (el.scrollLeft >= half) el.scrollLeft -= half
        }
      }
      raf = requestAnimationFrame(loop)
    }
    raf = requestAnimationFrame(loop)
    return () => cancelAnimationFrame(raf)
  }, [])

  if (items.length === 0) return null

  const endDrag = () => {
    const st = dragState.current
    if (st.moved) {
      // 拖拽过则拦截本次 click，避免误触卡片
      const block = (ev: MouseEvent) => {
        ev.stopPropagation()
        ev.preventDefault()
        document.removeEventListener('click', block, true)
      }
      document.addEventListener('click', block, true)
      setTimeout(() => document.removeEventListener('click', block, true), 300)
    }
    dragState.current.active = false
    setDragging(false)
  }
  const onMouseDown = (e: React.MouseEvent) => {
    const el = viewportRef.current
    if (!el) return
    dragState.current = { active: true, startX: e.clientX, startScroll: el.scrollLeft, moved: false }
    setDragging(true)
  }
  const onMouseMove = (e: React.MouseEvent) => {
    const st = dragState.current
    const el = viewportRef.current
    if (!st.active || !el) return
    const dx = e.clientX - st.startX
    if (Math.abs(dx) > 4) st.moved = true
    el.scrollLeft = st.startScroll - dx
  }
  const onTouchStart = (e: React.TouchEvent) => {
    const el = viewportRef.current
    if (!el || e.touches.length === 0) return
    dragState.current = { active: true, startX: e.touches[0].clientX, startScroll: el.scrollLeft, moved: false }
    setDragging(true)
  }
  const onTouchMove = (e: React.TouchEvent) => {
    const st = dragState.current
    const el = viewportRef.current
    if (!st.active || !el || e.touches.length === 0) return
    const dx = e.touches[0].clientX - st.startX
    if (Math.abs(dx) > 4) st.moved = true
    el.scrollLeft = st.startScroll - dx
  }

  return (
    <div className="panel hud-frame flex flex-col anim-enter-slow">
      <div className="flex items-center gap-1.5 px-4 pt-3 pb-2 border-b border-base-600">
        <Radio size={13} className="text-accent-bright pulse-soft" />
        <span className="panel-title">{title ?? '任务动态'}</span>
        <span className="ml-auto num-mono text-[10px] text-base-400">{items.length} 条</span>
      </div>
      <div
        ref={viewportRef}
        className={`ticker-viewport px-3 py-2.5 ${dragging ? 'dragging' : ''}`}
        onMouseDown={onMouseDown}
        onMouseMove={onMouseMove}
        onMouseUp={endDrag}
        onMouseLeave={endDrag}
        onTouchStart={onTouchStart}
        onTouchMove={onTouchMove}
        onTouchEnd={endDrag}
      >
        <div className="ticker-h-track">
          {doubled.map((t, i) => {
            const st = statusOf(t)
            const daysLeft = t.dueDate ? daysUntil(t.dueDate) : null
            return (
              <button
                key={t.id + '-' + i}
                onClick={() => onOpen(t)}
                className="w-[340px] shrink-0 text-left flex flex-col gap-1.5 rounded-md border border-base-600 bg-base-850 px-3 py-2.5 hover:border-accent-dim/70 hover:bg-base-800 clickable anim-enter"
              >
                <div className="flex items-center gap-2">
                  <span className="num-mono text-[11px] text-accent-bright font-semibold shrink-0">
                    {t.id}
                  </span>
                  {st && (
                    <span className={`ml-auto text-[10px] shrink-0 ${st.cls}`}>{st.label}</span>
                  )}
                </div>
                <span className="text-[19px] text-gray-100 leading-snug line-clamp-2 font-bold">
                  {t.title}
                </span>
                {t.latestUpdate && (
                  <span className="text-[12px] text-base-300 leading-snug line-clamp-1 truncate">
                    最新：{t.latestUpdate}
                  </span>
                )}
                <div className="mt-auto flex items-center gap-1.5 pt-1">
                  <span className="truncate font-semibold text-gray-100 text-[14px]">{t.ownerName || '未分配'}</span>
                  <span className="text-base-400 text-[12px]">·</span>
                  <span className="flex items-center gap-0.5 shrink-0 text-[12px] text-base-300">
                    <Flag size={12} />
                    {t.dueDate ? fmtDate(t.dueDate) : '—'}
                  </span>
                  {daysLeft !== null && (
                    <span className={`ml-auto flex items-center gap-0.5 shrink-0 text-[14px] font-black ${daysLeft < 0 ? 'text-red-500' : daysLeft <= 3 ? 'text-red-400' : 'text-red-300'}`}>
                      <ClockAlert size={14} />
                      {daysLeft < 0 ? `逾期${-daysLeft}天` : `还剩${daysLeft}天`}
                    </span>
                  )}
                </div>
              </button>
            )
          })}
        </div>
      </div>
    </div>
  )
}
