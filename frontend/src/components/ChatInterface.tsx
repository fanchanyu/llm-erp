import { useState, useRef, useEffect } from 'react'
import { useChat } from '../hooks/useChat'
import { useTranslation } from '../i18n'

interface Props {
  initialPrompt?: string
}

export function ChatInterface({ initialPrompt }: Props) {
  const { messages, loading, sendMessage, clearMessages } = useChat()
  const [input, setInput] = useState('')
  const [lastPrompt, setLastPrompt] = useState('')
  const endRef = useRef<HTMLDivElement>(null)
  const { t } = useTranslation()

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  useEffect(() => {
    if (initialPrompt && initialPrompt !== lastPrompt) {
      setLastPrompt(initialPrompt)
      setInput(initialPrompt)
      const timer = setTimeout(() => {
        sendMessage(initialPrompt)
        setInput('')
      }, 500)
      return () => clearTimeout(timer)
    }
  }, [initialPrompt, lastPrompt, sendMessage])

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (input.trim() && !loading) {
      sendMessage(input)
      setInput('')
    }
  }

  return (
    <div className="flex flex-col h-[calc(100vh-8rem)] bg-gray-900 rounded-2xl shadow-xl border border-gray-800 overflow-hidden">
      <div className="flex items-center justify-between px-5 py-3 border-b border-gray-800 bg-gray-900/50">
        <div className="flex items-center gap-3">
          <div className={`w-2.5 h-2.5 rounded-full ${loading ? 'bg-yellow-400 animate-pulse' : 'bg-green-400'}`} />
          <span className="text-sm font-medium text-gray-300">
            {loading ? t('chat.thinking') : t('chat.connected')}
          </span>
        </div>
        <button
          onClick={clearMessages}
          className="text-xs text-gray-500 hover:text-gray-300 transition-colors px-3 py-1 rounded-lg hover:bg-gray-800"
        >
          {t('chat.clear')}
        </button>
      </div>

      <div className="flex-1 overflow-y-auto px-5 py-5 space-y-4 bg-gray-900/30">
        {messages.map((msg, i) => (
          <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div
              className={`max-w-[85%] rounded-2xl px-5 py-3.5 text-sm leading-relaxed whitespace-pre-wrap ${
                msg.role === 'user'
                  ? 'bg-gradient-to-r from-blue-600 to-blue-500 text-white shadow-lg shadow-blue-600/20'
                  : 'bg-gray-800 text-gray-200 border border-gray-700/50'
              }`}
            >
              {msg.intent === 'no_api_key' && <div className="text-yellow-400 mb-2">⚠️</div>}
              {msg.content}
            </div>
          </div>
        ))}

        {loading && (
          <div className="flex justify-start">
            <div className="bg-gray-800 rounded-2xl px-5 py-4 border border-gray-700/50">
              <div className="flex gap-1.5">
                <div className="w-2 h-2 bg-gray-500 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                <div className="w-2 h-2 bg-gray-500 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                <div className="w-2 h-2 bg-gray-500 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
              </div>
            </div>
          </div>
        )}
        <div ref={endRef} />
      </div>

      <form onSubmit={handleSubmit} className="border-t border-gray-800 px-5 py-4 bg-gray-900/50">
        <div className="flex gap-3">
          <input
            type="text"
            value={input}
            onChange={e => setInput(e.target.value)}
            placeholder={t('chat.placeholder')}
            className="flex-1 px-4 py-3 bg-gray-800 border border-gray-700 rounded-xl text-sm text-gray-200 placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
            disabled={loading}
          />
          <button
            type="submit"
            disabled={loading || !input.trim()}
            className="px-6 py-3 bg-gradient-to-r from-blue-600 to-blue-500 text-white rounded-xl text-sm font-medium hover:from-blue-500 hover:to-blue-400 disabled:opacity-40 disabled:cursor-not-allowed transition-all shadow-lg shadow-blue-600/20"
          >
            {loading ? '...' : t('chat.send')}
          </button>
        </div>
      </form>
    </div>
  )
}
