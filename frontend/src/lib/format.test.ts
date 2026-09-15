import { describe, expect, it } from 'vitest'
import { daysUntil, fmtDate, fmtDuration, isTaskActive, todayISO, toISO } from './format'

describe('format 日期工具', () => {
  it('todayISO 返回本地日期 YYYY-MM-DD', () => {
    expect(todayISO()).toMatch(/^\d{4}-\d{2}-\d{2}$/)
  })

  it('toISO 本地时区格式化', () => {
    const d = new Date(2026, 8, 5, 12, 0) // 2026-09-05
    expect(toISO(d)).toBe('2026-09-05')
  })

  it('daysUntil 计算天数差', () => {
    const today = todayISO()
    expect(daysUntil(today)).toBe(0)
  })

  it('fmtDate 输出 09.18 格式，空值返回 --', () => {
    expect(fmtDate('2026-09-18')).toBe('09.18')
    expect(fmtDate(undefined)).toBe('--')
    expect(fmtDate('bad')).toBe('bad')
  })

  it('fmtDuration 小时分钟格式', () => {
    expect(fmtDuration(0)).toBe('0h')
    expect(fmtDuration(46 * 60 + 32)).toBe('46h 32m')
  })
})

describe('任务状态判定', () => {
  it('完成/停滞/停止视为 inactive', () => {
    expect(isTaskActive({ id: '1', status: '进行中', overdue: false } as never)).toBe(true)
    expect(isTaskActive({ id: '1', status: '已完成', overdue: false } as never)).toBe(false)
    expect(isTaskActive({ id: '1', status: '停滞', overdue: false } as never)).toBe(false)
    expect(isTaskActive({ id: '1', status: '已停止', overdue: false } as never)).toBe(false)
    expect(isTaskActive({ id: '1', overdue: false } as never)).toBe(true)
  })
})
