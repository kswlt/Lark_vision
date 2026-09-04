import { useEffect, useRef, useState } from 'react'
import { ScanFace, CheckCircle2 } from 'lucide-react'

interface LatestRecog {
  name?: string | null
  time?: string | null
  status?: string | null
}

interface CamStatus {
  status?: string
  connected?: boolean
  frameTime?: string | null
  capture_fps?: number
  preview_fps?: number
  recognition_fps?: number
  frame_age_ms?: number | null
}

/** 相机实时画面：MJPEG 连续视频流（/api/camera/stream）+ 低频状态/FPS 轮询 + 打卡成功提示 */
export default function CameraPanel() {
  const [status, setStatus] = useState<CamStatus | null>(null)
  const [showOk, setShowOk] = useState(false)
  const [okName, setOkName] = useState('')
  const okTimer = useRef<ReturnType<typeof setTimeout> | null>(null)

  // 状态 + FPS + 打卡提示：1.5s 低频轮询（与视频流完全独立）
  useEffect(() => {
    let alive = true
    const poll = async () => {
      try {
        const [st, lg] = await Promise.all([
          fetch('/api/camera/status', { headers: { Accept: 'application/json' } }).then((r) => r.json()),
          fetch('/api/attendance/face-latest', { headers: { Accept: 'application/json' } }).then((r) => r.json())
        ])
        if (!alive) return
        setStatus(st as CamStatus)
        if (lg?.status === 'checked' && lg.name) {
          setOkName(lg.name)
          setShowOk(true)
          if (okTimer.current) clearTimeout(okTimer.current)
          okTimer.current = setTimeout(() => setShowOk(false), 6000)
        }
      } catch {
        /* 忽略瞬时错误 */
      }
    }
    poll()
    const id = setInterval(poll, 1500)
    return () => {
      alive = false
      clearInterval(id)
    }
  }, [])

  const connected = status?.connected ?? status?.status === 'online'
  const live = status?.preview_fps ?? 0

  return (
    <div
      className="anim-enter-slow w-full h-full flex flex-col"
      style={{ animationDelay: '60ms' }}
    >
      <div className="panel-title mb-1.5 flex items-center gap-2">
        <ScanFace size={15} className="text-accent" />
        人脸识别打卡
        <span className="ml-auto flex items-center gap-2 text-[11px]">
          {live > 0 && (
            <span className="num-mono text-base-300">
              {live.toFixed(0)} <span className="text-base-400">FPS</span>
            </span>
          )}
          <span className="flex items-center gap-1.5">
            <span
              className={`inline-block h-2 w-2 rounded-full ${
                connected ? 'bg-green-500' : 'bg-base-400'
              }`}
            />
            {connected ? (status?.frameTime ?? '') : '相机未连接'}
          </span>
        </span>
      </div>
      <div className="panel overflow-hidden p-0 flex-1 min-h-[150px]">
        <div className="relative h-full w-full bg-black/5">
          {/* MJPEG 连续视频流：浏览器自动持续解析 */}
          <img
            src="/api/camera/stream"
            alt="相机画面"
            className="absolute inset-0 h-full w-full object-cover"
            onError={(e) => {
              ;(e.target as HTMLImageElement).style.opacity = '0.15'
            }}
            onLoad={(e) => {
              ;(e.target as HTMLImageElement).style.opacity = '1'
            }}
          />
          {!connected && (
            <div className="absolute inset-0 flex items-center justify-center text-[12px] text-base-300">
              等待相机画面…
            </div>
          )}
          {showOk && (
            <div className="absolute inset-x-0 top-0 z-10 flex items-center justify-center gap-1.5 bg-green-600/90 px-3 py-1.5 shadow-lg tick-pop">
              <CheckCircle2 size={15} className="text-white shrink-0" />
              <span className="text-[13px] font-black text-white">打卡成功 · {okName}</span>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
