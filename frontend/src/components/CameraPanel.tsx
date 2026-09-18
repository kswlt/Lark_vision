import { useEffect, useRef, useState } from 'react'
import { ScanFace, CheckCircle2, KeyRound } from 'lucide-react'

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

/** 相机实时画面：MJPEG 连续视频流（/api/camera/stream）+ 低频状态/FPS 轮询 + 打卡成功提示
 *
 * 授权：CAMERA_PUBLIC=false 且接口返回 401/403 时，面板内显示轻量授权门
 * （输入 Viewer Token -> POST /api/viewer/session 换取 HttpOnly cookie）。
 * 之后 status / face-latest / MJPEG 流（<img> 子资源）都会自动携带 cookie，
 * 不需要把 token 拼进 URL 或 JS。
 */
export default function CameraPanel() {
  const [status, setStatus] = useState<CamStatus | null>(null)
  const [showOk, setShowOk] = useState(false)
  const [okName, setOkName] = useState('')
  const [fallback, setFallback] = useState(false)
  const [frameTick, setFrameTick] = useState(0)
  const [streamTick, setStreamTick] = useState(0)
  // 轻量授权门状态（仅 CAMERA_PUBLIC=false 且未授权时出现）
  const [authRequired, setAuthRequired] = useState(false)
  const [authError, setAuthError] = useState('')
  const [token, setToken] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const okTimer = useRef<ReturnType<typeof setTimeout> | null>(null)
  // 授权成功后 +1，重新挂载 MJPEG 流并立即重轮询
  const [reloadNonce, setReloadNonce] = useState(0)

  // 一次性时间戳 + streamTick：避免浏览器缓存复用 MJPEG 响应；授权成功后 +1 强制重挂载流
  const streamSrc = `/api/camera/stream?ts=${Date.now()}-${streamTick}`

  // MJPEG 加载失败时回退到 JPEG 轮询（兜底，保证任何浏览器都有画面）
  useEffect(() => {
    if (!fallback) return
    const id = setInterval(() => setFrameTick((t) => t + 1), 500)
    return () => clearInterval(id)
  }, [fallback])

  // 状态 + FPS + 打卡提示：1.5s 低频轮询（与视频流完全独立）
  // 401/403 -> 进入授权门；不中断轮询，授权/公开后可自愈
  useEffect(() => {
    let alive = true
    const poll = async () => {
      try {
        const [stRes, lgRes] = await Promise.all([
          fetch('/api/camera/status', { headers: { Accept: 'application/json' } }),
          fetch('/api/attendance/face-latest', { headers: { Accept: 'application/json' } })
        ])
        if (stRes.status === 401 || stRes.status === 403) {
          if (alive) setAuthRequired(true)
          return
        }
        if (alive) setAuthRequired(false)
        const [st, lg] = await Promise.all([
          stRes.json() as Promise<CamStatus>,
          lgRes.json() as Promise<LatestRecog>
        ])
        if (!alive) return
        setStatus(st)
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
  }, [reloadNonce])

  // 提交 Viewer Token -> 建立 HttpOnly session cookie -> 重载画面
  const submitToken = async () => {
    const t = token.trim()
    if (!t || submitting) return
    setSubmitting(true)
    setAuthError('')
    try {
      const res = await fetch('/api/viewer/session', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token: t })
      })
      const data = (await res.json().catch(() => ({}))) as { message?: string }
      if (!res.ok) {
        setAuthError(data?.message || `授权失败（${res.status}）`)
        return
      }
      // 成功：关授权门、清空输入、重新挂载 MJPEG 流并立即轮询
      setAuthRequired(false)
      setToken('')
      setFallback(false)
      setReloadNonce((v) => v + 1)
    } catch {
      setAuthError('网络错误，请重试')
    } finally {
      setSubmitting(false)
    }
  }

  const connected = status?.connected ?? status?.status === 'online'
  const live = status?.preview_fps ?? 0

  return (
    <div
      className="anim-enter-slow w-full h-full flex flex-col"
      style={{ animationDelay: '60ms' }}
    >
      <div className="panel-title mb-1.5 flex items-center gap-2">
        <ScanFace size={15} className="text-accent" />
        飞书补充打卡
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
      <div className="panel overflow-hidden p-0 flex-1 min-h-[140px]">
        <div className="relative h-full w-full bg-black/5">
          {authRequired ? (
            /* 轻量授权门：仅 CAMERA_PUBLIC=false 且未授权时出现，不改变整体 UI */
            <div className="absolute inset-0 z-10 flex items-center justify-center bg-black/60">
              <div className="px-4 py-3 rounded-lg border border-base-600 bg-base-850 text-center max-w-[280px] w-full mx-4">
                <div className="flex items-center justify-center gap-1.5 text-[12px] text-base-300 mb-2">
                  <KeyRound size={13} className="text-accent" />
                  相机画面需要访问授权
                </div>
                <input
                  type="password"
                  value={token}
                  onChange={(e) => setToken(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') void submitToken()
                  }}
                  placeholder="输入 Viewer Token"
                  autoFocus
                  className="w-full px-2 py-1.5 rounded bg-base-900 border border-base-600 text-[12px] text-gray-100 outline-none focus:border-accent-dim"
                />
                <button
                  onClick={() => void submitToken()}
                  disabled={submitting}
                  className="mt-2 w-full px-3 py-1.5 rounded bg-accent-bright text-white text-[12px] font-bold disabled:opacity-50"
                >
                  {submitting ? '验证中…' : '授权'}
                </button>
                {authError && (
                  <div className="mt-1.5 text-[10px] text-red-400">{authError}</div>
                )}
              </div>
            </div>
          ) : (
            <>
              {/* MJPEG 连续视频流（失败自动回退 JPEG 轮询兜底） */}
              <img
                src={fallback ? `/api/camera/frame?t=${frameTick}` : streamSrc}
                alt="相机画面"
                className="absolute inset-0 h-full w-full object-cover"
                onError={(e) => {
                  ;(e.target as HTMLImageElement).style.opacity = '0.15'
                  setFallback(true)
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
            </>
          )}
        </div>
      </div>
    </div>
  )
}
