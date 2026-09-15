import { afterEach, describe, expect, it, vi } from 'vitest'
import { ApiError, api, DEFAULT_TIMEOUT_MS, get } from './client'

function mockFetchOnce(status: number, body: unknown) {
  return vi.fn().mockResolvedValue(
    new Response(JSON.stringify(body), {
      status,
      headers: { 'Content-Type': 'application/json' }
    })
  )
}

afterEach(() => {
  vi.restoreAllMocks()
  vi.useRealTimers()
})

describe('api client', () => {
  it('成功请求返回 JSON', async () => {
    vi.stubGlobal('fetch', mockFetchOnce(200, { ok: true }))
    const data = await api.health()
    expect(data).toEqual({ ok: true })
  })

  it('HTTP 错误抛出 ApiError 并带状态码', async () => {
    vi.stubGlobal('fetch', mockFetchOnce(500, {}))
    await expect(api.health()).rejects.toMatchObject({
      name: 'ApiError',
      status: 500
    })
  })

  it('请求超时抛出 ApiError(status=0)', async () => {
    const fetchMock = vi.fn((_url: string, init?: RequestInit) => {
      return new Promise<Response>((_resolve, reject) => {
        init?.signal?.addEventListener('abort', () => {
          reject(new DOMException('Aborted', 'AbortError'))
        })
      })
    })
    vi.stubGlobal('fetch', fetchMock)
    const p = get('/api/health', { timeoutMs: 100 })
    // 立即挂上 handler，避免 rejection 被当作 unhandled
    const settled = p.catch((e: unknown) => e)
    // 等待真实超时触发（100ms timeout + 余量）
    await new Promise((r) => setTimeout(r, 300))
    await expect(settled).resolves.toMatchObject({ name: 'ApiError', status: 0 })
  })

  it('网络错误抛出 ApiError(status=0)', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('Failed to fetch')))
    await expect(api.tasks()).rejects.toMatchObject({ name: 'ApiError', status: 0 })
  })

  it('默认超时时间为 15s', () => {
    expect(DEFAULT_TIMEOUT_MS).toBe(15_000)
  })
})
