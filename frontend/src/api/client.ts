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
} from '../types'

/** 统一 API 错误：携带 HTTP 状态码（0 = 网络/超时） */
export class ApiError extends Error {
  readonly status: number
  constructor(message: string, status: number) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

/** 默认请求超时：15s（防止飞书慢接口挂住页面） */
export const DEFAULT_TIMEOUT_MS = 15_000

interface GetOptions {
  signal?: AbortSignal
  timeoutMs?: number
}

export async function get<T>(path: string, opts?: GetOptions): Promise<T> {
  const ctrl = new AbortController()
  const timeout = opts?.timeoutMs ?? DEFAULT_TIMEOUT_MS
  const timer = setTimeout(() => ctrl.abort(), timeout)
  const signal = opts?.signal ?? ctrl.signal
  try {
    const res = await fetch(path, {
      headers: { Accept: 'application/json' },
      signal
    })
    if (!res.ok) {
      throw new ApiError(`API ${path} -> ${res.status}`, res.status)
    }
    return res.json() as Promise<T>
  } catch (e) {
    if (e instanceof ApiError) throw e
    if (e instanceof DOMException && e.name === 'AbortError') {
      throw new ApiError(`API ${path} 请求超时（${timeout}ms）`, 0)
    }
    throw new ApiError(`API ${path} 网络错误`, 0)
  } finally {
    clearTimeout(timer)
  }
}

export const api = {
  tasks: () => get<Task[]>('/api/tasks'),
  dashboard: () => get<Dashboard>('/api/dashboard'),
  groups: () => get<GroupSummary[]>('/api/groups'),
  robots: () => get<RobotSummary[]>('/api/robots'),
  worktime: (range: 'week' | 'month' = 'week') =>
    get<WorktimePerson[]>(`/api/worktime/leaderboard?range=${range}`),
  unchecked: () =>
    get<{ names: string[]; date: string }>('/api/worktime/unchecked'),
  faceCheckin: () =>
    get<{ names: string[]; date: string }>('/api/attendance/face-checkin'),
  duty: () => get<DutyDay[]>('/api/duty'),
  people: () => get<PeopleSummary[]>('/api/people'),
  health: () => get<Health>('/api/health'),
  meta: () => get<TeamMeta>('/api/meta')
}
