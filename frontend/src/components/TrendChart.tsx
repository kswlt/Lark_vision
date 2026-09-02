import { TrendingUp } from 'lucide-react'
import {
  ResponsiveContainer,
  ComposedChart,
  Area,
  Line,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid
} from 'recharts'
import type { TrendPoint } from '../types'

interface TrendChartProps {
  data: TrendPoint[]
}

/** 任务完成趋势：近 14 天 当日完成(柱) + 累计完成(线/面积) */
export default function TrendChart({ data }: TrendChartProps) {
  if (!data || data.length === 0) return null
  return (
    <div className="panel hud-frame flex flex-col anim-enter-slow flex-1 min-h-0">
      <div className="flex items-center gap-1.5 px-4 pt-2.5 pb-1 shrink-0">
        <TrendingUp size={13} className="text-accent-bright" />
        <span className="panel-title">任务完成趋势</span>
        <span className="ml-auto text-[9px] text-base-400">近 14 天 · 完成</span>
      </div>
      <div className="flex-1 min-h-0 px-2 pb-2">
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={data} margin={{ top: 6, right: 6, bottom: 0, left: -18 }}>
            <CartesianGrid stroke="#dbe1e8" strokeDasharray="3 3" vertical={false} />
            <XAxis
              dataKey="date"
              tick={{ fontSize: 9, fill: '#6b7682' }}
              tickLine={false}
              axisLine={{ stroke: '#c7cfd8' }}
              interval={1}
            />
            <YAxis
              allowDecimals={false}
              tick={{ fontSize: 9, fill: '#6b7682' }}
              tickLine={false}
              axisLine={false}
              width={24}
            />
            <Tooltip
              cursor={{ fill: 'rgba(23,143,143,0.06)' }}
              contentStyle={{
                background: '#fff',
                border: '1px solid #dbe1e8',
                borderRadius: 6,
                fontSize: 11,
                color: '#2b343d'
              }}
              labelStyle={{ color: '#6b7682', fontSize: 10 }}
              formatter={(v, name) => [String(v), name === 'done' ? '当日完成' : '累计完成']}
            />
            <Bar dataKey="done" fill="#8fd3d3" radius={[2, 2, 0, 0]} barSize={8} />
            <Line
              type="monotone"
              dataKey="cum"
              stroke="#0c7e7e"
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 3 }}
            />
            <Area
              type="monotone"
              dataKey="cum"
              stroke="none"
              fill="#178f8f"
              fillOpacity={0.08}
            />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
