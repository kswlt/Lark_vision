import { useNavigate } from 'react-router-dom'
import type { Group, MatrixRow, Robot } from '../types'
import { GROUPS, ROBOTS } from '../config/constants'

interface MatrixTableProps {
  matrix: MatrixRow[]
}

const rowOrder = [...ROBOTS, null]

export default function MatrixTable({ matrix }: MatrixTableProps) {
  const nav = useNavigate()
  if (!matrix || matrix.length === 0) return null

  const rows = rowOrder
    .map((r) => matrix.find((m) => (m.robot ?? null) === r))
    .filter(Boolean) as MatrixRow[]

  return (
    <div className="panel hud-frame overflow-x-auto">
      <table className="w-full text-center text-[12px]">
        <thead>
          <tr className="border-b border-base-600">
            <th className="py-2.5 px-3 text-left text-[10px] tracking-[0.2em] text-base-300 font-semibold">
              兵种
            </th>
            {GROUPS.map((g) => (
              <th key={g} className="py-2.5 px-3 text-[10px] tracking-[0.2em] text-base-300 font-semibold">
                {g}
              </th>
            ))}
            <th className="py-2.5 px-3 text-[10px] tracking-[0.2em] text-base-300 font-semibold">
              合计
            </th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row, ri) => {
            const total = GROUPS.reduce((s, g) => s + (row.cells[g]?.total ?? 0), 0)
            const isNull = row.robot === null
            return (
              <tr
                key={row.robot ?? 'none'}
                className={`border-b border-base-700 last:border-0 anim-enter ${
                  isNull ? 'opacity-60' : ''
                }`}
                style={{ animationDelay: `${ri * 40}ms` }}
              >
                <td className="py-2 px-3 text-left font-medium text-gray-300">
                  {row.robot ?? '未指定'}
                </td>
                {GROUPS.map((g: Group) => {
                  const cell = row.cells[g] ?? { total: 0, overdue: 0 }
                  if (cell.total === 0) {
                    return (
                      <td key={g} className="py-2 px-3 text-base-500">
                        —
                      </td>
                    )
                  }
                  return (
                    <td key={g} className="py-2 px-3">
                      <button
                        onClick={() =>
                          nav(
                            `/tasks?robot=${row.robot ?? 'none'}&group=${g}`
                          )
                        }
                        className="inline-flex items-center gap-1.5 px-2 py-1 rounded hover:bg-accent-faint text-gray-200 clickable matrix-cell"
                      >
                        <span className="num-mono font-semibold">{cell.total}</span>
                        {cell.overdue > 0 && (
                          <span className="num-mono text-[10px] text-red-400">+{cell.overdue}</span>
                        )}
                      </button>
                    </td>
                  )
                })}
                <td className="py-2 px-3 num-mono text-base-300 font-medium">{total}</td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
