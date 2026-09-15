export type Group = '算法' | '电控' | '机械' | '运营'
export type Robot = '重装' | '步兵' | '哨兵' | '雷达' | '飞镖'
export type Priority = 'super_urgent' | 'important_urgent' | 'important' | 'normal'

export interface Task {
  id: string
  title: string
  group?: Group
  robot?: Robot | null
  ownerId?: string
  ownerName?: string
  ownerAvatarUrl?: string
  dueDate?: string
  actualFinishDate?: string
  overdue: boolean
  overdueDays?: number
  priority: Priority
  latestUpdate?: string
  latestUpdateTime?: string
  daysSinceUpdate?: number
  dependency?: string
  blocked?: boolean
  status?: string
  history?: TaskUpdate[]
}

export interface TaskUpdate {
  time?: string
  text?: string
}

export interface Milestone {
  id: string
  name: string
  date: string
  daysLeft: number
  overdue: boolean
  note?: string
}

export interface MatrixCell {
  total: number
  overdue: number
}

export interface MatrixRow {
  robot: Robot | null
  cells: Record<Group, MatrixCell>
}

export interface TrendPoint {
  date: string
  done: number
  cum: number
}

export interface Dashboard {
  counts: {
    total: number
    done: number
    overdue: number
    critical: number
    blocked: number
    stale: number
    dueSoon: number
  }
  highlights: Task[]
  timeline: Task[]
  matrix: MatrixRow[]
  trend: TrendPoint[]
}

export interface GroupSummary {
  group: Group
  total: number
  overdue: number
  critical: number
  blocked: number
  stale: number
}

export interface RobotSummary {
  robot: Robot | 'none'
  total: number
  done: number
  overdue: number
  critical: number
  blocked: number
  stale: number
  dueSoon: number
}

export interface WorktimePerson {
  userId: string
  userName: string
  group?: string
  avatarUrl?: string
  weekMinutes: number
  monthMinutes: number
}

export interface PeopleSummary {
  userId: string
  userName: string
  group?: string
  avatarUrl?: string
  weekMinutes: number
  monthMinutes: number
  activeTasks: number
  overdueTasks: number
}

export interface Health {
  status: string
  version: string
  dataSource: 'mock' | 'feishu'
  data_source?: 'mock' | 'feishu'
  feishu: 'ok' | 'degraded'
  last_success_sync?: string | null
  cache_age?: number | null
  stale: boolean
  timestamp: string
}

/** 统一队伍配置（GET /api/meta，来源 backend/config/team.yaml） */
export interface TeamMeta {
  teamName: string
  groups: string[]
  robots: string[]
  groupAliases: Record<string, string>
  robotAliases: Record<string, string | null>
  priorityLabels: Record<string, string>
}

export interface DutyDay {
  date: string
  name: string
  isToday: boolean
}
