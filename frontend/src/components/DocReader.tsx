import { useEffect, useState, useMemo } from 'react'
import { BookOpen, FileText, X, Loader2, RefreshCw, ChevronRight } from 'lucide-react'

interface DocFile {
  token: string
  name: string
  type: string
  url: string
  edited_time: string
}

// 基于日期的伪随机数（同一天返回同一个值）
function seededRandom(seed: number): number {
  const x = Math.sin(seed) * 10000
  return x - Math.floor(x)
}

function getTodaySeed(): number {
  const d = new Date()
  return d.getFullYear() * 10000 + (d.getMonth() + 1) * 100 + d.getDate()
}

export default function DocReader() {
  const [files, setFiles] = useState<DocFile[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [selected, setSelected] = useState<DocFile | null>(null)
  const [content, setContent] = useState('')
  const [contentLoading, setContentLoading] = useState(false)
  const [contentError, setContentError] = useState('')
  const [previewContent, setPreviewContent] = useState('')
  const [previewLoading, setPreviewLoading] = useState(false)
  const [manualIndex, setManualIndex] = useState<number | null>(null)

  // 计算当前显示的文档索引（基于日期随机，或手动选择）
  const currentIndex = useMemo(() => {
    if (files.length === 0) return 0
    if (manualIndex !== null) return manualIndex % files.length
    const seed = getTodaySeed()
    return Math.floor(seededRandom(seed) * files.length)
  }, [files.length, manualIndex])

  const currentDoc = files[currentIndex] || null

  // 加载文档列表
  useEffect(() => {
    let cancelled = false
    async function load() {
      setLoading(true)
      setError('')
      try {
        const res = await fetch('/api/docs/list')
        const data = await res.json()
        if (!cancelled) {
          setFiles(data.files || [])
          if (data.error) setError(data.error)
        }
      } catch (e) {
        if (!cancelled) setError(String(e))
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    load()
    return () => { cancelled = true }
  }, [])

  // 加载当前文档的预览内容
  useEffect(() => {
    if (!currentDoc) return
    let cancelled = false
    setPreviewLoading(true)
    setPreviewContent('')
    fetch(`/api/docs/content?doc_id=${encodeURIComponent(currentDoc.token)}&type=${currentDoc.type}`)
      .then(r => r.json())
      .then(data => {
        if (!cancelled) {
          if (data.error) {
            setPreviewContent('')
          } else {
            setPreviewContent(data.content || '')
          }
        }
      })
      .catch(() => { if (!cancelled) setPreviewContent('') })
      .finally(() => { if (!cancelled) setPreviewLoading(false) })
    return () => { cancelled = true }
  }, [currentDoc?.token])

  async function openDoc(doc: DocFile) {
    setSelected(doc)
    setContent('')
    setContentError('')
    setContentLoading(true)
    try {
      const res = await fetch(`/api/docs/content?doc_id=${encodeURIComponent(doc.token)}&type=${doc.type}`)
      const data = await res.json()
      if (data.error) {
        setContentError(data.error)
      } else {
        setContent(data.content || '')
      }
    } catch (e) {
      setContentError(String(e))
    } finally {
      setContentLoading(false)
    }
  }

  function shuffleDoc() {
    if (files.length <= 1) return
    let next = Math.floor(Math.random() * files.length)
    if (next === currentIndex) next = (next + 1) % files.length
    setManualIndex(next)
  }

  // 预览内容取前600字
  const previewText = previewContent.slice(0, 600)
  const hasMore = previewContent.length > 600

  return (
    <div className="panel flex flex-col overflow-hidden" style={{ minHeight: 280 }}>
      <div className="flex items-center gap-2 px-3 py-2 border-b border-base-600">
        <BookOpen size={14} className="text-accent-bright" />
        <span className="text-[12px] font-bold tracking-[0.1em] text-gray-100">今日历史文档</span>
        <span className="text-[10px] text-base-400 num-mono">共 {files.length} 份</span>
        <button
          onClick={shuffleDoc}
          disabled={files.length <= 1}
          className="ml-auto flex items-center gap-1 px-2 py-0.5 rounded text-[10px] text-base-300 hover:text-gray-100 hover:bg-base-700 transition-colors clickable disabled:opacity-30"
          title="换一篇"
        >
          <RefreshCw size={11} />
          换一篇
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-3">
        {loading && (
          <div className="flex items-center justify-center py-8 text-[11px] text-base-400">
            <Loader2 size={14} className="animate-spin mr-2" />
            加载中...
          </div>
        )}
        {!loading && error && (
          <div className="px-2 py-4 text-[11px] text-red-400">{error}</div>
        )}
        {!loading && !error && !currentDoc && (
          <div className="px-2 py-4 text-[11px] text-base-400">暂无文档</div>
        )}
        {!loading && !error && currentDoc && (
          <div className="flex flex-col h-full">
            {/* 文档标题 */}
            <div className="flex items-start gap-2 mb-2">
              <FileText size={14} className="text-accent-bright shrink-0 mt-0.5" />
              <span className="flex-1 text-[13px] font-bold text-gray-100 leading-snug">{currentDoc.name}</span>
            </div>

            {/* 预览内容 */}
            <div className="flex-1 min-h-0">
              {previewLoading && (
                <div className="flex items-center justify-center py-6 text-[11px] text-base-400">
                  <Loader2 size={12} className="animate-spin mr-2" />
                  加载文档内容...
                </div>
              )}
              {!previewLoading && previewText && (
                <p className="text-[11px] text-gray-300 leading-relaxed whitespace-pre-wrap">
                  {previewText}
                  {hasMore && <span className="text-base-400">...</span>}
                </p>
              )}
              {!previewLoading && !previewText && (
                <p className="text-[11px] text-base-400">暂无预览内容</p>
              )}
            </div>

            {/* 查看全文按钮 */}
            <button
              onClick={() => openDoc(currentDoc)}
              className="mt-2 flex items-center justify-center gap-1 px-3 py-1.5 rounded bg-accent/20 text-accent-bright text-[11px] font-bold hover:bg-accent/30 transition-colors clickable"
            >
              查看全文
              <ChevronRight size={12} />
            </button>
          </div>
        )}
      </div>

      {/* 文档内容模态框 */}
      {selected && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div className="absolute inset-0 bg-black/60" onClick={() => setSelected(null)} />
          <div className="relative panel w-full max-w-3xl max-h-[80vh] flex flex-col bg-base-900 border border-base-600 rounded-lg shadow-2xl">
            <div className="flex items-center gap-2 px-4 py-3 border-b border-base-600">
              <FileText size={16} className="text-accent-bright shrink-0" />
              <span className="flex-1 text-[13px] font-bold text-gray-100 truncate">{selected.name}</span>
              <button
                onClick={() => setSelected(null)}
                className="p-1 rounded text-base-300 hover:text-gray-100 hover:bg-base-700 clickable ml-2"
              >
                <X size={16} />
              </button>
            </div>
            <div className="flex-1 overflow-y-auto p-4">
              {contentLoading && (
                <div className="flex items-center justify-center py-12 text-[12px] text-base-400">
                  <Loader2 size={16} className="animate-spin mr-2" />
                  加载文档内容...
                </div>
              )}
              {!contentLoading && contentError && (
                <div className="text-[12px] text-red-400 py-4">加载失败：{contentError}</div>
              )}
              {!contentLoading && !contentError && !content && (
                <div className="text-[12px] text-base-400 py-4">文档内容为空</div>
              )}
              {!contentLoading && !contentError && content && (
                <pre className="text-[12px] text-gray-200 leading-relaxed whitespace-pre-wrap font-sans">{content}</pre>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
