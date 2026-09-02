import { useEffect, useState } from 'react'
import { Flag } from 'lucide-react'
import type { Milestone } from '../types'
import { fmtDate } from '../lib/format'
import { useCountUp } from '../lib/useCountUp'

interface CountdownRowProps {
  milestones: Milestone[]
}

interface Remain {
  days: number
  hours: number
  minutes: number
  seconds: number
}

/** 精确剩余时间（到里程碑当天 0 点） */
function remaining(iso: string): Remain {
  const [y, m, d] = iso.split('-').map(Number)
  const target = new Date(y, (m || 1) - 1, d || 1).getTime()
  const diff = Math.max(0, target - Date.now())
  return {
    days: Math.floor(diff / 86400000),
    hours: Math.floor((diff % 86400000) / 3600000),
    minutes: Math.floor((diff % 3600000) / 60000),
    seconds: Math.floor((diff % 60000) / 1000)
  }
}

const pad = (n: number) => String(n).padStart(2, '0')

function MilestoneCard({ m, i }: { m: Milestone; i: number }) {
  const [now, setNow] = useState(() => Date.now())
  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), 1000)
    return () => clearInterval(id)
  }, [])

  const overdue = m.daysLeft < 0
  const r = remaining(m.date)
  const days = useCountUp(overdue ? 0 : r.days)
  const [dh, dm, ds] = [pad(r.hours), pad(r.minutes), pad(r.seconds)]

  return (
    <div
      className={`panel hud-frame p-4 flex flex-col gap-1.5 pulse-slow anim-enter ${
        overdue ? 'border-red-500/50' : ''
      }`}
      style={{ animationDelay: `${i * 90}ms` }}
    >
      <div className="flex items-center justify-between">
        <span className="panel-title">{m.name}</span>
        <Flag size={13} className={overdue ? 'text-red-400' : 'text-accent-bright'} />
      </div>

      {overdue ? (
        <span className="text-3xl font-bold text-red-400 num-mono leading-none pulse-soft">
          已超期
        </span>
      ) : (
        <>
          <div className="flex items-baseline gap-1.5">
            <span className="text-5xl font-bold text-accent-bright num-mono leading-none glow-num">
              {days}
            </span>
            <span className="text-[11px] tracking-[0.2em] text-base-300">天</span>
          </div>
          <div className="num-mono text-[13px] text-accent-bright tracking-[0.2em] flex items-center gap-1">
            <span className="text-[9px] text-base-400">剩余</span>
            {dh}:{dm}:
            <span key={ds} className="tick-pop">
              {ds}
            </span>
          </div>
        </>
      )}

      <div className="num-mono text-[11px] text-base-300">
        {fmtDate(m.date)} · {m.note || '截止'}
      </div>
    </div>
  )
}

export default function CountdownRow({ milestones }: CountdownRowProps) {
  if (!milestones || milestones.length === 0) return null
  return (
    <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
      {milestones.map((m, i) => (
        <MilestoneCard key={m.id} m={m} i={i} />
      ))}
    </div>
  )
}
