import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode
} from 'react'
import { api } from './api/client'
import type {
  Dashboard,
  DutyDay,
  GroupSummary,
  Health,
  PeopleSummary,
  RobotSummary,
  Task,
  WorktimePerson
} from './types'

interface DataState {
  tasks: Task[]
  dashboard: Dashboard | null
  groups: GroupSummary[]
  robots: RobotSummary[]
  worktimeWeek: WorktimePerson[]
  worktimeMonth: WorktimePerson[]
  people: PeopleSummary[]
  health: Health | null
  duty: DutyDay[]
  unchecked: string[]
  faceCheckin: string[]
  loading: boolean
  error: string | null
  lastRefresh: number
  refresh: () => void
}

const DataContext = createContext<DataState | null>(null)

export function DataProvider({ children }: { children: ReactNode }) {
  const [tasks, setTasks] = useState<Task[]>([])
  const [dashboard, setDashboard] = useState<Dashboard | null>(null)
  const [groups, setGroups] = useState<GroupSummary[]>([])
  const [robots, setRobots] = useState<RobotSummary[]>([])
  const [worktimeWeek, setWorktimeWeek] = useState<WorktimePerson[]>([])
  const [worktimeMonth, setWorktimeMonth] = useState<WorktimePerson[]>([])
  const [people, setPeople] = useState<PeopleSummary[]>([])
  const [health, setHealth] = useState<Health | null>(null)
  const [duty, setDuty] = useState<DutyDay[]>([])
  const [unchecked, setUnchecked] = useState<string[]>([])
  const [faceCheckin, setFaceCheckin] = useState<string[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [tick, setTick] = useState(0)
  const [lastRefresh, setLastRefresh] = useState(Date.now())

  const refresh = useCallback(() => setTick((t) => t + 1), [])

  // 自动刷新：每天 17:30 自动刷新一次（大幅降低飞书API调用）
  // 其余时间依赖手动刷新按钮
  useEffect(() => {
    const REFRESH_HOUR = 17
    const REFRESH_MINUTE = 30
    let lastRefreshDay = -1

    const checkAndRefresh = () => {
      const now = new Date()
      const today = now.getDate()
      // 每天 17:30 后触发一次（且当天还没刷新过）
      if (
        (now.getHours() > REFRESH_HOUR ||
          (now.getHours() === REFRESH_HOUR && now.getMinutes() >= REFRESH_MINUTE)) &&
        lastRefreshDay !== today
      ) {
        lastRefreshDay = today
        refresh()
      }
    }

    // 启动时检查一次
    checkAndRefresh()
    // 每分钟检查一次是否到了刷新时间（几乎不消耗API，只是本地时间判断）
    const id = setInterval(checkAndRefresh, 60_000)
    return () => clearInterval(id)
  }, [refresh])

  useEffect(() => {
    let alive = true
    setLoading(true)
    setError(null)
    // 核心数据（页面主体）与扩展数据（劳模榜/值日等）分批：
    // 核心 settle 后立即放行 loading，避免飞书慢接口（如考勤）拖住整个页面。
    Promise.allSettled([
      api.tasks(),
      api.dashboard(),
      api.groups(),
      api.robots(),
      api.health()
    ]).then((results) => {
      if (!alive) return
      const [t, d, g, r, h] = results
      if (t.status === 'fulfilled') setTasks(t.value)
      if (d.status === 'fulfilled') setDashboard(d.value)
      if (g.status === 'fulfilled') setGroups(g.value)
      if (r.status === 'fulfilled') setRobots(r.value)
      if (h.status === 'fulfilled') setHealth(h.value)
      const failed = results.filter((x) => x.status === 'rejected')
      if (failed.length) setError(`部分数据加载失败 (${failed.length})`)
      setLoading(false)
      setLastRefresh(Date.now())
    })
    Promise.allSettled([
      api.worktime('week'),
      api.worktime('month'),
      api.unchecked(),
      api.faceCheckin(),
      api.duty(),
      api.people()
    ]).then((results) => {
      if (!alive) return
      const [ww, wm, u, fc, dy, p] = results
      if (ww.status === 'fulfilled') setWorktimeWeek(ww.value)
      if (wm.status === 'fulfilled') setWorktimeMonth(wm.value)
      if (u.status === 'fulfilled') setUnchecked(u.value.names ?? [])
      if (fc.status === 'fulfilled') setFaceCheckin(fc.value.names ?? [])
      if (dy.status === 'fulfilled') setDuty(dy.value)
      if (p.status === 'fulfilled') setPeople(p.value)
    })
    return () => {
      alive = false
    }
  }, [tick])

  const value = useMemo<DataState>(
    () => ({
      tasks,
      dashboard,
      groups,
      robots,
      worktimeWeek,
      worktimeMonth,
      people,
      health,
      duty,
      unchecked,
      faceCheckin,
      loading,
      error,
      lastRefresh,
      refresh
    }),
    [tasks, dashboard, groups, robots, worktimeWeek, worktimeMonth, people, health, duty, unchecked, faceCheckin, loading, error, lastRefresh, refresh]
  )

  return <DataContext.Provider value={value}>{children}</DataContext.Provider>
}

export function useData(): DataState {
  const ctx = useContext(DataContext)
  if (!ctx) throw new Error('useData must be used within DataProvider')
  return ctx
}
