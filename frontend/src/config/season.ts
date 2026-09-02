export interface SeasonMilestone {
  id: string
  name: string
  date: string
  /** 节点说明（可选） */
  note?: string
}

/**
 * 本赛季关键节点。日期改动只改这里，组件不写死。
 *
 * 官方赛程依据（RoboMaster 官网 robomasters.com）：
 * - RMUL 2026 高校联盟赛：内地站点 2026 年 3 月 - 4 月（山东站 3 月 19 - 22 日，齐鲁工业大学承办）
 * - RMUC 2026 区域赛：2026 年 5 月 - 6 月（南部 5/13-17 长沙、东部 5/20-25 济南、北部 5/29-6/2 沈阳）
 * - RMUC 2026 全国赛：2026 年 7 月 - 8 月（深圳总决赛 7/31-8/9）
 * 2026 赛季已于 2026 年 8 月结束，当前为备战下赛季。以下为下一赛季（2027）推算值，
 * 官方 2027 赛程公布前先按 2026 官方节奏占位，可随时调整。
 */
export const seasonMilestones: SeasonMilestone[] = [
  {
    id: 'full-build',
    name: '完整形态',
    date: '2027-01-10',
    note: '官方完整形态考核'
  },
  {
    id: 'league',
    name: '联盟赛',
    date: '2027-03-20',
    note: 'RMUL 高校联盟赛 · 山东站'
  },
  {
    id: 'regional',
    name: '区域赛',
    date: '2027-05-20',
    note: 'RMUC 区域赛'
  }
]
