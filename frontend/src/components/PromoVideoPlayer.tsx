import { useState, useEffect, useRef, useCallback } from 'react'

interface PromoVideoPlayerProps {
  onClose: () => void
}

// 宣传片列表（与后端public/promo_videos目录对应）
// 只保留1080p H.264编码的视频，确保Intel HD 630核显能流畅硬件解码
const PROMO_VIDEOS = [
  {
    title: '灯光秀 - RMUC 2025 全国总决赛',
    src: '/promo_videos/灯光秀 - RMUC 2025 全国总决赛.mp4',
  },
  {
    title: '《你，在为什么而努力》',
    src: '/promo_videos/《你，在为什么而努力》.mp4',
  },
  {
    title: '《金色十年》RMU 2025 纪录片（先导片）',
    src: '/promo_videos/《金色十年》RMU 2025 纪录片（先导片）.mp4',
  },
  {
    title: '交响乐表演 - RMUC 2025 全国总决赛',
    src: '/promo_videos/交响乐表演 - RMUC 2025 全国总决赛.mp4',
  },
  {
    title: '《下一场，去大疆》RM专属招聘通道品牌视频',
    src: '/promo_videos/《下一场，去大疆》RM专属招聘通道品牌视频.mp4',
  },
  {
    title: '预热视频 - RMUC 2025 全国总决赛',
    src: '/promo_videos/预热视频 _ RMUC 2025 全国总决赛.mp4',
  },
  {
    title: '《理想握在手中》',
    src: '/promo_videos/《理想握在手中》.mp4',
  },
]

