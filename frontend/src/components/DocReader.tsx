import { useEffect, useState } from 'react'
import { BookOpen, FileText, FileSpreadsheet, Folder, X, Loader2 } from 'lucide-react'

interface DocFile {
  token: string
  name: string
  type: string
  url: string
  edited_time: string
}

const TYPE_ICON: Record<string, typeof FileText> = {
  docx: FileText,
  doc: FileText,
  sheet: FileSpreadsheet,
  folder: Folder,
  bitable: FileSpreadsheet,
  file: FileText,
  mindnote: FileText,
  slides: FileText,
}

const TYPE_LABEL: Record<string, string> = {
  docx: '文档',
  doc: '文档',
  sheet: '表格',
  folder: '文件夹',
  bitable: '多维表格',
  file: '文件',
  mindnote: '思维笔记',
  slides: '幻灯片',
}

function fmtTime(ts: string): string {
  if (!ts) return ''
  try {
    const n = parseInt(ts, 10)
    if (isNaN(n)) return ts
    const d = new Date(n * 1000)
    return `${d.getMonth() + 1}/${d.getDate()} ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
  } catch {
    return ''
  }
}

export default function DocReader() {
  const [files, setFiles] = useState<DocFile[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [selected, setSelected] = useState<DocFile | null>(null)
  const [content, setContent] = useState('')
  const [contentLoading, setContentLoading] = useState(false)
  const [contentError, setContentError] = useState('')

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
    return () => {
      cancelled = true
    }
  }, [])

  async function openDoc(doc: DocFile) {
    if (doc.type === 'folder') {
      // 文件夹：暂不支持深入，提示
      return
    }
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

  return (
    <div className="panel flex flex-col overflow-hidden" style={{ minHeight: 200 }}>
      <div className="flex items-center gap-2 px-3 py-2 border-b border-base-600">
        <BookOpen size={14} className="text-accent-bright" />
        <span className="text-[12px] font-bold tracking-[0.1em] text-gray-100">今日历史文档</span>
        <span className="ml-auto text-[10px] text-base-400 num-mono">{files.length} 份</span>
      </div>

      <div className="flex-1 overflow-y-auto">
        {loading && (
          <div className="flex items-center justify-center py-8 text-[11px] text-base-400">
            <Loader2 size={14} className="animate-spin mr-2" />
            加载中...
          </div>
        )}
        {!loading && error && (
          <div className="px-3 py-4 text-[11px] text-red-400">{error}</div>
        )}
        {!loading && !error && files.length === 0 && (
          <div className="px-3 py-4 text-[11px] text-base-400">暂无文档</div>
        )}
        {!loading && !error && files.map((f) => {
          const Icon = TYPE_ICON[f.type] || FileText
          return (
            <button
              key={f.token}
              onClick={() => openDoc(f)}
              className="w-full flex items-center gap-2 px-3 py-2 hover:bg-base-800 transition-colors text-left border-b border-base-700/50 clickable"
            >
              <Icon size={13} className="text-accent-bright shrink-0" />
              <span className="flex-1 min-w-0 text-[11px] text-gray-200 truncate">{f.name}</span>
              <span className="text-[9px] text-base-400 shrink-0 num-mono">{TYPE_LABEL[f.type] || f.type}</span>
            </button>
          )
        })}
      </div>

      {/* 文档内容模态框 */}
      {selected && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div className="absolute inset-0 bg-black/60" onClick={() => setSelected(null)} />
          <div className="relative panel w-full max-w-3xl max-h-[80vh] flex flex-col bg-base-900 border border-base-600 rounded-lg shadow-2xl">
            <div className="flex items-center gap-2 px-4 py-3 border-b border-base-600">
              <FileText size={16} className="text-accent-bright shrink-0" />
              <span className="flex-1 text-[13px] font-bold text-gray-100 truncate">{selected.name}</span>
              <span className="text-[10px] text-base-400 num-mono">{TYPE_LABEL[selected.type] || selected.type}</span>
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
