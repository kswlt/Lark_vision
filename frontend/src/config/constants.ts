import type { Group, Priority, Robot } from '../types'

export const GROUPS: Group[] = ['算法', '电控', '机械', '运营']

export const ROBOTS: Robot[] = ['重装', '步兵1', '步兵2', '哨兵', '工程', '雷达', '飞镖']

export const PRIORITY_LABEL: Record<Priority, string> = {
  super_urgent: '超紧急限时',
  important_urgent: '重要紧急',
  important: '重要',
  normal: '一般'
}

export const PRIORITY_ORDER: Record<Priority, number> = {
  super_urgent: -1,
  important_urgent: 0,
  important: 1,
  normal: 2
}

export const DATA_SOURCE_LABEL: Record<string, string> = {
  mock: '模拟数据',
  feishu: '飞书实时'
}
