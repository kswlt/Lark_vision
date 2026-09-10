import { useEffect, useState } from 'react'
import { NavLink } from 'react-router-dom'
import { Bot, ClipboardList, LayoutDashboard, Moon, Network, Play, RefreshCw, Sun, Users } from 'lucide-react'
import { useData } from '../store'
import { DATA_SOURCE_LABEL } from '../config/constants'
import PromoVideoPlayer from './PromoVideoPlayer'

const THEME_KEY = 'rm_theme_v1'
const DAILY_REFRESH_HOUR = 17
const DAILY_REFRESH_MINUTE = 30

function useTheme(): [boolean, () => void] {
  const [dark, setDark] = useState(() => {
    try {
      return localStorage.getItem(THEME_KEY) === 'dark'
    } catch {
      return false
    }
  })
  useEffect(() => {
    const root = document.documentElement
    if (dark) {
      root.classList.add('dark')
    } else {
      root.classList.remove('dark')
    }
    try {
      localStorage.setItem(THEME_KEY, dark ? 'dark' : 'light')
    } catch {
      /* ignore */
    }
  }, [dark])
  return [dark, () => setDark((d) => !d)]
}

/** 计算下次自动刷新时间（每天 17:30） */
function getNextRefreshTime(now: Date): Date {
  const next = new Date(now)
  next.setHours(DAILY_REFRESH_HOUR, DAILY_REFRESH_MINUTE, 0, 0)
  if (next <= now) {
    next.setDate(next.getDate() + 1)
  }
  return next
}

/** 格式化时间为 MM-DD HH:mm */
function formatRefreshTime(d: Date): string {
  return `${pad2(d.getMonth() + 1)}-${pad2(d.getDate())} ${pad2(d.getHours())}:${pad2(d.getMinutes())}`
}

const NAV = [
  { to: '/dashboard', label: '首页', icon: LayoutDashboard },
  { to: '/tasks', label: '任务', icon: ClipboardList },
  { to: '/groups', label: '组别', icon: Network },
  { to: '/robots', label: '兵种', icon: Bot },
  { to: '/people', label: '成员', icon: Users }
]

const pad2 = (n: number) => String(n).padStart(2, '0')

/** 每秒刷新的实时时钟 */
function useClock(): Date {
  const [now, setNow] = useState(() => new Date())
  useEffect(() => {
    const id = setInterval(() => setNow(new Date()), 1000)
    return () => clearInterval(id)
  }, [])
  return now
}

interface TopBarProps {
  scale: number
  onScaleUp: () => void
  onScaleDown: () => void
}

