import { useEffect, useRef, useState } from 'react'

/** 数字滚动动画：值变化时从旧值缓动到新值 */
export function useCountUp(target: number, duration = 700) {
  const [val, setVal] = useState(0)
  const fromRef = useRef(0)
  const frameRef = useRef<number | null>(null)

  useEffect(() => {
    const from = fromRef.current
    const to = target
    if (from === to) {
      setVal(to)
      return
    }
    const start = performance.now()
    const tick = (now: number) => {
      const p = Math.min(1, (now - start) / duration)
      const eased = 1 - Math.pow(1 - p, 3)
      const v = Math.round(from + (to - from) * eased)
      setVal(v)
      if (p < 1) {
        frameRef.current = requestAnimationFrame(tick)
      } else {
        fromRef.current = to
      }
    }
    frameRef.current = requestAnimationFrame(tick)
    return () => {
      if (frameRef.current !== null) cancelAnimationFrame(frameRef.current)
    }
  }, [target, duration])

  return val
}
