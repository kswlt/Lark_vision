import { useEffect, useState } from 'react'
import { ScanFace } from 'lucide-react'

/** 相机实时画面小窗口：定时轮询 /api/camera/frame */
export default function CameraPanel() {
  const [tick, setTick] = useState(0)
  const [frameTime, setFrameTime] = useState<string | null>(null)

  useEffect(() => {
    const id = setInterval(() => setTick((t) => t + 1), 600)
    return () => clearInterval(id)
  }, [])

  useEffect(() => {
    fetch('/api/camera/status', { headers: { Accept: 'application/json' } })
      .then((r) => r.json())
      .then((d) => setFrameTime(d?.frameTime ?? null))
      .catch(() => setFrameTime(null))
  }, [tick])

  return (
    <div
      className="anim-enter-slow w-full h-full flex flex-col"
      style={{ animationDelay: '60ms' }}
    >
      <div className="panel-title mb-1.5 flex items-center gap-2">
        <ScanFace size={15} className="text-accent" />
        人脸识别打卡
        <span className="ml-auto flex items-center gap-1.5 text-[11px]">
          <span
            className={`inline-block h-2 w-2 rounded-full ${
              frameTime ? 'bg-green-500' : 'bg-base-400'
            }`}
          />
          {frameTime ? `实时 ${frameTime}` : '相机未连接'}
        </span>
      </div>
      <div className="panel overflow-hidden p-0 flex-1 min-h-0">
        <div className="relative h-full w-full bg-black/5">
          <img
            src={`/api/camera/frame?t=${tick}`}
            alt="相机画面"
            className="absolute inset-0 h-full w-full object-cover"
            onError={(e) => {
              ;(e.target as HTMLImageElement).style.opacity = '0.15'
            }}
            onLoad={(e) => {
              ;(e.target as HTMLImageElement).style.opacity = '1'
            }}
          />
          {!frameTime && (
            <div className="absolute inset-0 flex items-center justify-center text-[12px] text-base-300">
              等待相机画面…
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
