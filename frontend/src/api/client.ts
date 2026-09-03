import type {
  Dashboard,
  DutyDay,
  GroupSummary,
  Health,
  PeopleSummary,
  RobotSummary,
  Task,
  WorktimePerson
} from '../types'

async function get<T>(path: string): Promise<T> {
  const res = await fetch(path, { headers: { Accept: 'application/json' } })
  if (!res.ok) throw new Error(`API ${path} -> ${res.status}`)
  return res.json() as Promise<T>
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
  health: () => get<Health>('/api/health')
}
