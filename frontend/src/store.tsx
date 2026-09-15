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
  TeamMeta,
  WorktimePerson
} from './types'

/** 主数据（任务/看板/组别/兵种）刷新间隔：30s（后端有缓存，不直接打飞书） */
export const CORE_REFRESH_MS = 30_000
/** 工时/考勤/值日等扩展数据刷新间隔：5min */
export const EXTRA_REFRESH_MS = 5 * 60_000

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
  meta: TeamMeta | null
  /** 正在显示缓存数据（飞书不可用 / 数据过期） */
  stale: boolean
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
  const [meta, setMeta] = useState<TeamMeta | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [tick, setTick] = useState(0)
  const [lastRefresh, setLastRefresh] = useState(Date.now())

  const refresh = useCallback(() => {
    setLoading(true)
    setTick((t) => t + 1)
  }, [])

  // 核心数据：tasks / dashboard / groups / robots / health / meta
  const loadCore = useCallback(async () => {
    const results = await Promise.allSettled([
      api.tasks(),
      api.dashboard(),
      api.groups(),
      api.robots(),
      api.health(),
      api.meta()
    ])
    const [t, d, g, r, h, m] = results
    if (t.status === 'fulfilled') setTasks(t.value)
    if (d.status === 'fulfilled') setDashboard(d.value)
    if (g.status === 'fulfilled') setGroups(g.value)
    if (r.status === 'fulfilled') setRobots(r.value)
    if (h.status === 'fulfilled') setHealth(h.value)
    if (m.status === 'fulfilled') setMeta(m.value)
    const failed = results.filter((x) => x.status === 'rejected')
    if (failed.length) setError(`部分数据加载失败 (${failed.length})，正在显示缓存数据`)
    else setError(null)
  }, [])

  // 扩展数据：工时 / 未打卡 / 人脸打卡 / 值日 / 成员
  const loadExtra = useCallback(async () => {
    const results = await Promise.allSettled([
      api.worktime('week'),
      api.worktime('month'),
      api.unchecked(),
      api.faceCheckin(),
      api.duty(),
      api.people()
    ])
    const [ww, wm, u, fc, dy, p] = results
    if (ww.status === 'fulfilled') setWorktimeWeek(ww.value)
    if (wm.status === 'fulfilled') setWorktimeMonth(wm.value)
    if (u.status === 'fulfilled') setUnchecked(u.value.names ?? [])
    if (fc.status === 'fulfilled') setFaceCheckin(fc.value.names ?? [])
    if (dy.status === 'fulfilled') setDuty(dy.value)
    if (p.status === 'fulfilled') setPeople(p.value)
  }, [])

  // 初始 + 手动刷新：全部加载
  useEffect(() => {
    let alive = true
    const run = async () => {
      await loadCore()
      await loadExtra()
      if (!alive) return
      setLoading(false)
      setLastRefresh(Date.now())
    }
    void run()
    return () => {
      alive = false
    }
  }, [tick, loadCore, loadExtra])

  // 主数据周期刷新（30s）+ 扩展数据周期刷新（5min）
  // 标签页隐藏时暂停刷新；恢复可见时立即补一次
  useEffect(() => {
    let hidden = document.hidden

    const coreLoop = () => {
      if (document.hidden) return
      void loadCore()
      setLastRefresh(Date.now())
    }
    const extraLoop = () => {
      if (document.hidden) return
      void loadExtra()
    }
    const coreId = window.setInterval(coreLoop, CORE_REFRESH_MS)
    const extraId = window.setInterval(extraLoop, EXTRA_REFRESH_MS)

    const onVisibility = () => {
      const nowHidden = document.hidden
      const becameVisible = hidden && !nowHidden
      hidden = nowHidden
      if (becameVisible) {
        // 从隐藏恢复到可见：立即刷新一次（定时器休眠期间数据可能过期）
        coreLoop()
        extraLoop()
      }
    }
    document.addEventListener('visibilitychange', onVisibility)
    return () => {
      if (coreId !== undefined) window.clearInterval(coreId)
      if (extraId !== undefined) window.clearInterval(extraId)
      document.removeEventListener('visibilitychange', onVisibility)
    }
  }, [loadCore, loadExtra])

  const stale = health?.stale ?? false

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
      meta,
      stale,
      loading,
      error,
      lastRefresh,
      refresh
    }),
    [tasks, dashboard, groups, robots, worktimeWeek, worktimeMonth, people, health, duty, unchecked, faceCheckin, meta, stale, loading, error, lastRefresh, refresh]
  )

  return <DataContext.Provider value={value}>{children}</DataContext.Provider>
}

export function useData(): DataState {
  const ctx = useContext(DataContext)
  if (!ctx) throw new Error('useData must be used within DataProvider')
  return ctx
}