/** 顶部导航栏：品牌 + 导航 + 时钟 + 数据源 + 刷新 + 缩放 */
export default function TopBar({ scale, onScaleUp, onScaleDown }: TopBarProps) {
  const { health, loading, refresh, lastRefresh } = useData()
  const clock = useClock()
  const [dark, toggleDark] = useTheme()
  const live = health?.dataSource === 'feishu'
  const source = health?.dataSource ?? 'mock'
  const [showPromo, setShowPromo] = useState(false)
  const nextRefresh = getNextRefreshTime(clock)
  const lastRefreshStr = formatRefreshTime(new Date(lastRefresh))

  // URL参数自动播放宣传片：?autoplay=promo
  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    if (params.get('autoplay') === 'promo') {
      // 延迟一点，确保页面加载完成
      setTimeout(() => setShowPromo(true), 1000)
    }
  }, [])

  return (
    <>
    <header className="h-14 shrink-0 flex items-center gap-4 px-4 bg-base-850 border-b border-base-600 relative z-20">
      {/* 品牌 */}
      <div className="flex items-center gap-2.5 shrink-0 pr-2">
        <img
          src="/logo-team.png"
          alt="Adam"
          className="h-9 w-9 object-contain drop-shadow-sm"
        />
        <div className="leading-none">
          <div className="text-[14px] font-black tracking-[0.06em] text-gray-100">
            Adam 进度管理系统
          </div>
          <img
            src="/rm-logo.png"
            alt="RM"
            className="h-[12px] mt-1.5 object-contain opacity-90"
          />
        </div>
      </div>

      <div className="w-px h-6 bg-base-600 shrink-0" />

      {/* 导航 */}
      <nav className="flex items-center gap-1">
        {NAV.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              `flex items-center gap-1.5 px-3 py-1.5 rounded text-[12px] transition-colors ${
                isActive
                  ? 'bg-accent-faint text-accent-bright shadow-[inset_0_-2px_0_0_rgba(29,95,214,0.6)]'
                  : 'text-base-300 hover:text-gray-200 hover:bg-base-700'
              }`
            }
          >
            <Icon size={15} strokeWidth={1.8} />
            {label}
          </NavLink>
        ))}
      </nav>

      <div className="flex-1" />

      {/* 时钟 */}
      <span className="num-mono text-[12px] text-gray-300 flex items-center gap-1 px-2 py-1 rounded border border-base-600">
        <span className="w-1.5 h-1.5 rounded-full bg-accent-bright live-dot" />
        {pad2(clock.getMonth() + 1)}-{pad2(clock.getDate())}
        <span className="text-accent-bright px-0.5">{pad2(clock.getHours())}:{pad2(clock.getMinutes())}</span>
        <span key={clock.getSeconds()} className="tick-pop text-accent-bright">
          :{pad2(clock.getSeconds())}
        </span>
      </span>

      {/* 宣传片按钮 */}
      <button
        onClick={() => setShowPromo(true)}
        className="flex items-center gap-1.5 px-2.5 py-1 rounded border border-base-600 text-[10px] text-base-300 hover:text-white hover:border-accent-bright hover:bg-accent-bright/10 transition-all clickable"
        title="点击进入全屏循环播放宣传片（双击退出）"
      >
        <Play size={11} className="text-accent-bright" />
        宣传片
      </button>

      {/* 刷新按钮 + 刷新时间提示 */}
      <div className="flex items-center gap-1">
        <button
          onClick={refresh}
          className="flex items-center gap-1.5 px-2 py-1 rounded border border-base-600 text-[10px] text-base-300 hover:text-gray-200 clickable"
          title={`手动刷新\n上次刷新: ${lastRefreshStr}\n下次自动刷新: ${formatRefreshTime(nextRefresh)}`}
        >
          <RefreshCw size={11} className={loading ? 'spin' : ''} />
          刷新
        </button>
        <span className="num-mono text-[9px] text-base-400 hidden xl:inline">
          下次 {pad2(nextRefresh.getHours())}:{pad2(nextRefresh.getMinutes())}
        </span>
      </div>

      {/* 深色模式切换 */}
      <button
        onClick={toggleDark}
        className="flex items-center justify-center w-8 h-8 rounded border border-base-600 text-base-300 hover:text-gray-200 clickable"
        title={dark ? '切换浅色模式' : '切换深色模式'}
      >
        {dark ? <Sun size={14} /> : <Moon size={14} />}
      </button>

      {/* 缩放 */}
      <div className="flex items-center gap-1 px-1.5 py-1 rounded border border-base-600">
        <button
          onClick={onScaleDown}
          className="px-1 py-0.5 rounded text-[10px] text-base-300 hover:text-gray-200 clickable"
          title="缩小"
        >
          A−
        </button>
        <span className="num-mono w-10 text-center text-[10px] text-base-300">
          {Math.round(scale * 100)}%
        </span>
        <button
          onClick={onScaleUp}
          className="px-1 py-0.5 rounded text-[10px] text-base-300 hover:text-gray-200 clickable"
          title="放大"
        >
          A+
        </button>
      </div>
    </header>

    {/* 全屏宣传片播放器 */}
    {showPromo && <PromoVideoPlayer onClose={() => setShowPromo(false)} />}
    </>
  )
}
