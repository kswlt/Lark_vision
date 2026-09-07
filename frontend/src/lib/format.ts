/**
 * 日期工具：一律使用本地时区，避免 ISO UTC 偏移导致日期错位。
 */

export function todayISO(): string {
  const d = new Date()
  return toISO(d)
}

export function toISO(d: Date): string {
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

/** daysUntil = target - today（可为负） */
export function daysUntil(iso: string): number {
  return Math.floor((parseISO(iso).getTime() - startOfToday().getTime()) / 86400000)
}

function startOfToday(): Date {
  const d = new Date()
  d.setHours(0, 0, 0, 0)
  return d
}

function parseISO(iso: string): Date {
  const [y, m, d] = iso.split('-').map(Number)
  return new Date(y, (m || 1) - 1, d || 1)
}

/** 09.18 格式 */
export function fmtDate(iso?: string): string {
  if (!iso) return '--'
  const p = iso.split('-')
  if (p.length !== 3) return iso
  return `${p[1]}.${p[2]}`
}

/** 46h 32m 格式 */
export function fmtDuration(minutes: number): string {
  if (!minutes || minutes <= 0) return '0h'
  const h = Math.floor(minutes / 60)
  const m = Math.round(minutes % 60)
  return `${h}h ${String(m).padStart(2, '0')}m`
}

/** 中文时长：X天 / X小时 / X分钟 */
export function fmtAgo(days: number): string {
  if (days <= 0) return '今天'
  if (days === 1) return '1天'
  return `${days}天`
}

import type { Task } from '../types'

/** 已完结（完成/停滞/停止）的任务视为不再进行中 */
export function isTaskInactive(t: Task): boolean {
  const s = t.status || ''
  return s.includes('完成') || s.includes('停滞') || s.includes('停止')
}

/** 只保留进行中任务 */
export function isTaskActive(t: Task): boolean {
  return !isTaskInactive(t)
}
