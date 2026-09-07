import { useState, useEffect } from 'react'
import { Crown, Heart, Timer } from 'lucide-react'
import { useData } from '../store'
import Avatar from './Avatar'
import { GROUP_DOT } from './Badge'
import type { Group } from '../types'

const LIKES_KEY = 'rm_leaderboard_likes_v1'

function loadLikes(): Record<string, number> {
  try {
    return JSON.parse(localStorage.getItem(LIKES_KEY) || '{}')
  } catch {
    return {}
  }
}

interface Floater {
  id: number
  userId: string
}

const LIKE_ANIMATIONS = `
@keyframes like-heartbeat {
  0% { transform: scale(1); }
  15% { transform: scale(1.35); }
  30% { transform: scale(0.9); }
  45% { transform: scale(1.25); }
  60% { transform: scale(0.95); }
  75% { transform: scale(1.1); }
  100% { transform: scale(1); }
}
@keyframes like-float-up {
  0% { opacity: 1; transform: translateY(0) scale(1); }
  50% { opacity: 1; transform: translateY(-18px) scale(1.2); }
  100% { opacity: 0; transform: translateY(-36px) scale(0.8); }
}
@keyframes like-glow {
  0% { box-shadow: 0 0 0 0 rgba(239,68,68,0.5); }
  70% { box-shadow: 0 0 0 10px rgba(239,68,68,0); }
  100% { box-shadow: 0 0 0 0 rgba(239,68,68,0); }
}
.like-heart-anim { animation: like-heartbeat 0.6s ease-in-out; }
.like-floater { animation: like-float-up 0.8s ease-out forwards; }
.like-glow-anim { animation: like-glow 0.6s ease-out; }
`

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
  const [likes, setLikes] = useState<Record<string, number>>(loadLikes)
  const [floaters, setFloaters] = useState<Floater[]>([])
  const [heartAnim, setHeartAnim] = useState<Record<string, number>>({})
  const floaterId = useState({ value: 0 })[0]

  useEffect(() => {
    try { localStorage.setItem(LIKES_KEY, JSON.stringify(likes)) } catch { /* ignore */ }
  }, [likes])

  const handleLike = (userId: string) => {
    setLikes((prev) => ({ ...prev, [userId]: (prev[userId] || 0) + 1 }))
    // 爱心跳动动画
    setHeartAnim((prev) => ({ ...prev, [userId]: (prev[userId] || 0) + 1 }))
    // 飘升 +1
    const id = ++floaterId.value
    setFloaters((prev) => [...prev, { id, userId }])
    setTimeout(() => {
      setFloaters((prev) => prev.filter((f) => f.id !== id))
    }, 800)
  }

  const full = range === 'week' ? worktimeWeek : worktimeMonth
  const minutesOf = (p: WorktimeEntry) =>
    range === 'week' ? p.weekMinutes ?? 0 : p.monthMinutes ?? 0
  // 综合分数 = 工时小时数 + 点赞数 * 0.05（点赞权重很低，工时为主）
  const scoreOf = (p: WorktimeEntry) =>
    minutesOf(p) / 60 + (likes[p.userId] || 0) * 0.05
  // 按综合分数降序排序
  const sorted = [...full].sort((a, b) => scoreOf(b) - scoreOf(a))
  // 前 3 用高亮样式，第 4 名起复用普通样式
  const list = sorted.map((p, i) => ({ p, s: RANK_STYLE[Math.min(i, 2)] }))

  return (
    <div className="panel hud-frame px-2.5 py-1.5 flex flex-col anim-enter-slow">
      <style>{LIKE_ANIMATIONS}</style>
      <div className="flex items-center justify-between mb-1 shrink-0">
        <span className="panel-title flex items-center gap-1">
          <Timer size={10} />
          劳模榜 · 综合排行
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
        <div className="space-y-1.5 max-h-[260px] overflow-y-auto leader-scroll pr-1">
          {list.map(({ p, s }, i) => {
            const dur = splitDur(minutesOf(p))
            return (
              <div
                key={p.userId}
                className={`flex items-center gap-2.5 rounded-md border px-2.5 py-2 card-lift anim-enter ${s.card}`}
                style={{ animationDelay: `${Math.min(i, 8) * 60}ms` }}
              >
                {s.big && <Crown size={12} className="text-accent-bright shrink-0" />}
                <span
                  className={`num-mono text-[11px] font-bold px-1.5 py-0.5 rounded shrink-0 w-6 text-center ${s.chip}`}
                >
                  {String(i + 1).padStart(2, '0')}
                </span>
                <Avatar name={p.userName} url={p.avatarUrl} size={26} />
                <span className="text-[14px] font-semibold text-gray-100 truncate w-20 shrink-0">
                  {p.userName || '未命名'}
                </span>
                <div className="flex items-center gap-2 ml-auto shrink-0">
                  <div className="flex items-baseline gap-0.5">
                    <span className={`num-mono font-bold text-[18px] leading-none ${s.num}`}>
                      {dur.h}
                    </span>
                    <span className={`num-mono text-[11px] leading-none ${s.num}`}>h</span>
                    <span className="num-mono text-[13px] text-gray-300 leading-none">
                      {dur.m}m
                    </span>
                  </div>
                  {/* 点赞按钮 */}
                  <div className="relative flex items-center">
                    <button
                      onClick={() => handleLike(p.userId)}
                      className={`relative flex items-center gap-0.5 px-1.5 py-1 rounded-full transition-all cursor-pointer text-red-500 hover:bg-red-500/10 active:scale-90 ${
                        heartAnim[p.userId] ? 'like-glow-anim' : ''
                      }`}
                      title="点赞支持"
                    >
                      <Heart
                        key={heartAnim[p.userId] || 0}
                        size={14}
                        fill="currentColor"
                        strokeWidth={2}
                        className={heartAnim[p.userId] ? 'like-heart-anim' : ''}
                      />
                      {(likes[p.userId] || 0) > 0 && (
                        <span className="num-mono text-[11px] font-bold leading-none">
                          {likes[p.userId]}
                        </span>
                      )}
                    </button>
                    {/* 飘升 +1 */}
                    {floaters
                      .filter((f) => f.userId === p.userId)
                      .map((f) => (
                        <span
                          key={f.id}
                          className="like-floater absolute -top-1 left-1/2 -translate-x-1/2 text-red-500 font-bold text-[12px] pointer-events-none whitespace-nowrap"
                        >
                          +1
                        </span>
                      ))}
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
