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

  useEffect(() => {
    // 全局缩放（Chromium 支持 html.zoom，等效浏览器缩放）
    document.documentElement.style.zoom = String(scale)
    try {
      localStorage.setItem(LS_KEY, String(scale))
    } catch {
      /* ignore */
    }
  }, [scale])

  const step = (dir: 1 | -1) => {
    const i = SCALES.indexOf(scale)
    const j = Math.max(0, Math.min(SCALES.length - 1, i + dir))
    setScale(SCALES[j])
  }

  return (
    <div className="flex flex-col h-screen overflow-hidden">
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