export default function PromoVideoPlayer({ onClose }: PromoVideoPlayerProps) {
  const [currentIndex, setCurrentIndex] = useState(0)
  const [showControls, setShowControls] = useState(true)
  const [isPlaying, setIsPlaying] = useState(false)
  const [autoPlayFailed, setAutoPlayFailed] = useState(false)
  const videoRef = useRef<HTMLVideoElement>(null)
  const controlsTimeoutRef = useRef<number | null>(null)

  const currentVideo = PROMO_VIDEOS[currentIndex]

  // 播放下一个视频
  const playNext = useCallback(() => {
    setCurrentIndex((prev) => (prev + 1) % PROMO_VIDEOS.length)
  }, [])

  // 视频结束自动播放下一个
  const handleVideoEnd = useCallback(() => {
    playNext()
  }, [playNext])

  // 双击退出全屏
  const handleDoubleClick = useCallback(() => {
    onClose()
  }, [onClose])

  // 单击显示/隐藏控制栏
  const handleClick = useCallback(() => {
    setShowControls((prev) => !prev)
    // 3秒后自动隐藏控制栏
    if (controlsTimeoutRef.current) {
      clearTimeout(controlsTimeoutRef.current)
    }
    controlsTimeoutRef.current = window.setTimeout(() => {
      setShowControls(false)
    }, 3000)
  }, [])

  // 临时取消全局缩放，确保视频真正全屏
  useEffect(() => {
    const root = document.documentElement
    const originalZoom = root.style.zoom
    root.style.zoom = '1'
    return () => {
      root.style.zoom = originalZoom
    }
  }, [])

  // 键盘快捷键
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose()
      } else if (e.key === 'ArrowRight') {
        playNext()
      } else if (e.key === ' ') {
        e.preventDefault()
        if (videoRef.current) {
          if (videoRef.current.paused) {
            playVideo()
          } else {
            videoRef.current.pause()
          }
        }
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [onClose, playNext])

  // 播放视频（带声音）
  const playVideo = useCallback(() => {
    if (videoRef.current) {
      videoRef.current.play().then(() => {
        setIsPlaying(true)
        setAutoPlayFailed(false)
      }).catch(() => {
        setAutoPlayFailed(true)
        setIsPlaying(false)
      })
    }
  }, [])

  // 切换视频后自动播放（带声音，因为是用户点击按钮触发的）
  useEffect(() => {
    if (videoRef.current) {
      videoRef.current.load()
      // 延迟一点播放，确保视频已加载
      setTimeout(() => {
        playVideo()
      }, 100)
    }
  }, [currentIndex, playVideo])

  // 视频播放/暂停事件
  const handlePlay = useCallback(() => {
    setIsPlaying(true)
    setAutoPlayFailed(false)
  }, [])

  const handlePause = useCallback(() => {
    setIsPlaying(false)
  }, [])

  // 初始显示控制栏，3秒后隐藏
  useEffect(() => {
    controlsTimeoutRef.current = window.setTimeout(() => {
      setShowControls(false)
    }, 3000)
    return () => {
      if (controlsTimeoutRef.current) {
        clearTimeout(controlsTimeoutRef.current)
      }
    }
  }, [])

  return (
    <div
      className="fixed inset-0 z-[9999] bg-black cursor-pointer overflow-hidden"
      style={{ margin: 0, padding: 0 }}
      onDoubleClick={handleDoubleClick}
      onClick={handleClick}
    >
      {/* 视频 - 绝对定位填满整个屏幕，object-contain保持宽高比居中 */}
      <video
        ref={videoRef}
        style={{
          position: 'absolute',
          top: 0,
          left: 0,
          width: '100%',
          height: '100%',
          objectFit: 'contain',
          display: 'block',
          margin: 0,
          padding: 0,
        }}
        src={currentVideo.src}
        onEnded={handleVideoEnd}
        onPlay={handlePlay}
        onPause={handlePause}
        autoPlay
        loop={false}
        playsInline
      />

      {/* 自动播放失败时显示中央播放按钮 */}
      {(autoPlayFailed || !isPlaying) && (
        <div
          className="absolute inset-0 flex items-center justify-center cursor-pointer"
          onClick={(e) => {
            e.stopPropagation()
            playVideo()
          }}
        >
          <div className="w-24 h-24 rounded-full bg-white/20 backdrop-blur-sm flex items-center justify-center border-2 border-white/40 hover:bg-white/30 transition-all">
            <svg className="w-12 h-12 text-white ml-1" fill="currentColor" viewBox="0 0 24 24">
              <path d="M8 5v14l11-7z" />
            </svg>
          </div>
          <div className="absolute bottom-40 text-white/80 text-lg">
            点击播放（带声音）
          </div>
        </div>
      )}

      {/* 控制栏 */}
      <div
        className={`absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/80 to-transparent p-6 transition-opacity duration-300 ${
          showControls ? 'opacity-100' : 'opacity-0 pointer-events-none'
        }`}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between text-white">
          {/* 当前视频标题 */}
          <div className="flex-1">
            <div className="text-lg font-medium">{currentVideo.title}</div>
            <div className="text-sm text-gray-300 mt-1">
              {currentIndex + 1} / {PROMO_VIDEOS.length} · 循环播放中
            </div>
          </div>

          {/* 控制按钮 */}
          <div className="flex items-center gap-3">
            <button
              onClick={() => setCurrentIndex((prev) => (prev - 1 + PROMO_VIDEOS.length) % PROMO_VIDEOS.length)}
              className="px-4 py-2 rounded bg-white/10 hover:bg-white/20 text-sm transition-colors"
            >
              上一个
            </button>
            <button
              onClick={() => {
                if (videoRef.current) {
                  if (videoRef.current.paused) {
                    playVideo()
                  } else {
                    videoRef.current.pause()
                  }
                }
              }}
              className="px-4 py-2 rounded bg-white/10 hover:bg-white/20 text-sm transition-colors"
            >
              {isPlaying ? '暂停' : '播放'}
            </button>
            <button
              onClick={playNext}
              className="px-4 py-2 rounded bg-white/10 hover:bg-white/20 text-sm transition-colors"
            >
              下一个
            </button>
            <button
              onClick={onClose}
              className="px-4 py-2 rounded bg-red-500/80 hover:bg-red-500 text-sm transition-colors"
            >
              退出 (双击)
            </button>
          </div>
        </div>
      </div>

      {/* 顶部提示 */}
      <div
        className={`absolute top-6 left-1/2 -translate-x-1/2 text-white/60 text-sm transition-opacity duration-300 ${
          showControls ? 'opacity-100' : 'opacity-0'
        }`}
      >
        双击屏幕或按 ESC 退出全屏 · 空格键暂停/播放 · 方向键切换
      </div>
    </div>
  )
}
