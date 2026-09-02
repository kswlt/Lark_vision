import { useMemo, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { LayoutGrid, List, Rows3, Search } from 'lucide-react'
import { useData } from '../store'
import TaskCard from '../components/TaskCard'
import TaskDrawer from '../components/TaskDrawer'
import Avatar from '../components/Avatar'
import {
  GroupBadge,
  OverdueBadge,
  PriorityBadge,
  RobotBadge,
  StaleBadge,
  BlockedBadge
} from '../components/Badge'
import { GROUPS, ROBOTS, PRIORITY_LABEL, PRIORITY_ORDER } from '../config/constants'
import { daysUntil, fmtAgo, fmtDate } from '../lib/format'
import type { Group, Priority, Robot, Task } from '../types'

type QuickFilter = 'all' | 'overdue' | 'critical' | 'blocked' | 'stale' | 'dueSoon'
type ViewMode = 'card' | 'list' | 'table'
type SortKey = 'id' | 'due' | 'update' | 'priority'

const QUICK: { key: QuickFilter; label: string }[] = [
  { key: 'all', label: '全部' },
  { key: 'overdue', label: '已延期' },
  { key: 'critical', label: '重要紧急' },
  { key: 'blocked', label: '阻塞' },
  { key: 'stale', label: '3日未更新' },
  { key: 'dueSoon', label: '7日内截止' }
]

export default function Tasks() {
  const { tasks } = useData()
  const [params, setParams] = useSearchParams()
  const [quick, setQuick] = useState<QuickFilter>('all')
  const [group, setGroup] = useState<Group | ''>(params.get('group') as Group | '' || '')
  const [robot, setRobot] = useState<Robot | 'none' | ''>(
    (params.get('robot') as Robot | 'none' | '') || ''
  )
  const [priority, setPriority] = useState<Priority | ''>('')
  const [owner, setOwner] = useState('')
  const [query, setQuery] = useState('')
  const [view, setView] = useState<ViewMode>('card')
  const [sort, setSort] = useState<SortKey>('priority')
  const [selected, setSelected] = useState<Task | null>(null)

  const owners = useMemo(() => {
    const set = new Set<string>()
    tasks.forEach((t) => t.ownerName && set.add(t.ownerName))
    return [...set].sort()
  }, [tasks])

  const filtered = useMemo(() => {
    let list = [...tasks]
    if (quick === 'overdue') list = list.filter((t) => t.overdue)
    if (quick === 'critical') list = list.filter((t) => t.priority === 'important_urgent')
    if (quick === 'blocked') list = list.filter((t) => t.blocked)
    if (quick === 'stale')
      list = list.filter((t) => t.daysSinceUpdate !== undefined && t.daysSinceUpdate >= 3)
    if (quick === 'dueSoon') {
      list = list.filter((t) => {
        if (!t.dueDate || t.overdue) return false
        const d = daysUntil(t.dueDate)
        return d >= 0 && d <= 7
      })
    }
    if (group) list = list.filter((t) => t.group === group)
    if (robot === 'none') list = list.filter((t) => !t.robot)
    else if (robot) list = list.filter((t) => t.robot === robot)
    if (priority) list = list.filter((t) => t.priority === priority)
    if (owner) list = list.filter((t) => t.ownerName === owner)
    if (query.trim()) {
      const q = query.trim().toLowerCase()
      list = list.filter((t) =>
        [t.id, t.title, t.ownerName, t.latestUpdate, t.group, t.robot]
          .filter(Boolean)
          .some((v) => String(v).toLowerCase().includes(q))
      )
    }
    if (sort === 'id') list.sort((a, b) => a.id.localeCompare(b.id))
    if (sort === 'due')
      list.sort((a, b) => (a.dueDate || '9999').localeCompare(b.dueDate || '9999'))
    if (sort === 'update')
      list.sort(
        (a, b) =>
          (b.latestUpdateTime || '').localeCompare(a.latestUpdateTime || '') || (b.id > a.id ? 1 : -1)
      )
    if (sort === 'priority')
      list.sort(
        (a, b) =>
          (b.overdue ? 1 : 0) - (a.overdue ? 1 : 0) ||
          PRIORITY_ORDER[a.priority] - PRIORITY_ORDER[b.priority] ||
          (b.daysSinceUpdate ?? 0) - (a.daysSinceUpdate ?? 0)
      )
    return list
  }, [tasks, quick, group, robot, priority, owner, query, sort])

  const selectField =
    'bg-base-800 border border-base-600 rounded px-2 py-1.5 text-[11px] text-gray-300 outline-none focus:border-accent-dim'

  return (
    <div className="p-5 space-y-3 max-w-[1400px]">
      <div className="flex items-center justify-between flex-wrap gap-2">
        <h1 className="text-lg font-bold tracking-[0.15em] text-gray-100">任务中心</h1>
        <span className="num-mono text-[11px] text-base-300">{filtered.length} 条</span>
      </div>

      <div className="panel p-2.5 space-y-2.5">
        <div className="flex items-center gap-2 flex-wrap">
          <div className="flex items-center gap-1.5 flex-1 min-w-[220px]">
            <Search size={13} className="text-base-400" />
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="搜索 任务名 / 编号 / 负责人 / 进展 / 组别 / 兵种"
              className="flex-1 bg-transparent outline-none text-[12px] text-gray-200 placeholder:text-base-400"
            />
          </div>
          <div className="flex items-center gap-1">
            {([
              ['card', LayoutGrid],
              ['list', List],
              ['table', Rows3]
            ] as [ViewMode, typeof LayoutGrid][]).map(([v, Icon]) => (
              <button
                key={v}
                onClick={() => setView(v)}
                className={`p-1.5 rounded border ${
                  view === v
                    ? 'bg-accent-faint text-accent-bright border-accent-dim'
                    : 'border-base-600 text-base-400 hover:text-gray-200'
                }`}
              >
                <Icon size={13} />
              </button>
            ))}
          </div>
        </div>

        <div className="flex items-center gap-1.5 flex-wrap">
          {QUICK.map(({ key, label }) => (
            <button
              key={key}
              onClick={() => setQuick(key)}
              className={`px-2.5 py-1 rounded text-[11px] border ${
                quick === key
                  ? 'bg-accent-faint text-accent-bright border-accent-dim'
                  : 'border-base-600 text-base-300 hover:text-gray-200'
              }`}
            >
              {label}
            </button>
          ))}
        </div>

        <div className="flex items-center gap-2 flex-wrap">
          <select value={group} onChange={(e) => setGroup(e.target.value as Group | '')} className={selectField}>
            <option value="">全部组别</option>
            {GROUPS.map((g) => (
              <option key={g} value={g}>
                {g}
              </option>
            ))}
          </select>
          <select value={robot} onChange={(e) => setRobot(e.target.value as Robot | 'none' | '')} className={selectField}>
            <option value="">全部兵种</option>
            {ROBOTS.map((r) => (
              <option key={r} value={r}>
                {r}
              </option>
            ))}
            <option value="none">未指定</option>
          </select>
          <select value={priority} onChange={(e) => setPriority(e.target.value as Priority | '')} className={selectField}>
            <option value="">全部重要程度</option>
            <option value="important_urgent">重要紧急</option>
            <option value="important">重要</option>
            <option value="normal">一般</option>
          </select>
          <select value={owner} onChange={(e) => setOwner(e.target.value)} className={selectField}>
            <option value="">全部负责人</option>
            {owners.map((o) => (
              <option key={o} value={o}>
                {o}
              </option>
            ))}
          </select>
          <select value={sort} onChange={(e) => setSort(e.target.value as SortKey)} className={selectField}>
            <option value="priority">排序：优先级</option>
            <option value="due">排序：截止日期</option>
            <option value="update">排序：最近更新</option>
            <option value="id">排序：编号</option>
          </select>
        </div>
      </div>

      {view === 'card' && (
        <div className="grid grid-cols-1 md:grid-cols-2 2xl:grid-cols-3 gap-3">
          {filtered.map((t) => (
            <TaskCard key={t.id} task={t} onOpen={setSelected} />
          ))}
        </div>
      )}

      {view === 'list' && (
        <div className="panel divide-y divide-base-700">
          {filtered.map((t) => (
            <button
              key={t.id}
              onClick={() => setSelected(t)}
              className="w-full text-left flex items-center gap-2.5 px-3 py-2 hover:bg-base-800 clickable"
            >
              <span className="num-mono text-[11px] text-accent-bright w-16 shrink-0">{t.id}</span>
              <span className="flex-1 text-[12px] text-gray-200 truncate">{t.title}</span>
              <GroupBadge group={t.group} />
              <RobotBadge robot={t.robot} />
              <PriorityBadge priority={t.priority} />
              {t.overdue && <OverdueBadge days={t.overdueDays} />}
              <span className="num-mono text-[11px] text-base-300 w-10 text-right shrink-0">
                {t.dueDate ? fmtDate(t.dueDate) : '--'}
              </span>
            </button>
          ))}
        </div>
      )}

      {view === 'table' && (
        <div className="panel overflow-x-auto">
          <table className="w-full text-[12px]">
            <thead>
              <tr className="border-b border-base-600 text-left">
                {['编号', '任务', '组别', '兵种', '负责人', '重要程度', '状态', '截止', '最近更新'].map(
                  (h) => (
                    <th key={h} className="px-3 py-2 text-[10px] tracking-[0.15em] text-base-300 font-semibold">
                      {h}
                    </th>
                  )
                )}
              </tr>
            </thead>
            <tbody className="divide-y divide-base-700">
              {filtered.map((t) => (
                <tr key={t.id} onClick={() => setSelected(t)} className="hover:bg-base-800 cursor-pointer">
                  <td className="px-3 py-2 num-mono text-accent-bright">{t.id}</td>
                  <td className="px-3 py-2 text-gray-200 max-w-[340px]">
                    <span className="line-clamp-1">{t.title}</span>
                  </td>
                  <td className="px-3 py-2 text-base-300">{t.group ?? '—'}</td>
                  <td className="px-3 py-2 text-base-300">{t.robot ?? '—'}</td>
                  <td className="px-3 py-2">
                    <span className="flex items-center gap-1.5 text-gray-300">
                      <Avatar name={t.ownerName} url={t.ownerAvatarUrl} size={16} />
                      {t.ownerName || '—'}
                    </span>
                  </td>
                  <td className="px-3 py-2 text-base-300">
                    {t.priority ? PRIORITY_LABEL[t.priority] : '—'}
                  </td>
                  <td className="px-3 py-2">
                    <span className="flex items-center gap-1">
                      {t.blocked && <BlockedBadge />}
                      {t.overdue && <OverdueBadge days={t.overdueDays} />}
                      {!t.overdue && t.daysSinceUpdate !== undefined && t.daysSinceUpdate >= 3 && (
                        <StaleBadge days={t.daysSinceUpdate} />
                      )}
                      {!t.blocked && !t.overdue && (t.daysSinceUpdate ?? 0) < 3 && (
                        <span className="text-base-400">正常</span>
                      )}
                    </span>
                  </td>
                  <td className="px-3 py-2 num-mono text-base-300">
                    {t.dueDate ? fmtDate(t.dueDate) : '--'}
                  </td>
                  <td className="px-3 py-2 num-mono text-base-300 whitespace-nowrap">
                    {t.daysSinceUpdate === undefined ? '--' : fmtAgo(t.daysSinceUpdate)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {filtered.length === 0 && (
        <div className="panel p-8 text-center text-[12px] text-base-400">没有匹配的任务</div>
      )}

      <TaskDrawer task={selected} onClose={() => setSelected(null)} />
    </div>
  )
}
