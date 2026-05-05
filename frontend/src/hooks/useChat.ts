import { useState, useCallback } from 'react'
import { chat } from '../api/client'

interface Message {
  role: 'user' | 'assistant'
  content: string
  intent?: string
}

export function useChat() {
  const [messages, setMessages] = useState<Message[]>([
    {
      role: 'assistant',
      content: '👋 你好！我是 LLM-ERP 助手。你可以問我：\n\n• 「庫存還有多少 M6 螺絲？」\n• 「幫我向大明螺絲買 500 顆 M6」\n• 「A 產品用哪些料？」\n• 「A 產品要做 100 台，料夠不夠？」',
    },
  ])
  const [loading, setLoading] = useState(false)
  const [sessionId, setSessionId] = useState<string>()

  const sendMessage = useCallback(async (content: string) => {
    if (!content.trim() || loading) return

    const userMsg: Message = { role: 'user', content }
    setMessages(prev => [...prev, userMsg])
    setLoading(true)

    try {
      const result = await chat(content, sessionId)
      const assistantMsg: Message = {
        role: 'assistant',
        content: result.reply || '處理完成',
        intent: result.intent,
      }
      setMessages(prev => [...prev, assistantMsg])
      if (result.session_id) {
        setSessionId(result.session_id)
      }
    } catch (err: any) {
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: `❌ 錯誤：${err.message || '連線失敗'}`,
      }])
    } finally {
      setLoading(false)
    }
  }, [loading, sessionId])

  const clearMessages = useCallback(() => {
    setMessages([
      {
        role: 'assistant',
        content: '👋 對話已重置。有什麼我可以幫你的？',
      },
    ])
    setSessionId(undefined)
  }, [])

  return { messages, loading, sendMessage, clearMessages }
}
