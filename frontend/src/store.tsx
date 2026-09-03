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

  const refresh = useCallback(() => setTick((t) => t + 1), [])

  // 自动轮询：每 60 秒自动刷新一次，跟随飞书多维表格/考勤最新数据
  useEffect(() => {
    const id = setInterval(() => refresh(), 60_000)
    return () => clearInterval(id)
  }, [refresh])

  useEffect(() => {
    let alive = true
    setLoading(true)
    setError(null)
    Promise.allSettled([
      api.tasks(),
      api.dashboard(),
      api.groups(),
      api.robots(),
      api.worktime('week'),
      api.worktime('month'),
      api.unchecked(),
      api.faceCheckin(),
      api.duty(),
      api.people(),
      api.health()
    ]).then((results) => {
      if (!alive) return
      const [t, d, g, r, ww, wm, u, fc, dy, p, h] = results
      if (t.status === 'fulfilled') setTasks(t.value)
      if (d.status === 'fulfilled') setDashboard(d.value)
      if (g.status === 'fulfilled') setGroups(g.value)
      if (r.status === 'fulfilled') setRobots(r.value)
      if (ww.status === 'fulfilled') setWorktimeWeek(ww.value)
      if (wm.status === 'fulfilled') setWorktimeMonth(wm.value)
      if (u.status === 'fulfilled') setUnchecked(u.value.names ?? [])
      if (fc.status === 'fulfilled') setFaceCheckin(fc.value.names ?? [])
      if (dy.status === 'fulfilled') setDuty(dy.value)
      if (p.status === 'fulfilled') setPeople(p.value)
      if (h.status === 'fulfilled') setHealth(h.value)
      const failed = results.filter((x) => x.status === 'rejected')
      if (failed.length) setError(`部分数据加载失败 (${failed.length})`)
      setLoading(false)
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
      refresh
    }),
    [tasks, dashboard, groups, robots, worktimeWeek, worktimeMonth, people, health, duty, unchecked, faceCheckin, loading, error, refresh]
  )

  return <DataContext.Provider value={value}>{children}</DataContext.Provider>
}

export function useData(): DataState {
  const ctx = useContext(DataContext)
  if (!ctx) throw new Error('useData must be used within DataProvider')
  return ctx
}
