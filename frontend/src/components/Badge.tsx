import type { Group, Priority, Robot } from '../types'

export const GROUP_DOT: Record<Group, string> = {
  算法: '#3fb6b6',
  电控: '#7aa2f7',
  机械: '#b48ead',
  运营: '#a3be8c'
}

const badgeBase = 'inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-medium leading-none whitespace-nowrap'

export function GroupBadge({ group }: { group?: Group | null }) {
  if (!group) return null
  return (
    <span className={`${badgeBase} bg-base-700 text-gray-300`}>
      <span className="w-1.5 h-1.5 rounded-full" style={{ background: GROUP_DOT[group] }} />
      {group}
    </span>
  )
}

export function RobotBadge({ robot }: { robot?: Robot | null }) {
  if (!robot) return null
  return (
    <span className={`${badgeBase} bg-base-700 text-gray-400`}>
      <span className="w-1 h-1 rounded-sm bg-base-400" />
      {robot}
    </span>
  )
}

export function PriorityBadge({ priority }: { priority: Priority }) {
  if (priority === 'important_urgent') {
    return (
      <span className={`${badgeBase} bg-red-500/15 text-red-400 ring-1 ring-red-500/30 pulse-soft`}>
        重要紧急
      </span>
    )
  }
  if (priority === 'important') {
    return (
      <span className={`${badgeBase} bg-amber-500/15 text-amber-400 ring-1 ring-amber-500/30 pulse-soft`}>
        重要
      </span>
    )
  }
  return (
    <span className={`${badgeBase} bg-base-700 text-base-300`}>一般</span>
  )
}

export function OverdueBadge({ days }: { days?: number }) {
  return (
    <span className={`${badgeBase} bg-red-500/15 text-red-400 ring-1 ring-red-500/30 pulse-soft`}>
      {days && days > 0 ? `已延期 ${days} 天` : '已延期'}
    </span>
  )
}

export function BlockedBadge() {
  return (
    <span className={`${badgeBase} bg-red-500/15 text-red-400 ring-1 ring-red-500/30 pulse-soft`}>
      阻塞
    </span>
  )
}

export function StaleBadge({ days }: { days?: number }) {
  return (
    <span className={`${badgeBase} bg-amber-500/15 text-amber-400 ring-1 ring-amber-500/30 pulse-soft`}>
      {days ? `${days} 日未更新` : '久未更新'}
    </span>
  )
}
