import { useState, useCallback } from 'react'
import { chat } from '../api/client'
import { useTranslation } from '../i18n'

interface Message {
  role: 'user' | 'assistant'
  content: string
  intent?: string
}

export function useChat() {
  const { t, lang } = useTranslation()
  const [messages, setMessages] = useState<Message[]>([
    {
      role: 'assistant',
      content: lang === 'zh'
        ? '👋 你好！我是 LLM-ERP 助手。你可以問我：\n\n• 「庫存還有多少 M6 螺絲？」\n• 「幫我向大明螺絲買 500 顆 M6」\n• 「ASM-001 用哪些料？」\n• 「做 5 台 CNC-001，料夠不夠？」'
        : '👋 Hello! I am your LLM-ERP assistant. Try asking:\n\n• "How many M6 screws in stock?"\n• "Create PO for 500 M6 from DaMing"\n• "Show BOM for ASM-001"\n• "Check material for 5x CNC-001"',
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
        content: result.reply || t('chat.processed'),
        intent: result.intent,
      }
      setMessages(prev => [...prev, assistantMsg])
      if (result.session_id) {
        setSessionId(result.session_id)
      }
    } catch (err: any) {
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: `${t('chat.error')}${err.message || t('chat.fail')}`,
      }])
    } finally {
      setLoading(false)
    }
  }, [loading, sessionId, t])

  const clearMessages = useCallback(() => {
    setMessages([
      {
        role: 'assistant',
        content: t('chat.reset'),
      },
    ])
    setSessionId(undefined)
  }, [t])

  return { messages, loading, sendMessage, clearMessages, sessionId }
}
