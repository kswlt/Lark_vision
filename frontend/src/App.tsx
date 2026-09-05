import { useEffect, useState } from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import TopBar from './components/TopBar'
import Dashboard from './pages/Dashboard'
import Tasks from './pages/Tasks'
import Groups from './pages/Groups'
import Robots from './pages/Robots'
import People from './pages/People'

/** 显示缩放档位 */
export const SCALES = [1, 1.15, 1.3, 1.5, 1.7]
export const DEFAULT_SCALE = 1.3
const LS_KEY = 'rm_scale_v2'

function readScale(): number {
  try {
    const v = localStorage.getItem(LS_KEY)
    const n = v ? Number(v) : NaN
    if (!Number.isNaN(n) && SCALES.includes(n)) return n
  } catch {
    /* ignore */
  }
  return DEFAULT_SCALE
}

export default function App() {
  const [scale, setScale] = useState<number>(readScale)
  const [shift, setShift] = useState({ x: 0, y: 0 })

  useEffect(() => {
    // 全局缩放（Chromium 支持 html.zoom，等效浏览器缩放）
    document.documentElement.style.zoom = String(scale)
    try {
      localStorage.setItem(LS_KEY, String(scale))
    } catch {
      /* ignore */
    }
  }, [scale])

  // 像素偏移防烧屏：每隔3分钟整个页面随机偏移1-2px，肉眼不可察觉但避免固定像素老化
  useEffect(() => {
    const id = setInterval(() => {
      setShift({
        x: Math.floor(Math.random() * 3) - 1, // -1, 0, 1
        y: Math.floor(Math.random() * 3) - 1,
      })
    }, 3 * 60 * 1000) // 3分钟
    return () => clearInterval(id)
  }, [])

  const step = (dir: 1 | -1) => {
    const i = SCALES.indexOf(scale)
    const j = Math.max(0, Math.min(SCALES.length - 1, i + dir))
    setScale(SCALES[j])
  }

  return (
    <div
      className="flex flex-col h-screen overflow-hidden"
      style={{ transform: `translate(${shift.x}px, ${shift.y}px)` }}
    >
      <TopBar scale={scale} onScaleUp={() => step(1)} onScaleDown={() => step(-1)} />
      <main className="flex-1 overflow-y-auto">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/tasks" element={<Tasks />} />
          <Route path="/groups" element={<Groups />} />
          <Route path="/robots" element={<Robots />} />
          <Route path="/people" element={<People />} />
          <Route path="*" element={<Navigate to="/dashboard" replace />} />
        </Routes>
      </main>
    </div>
  )
}
