import { useState, useRef, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Send, Bot, User, Sparkles } from 'lucide-react'
import { sendQuery } from '../../utils/api'
import { useQueryHistory } from '../../context/QueryContext'
import ResultDisplay from './ResultDisplay'
import AmbiguityModal from './AmbiguityModal'
import ErrorBanner from './ErrorBanner'
import LoadingSpinner from '../common/LoadingSpinner'

const SAMPLE_QUERIES = [
  'Show top 10 doctors by patient count',
  'What is the monthly revenue trend this year?',
  'List the most common diagnoses',
  'How many patients were admitted last month?',
  'Show revenue by payment method',
]

function Message({ msg }) {
  const isUser = msg.role === 'user'
  return (
    <motion.div
      initial={{ opacity: 0, x: isUser ? 16 : -16 }}
      animate={{ opacity: 1, x: 0 }}
      className={`flex gap-3 ${isUser ? 'flex-row-reverse' : 'flex-row'}`}
    >
      <div className={`w-8 h-8 flex-shrink-0 rounded-full flex items-center justify-center text-white shadow-sm ${isUser ? 'bg-primary-600' : 'bg-gradient-to-br from-teal-500 to-primary-600'}`}>
        {isUser ? <User className="w-4 h-4" /> : <Bot className="w-4 h-4" />}
      </div>
      <div className={`max-w-[80%] ${isUser ? 'items-end' : 'items-start'} flex flex-col gap-2`}>
        <div className={`px-4 py-2.5 rounded-2xl text-sm leading-relaxed ${
          isUser
            ? 'bg-primary-600 text-white rounded-tr-sm'
            : 'bg-slate-100 dark:bg-slate-700 text-slate-800 dark:text-slate-100 rounded-tl-sm'
        }`}>
          {msg.text}
        </div>
        {msg.result && <ResultDisplay result={msg.result} />}
        {msg.status === 'ignored' && (
          <p className="text-xs text-slate-400 px-1">
            This doesn't look like a data query. Try asking about patients, doctors, revenue, or diagnoses.
          </p>
        )}
        {msg.status === 'refinement_failed' && (
          <div className="flex items-start gap-2 px-3.5 py-3 rounded-xl bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-700/50 text-red-700 dark:text-red-300 text-xs leading-relaxed mt-1">
            <span className="text-base leading-none">⚠️</span>
            <span><span className="font-semibold">Query refined failed</span> — please try again later with a more specific question.</span>
          </div>
        )}
        {msg.status === 'guardrails_blocked' && (
          <div className="flex items-start gap-2 px-3.5 py-3 rounded-xl bg-orange-50 dark:bg-orange-900/20 border border-orange-200 dark:border-orange-700/50 text-orange-800 dark:text-orange-300 text-xs leading-relaxed mt-1">
            <span className="text-base leading-none">🛡️</span>
            <div>
              <span className="font-semibold block mb-0.5">Query Blocked by Security Guardrails</span>
              <span>{msg.detail}</span>
            </div>
          </div>
        )}
      </div>
    </motion.div>
  )
}

const MAX_REFINEMENTS = 3

export default function ChatInterface() {
  const [messages, setMessages] = useState([
    { id: 0, role: 'assistant', text: 'Hello! I\'m Medicore AI. Ask me anything about your hospital data — admissions, revenue, diagnoses, doctor workload, and more.' }
  ])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [ambiguous, setAmbiguous] = useState(null) // { originalQuery }
  const [refinementCount, setRefinementCount] = useState(0)
  const bottomRef = useRef(null)
  const { addEntry } = useQueryHistory()

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  async function runQuery(query, refinedQuery = null, attemptCount = 0) {
    setLoading(true)
    setError(null)
    try {
      const result = await sendQuery(query, refinedQuery)
      addEntry({ query: refinedQuery ?? query, ...result })

      if (result.status === 'ambiguous') {
        if (attemptCount >= MAX_REFINEMENTS) {
          setAmbiguous(null)
          setRefinementCount(0)
          setMessages((prev) => [...prev, {
            id: Date.now(), role: 'assistant',
            text: 'Query refined failed please try again later!',
            status: 'refinement_failed',
          }])
          return
        }
        setAmbiguous({ originalQuery: refinedQuery ?? query })
        setMessages((prev) => [...prev, {
          id: Date.now(), role: 'assistant',
          text: `⚠️ Your query needs a bit more detail (attempt ${attemptCount + 1}/${MAX_REFINEMENTS}). I've opened a refinement window for you.`,
        }])
        return
      }

      if (result.status === 'guardrails_blocked') {
        setMessages((prev) => [...prev, {
          id: Date.now(), role: 'assistant',
          text: '',
          detail: result.message ?? 'This query was blocked by the security guardrails.',
          status: 'guardrails_blocked',
        }])
        return
      }

      if (result.status === 'error') {
        setError(result.message ?? 'An unexpected error occurred.')
        return
      }

      if (result.status === 'ignored') {
        setMessages((prev) => [...prev, { id: Date.now(), role: 'assistant', text: '', status: 'ignored' }])
        return
      }

      setMessages((prev) => [...prev, {
        id: Date.now(), role: 'assistant',
        text: result.status === 'success'
          ? '✅ Here are your results:'
          : result.message ?? 'Query processed.',
        result,
      }])
    } catch (err) {
      setError(err?.response?.data?.detail ?? err.message ?? 'Failed to reach the server. Make sure the backend is running.')
    } finally {
      setLoading(false)
    }
  }

  function handleSend(e) {
    e?.preventDefault()
    const q = input.trim()
    if (!q || loading) return
    setInput('')
    setRefinementCount(0)
    setMessages((prev) => [...prev, { id: Date.now(), role: 'user', text: q }])
    runQuery(q)
  }

  function handleAmbiguitySubmit(refinedQuery) {
    const original = ambiguous.originalQuery
    const newCount = refinementCount + 1
    setAmbiguous(null)
    setRefinementCount(newCount)
    setMessages((prev) => [...prev, { id: Date.now(), role: 'user', text: refinedQuery }])
    runQuery(original, refinedQuery, newCount)
  }

  return (
    <div className="flex flex-col h-full">
      <h2 className="text-xl font-bold text-slate-800 dark:text-white mb-4 flex items-center gap-2">
        <span className="w-1 h-6 rounded-full bg-gradient-to-b from-primary-600 to-teal-500 inline-block" />
        Ask Your Data
      </h2>

      {/* Error banner */}
      <ErrorBanner message={error} onDismiss={() => setError(null)} />

      {/* Messages */}
      <div className="flex-1 overflow-y-auto rounded-2xl bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 p-4 space-y-5 min-h-[320px] max-h-[520px] mt-3">
        <AnimatePresence initial={false}>
          {messages.map((msg) => (
            <Message key={msg.id} msg={msg} />
          ))}
        </AnimatePresence>
        {loading && (
          <div className="flex gap-3 items-start">
            <div className="w-8 h-8 rounded-full bg-gradient-to-br from-teal-500 to-primary-600 flex items-center justify-center">
              <Bot className="w-4 h-4 text-white" />
            </div>
            <div className="px-4 py-3 rounded-2xl rounded-tl-sm bg-slate-100 dark:bg-slate-700">
              <LoadingSpinner size="sm" label="Analysing your query…" />
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Sample queries */}
      <div className="flex flex-wrap gap-2 mt-3">
        {SAMPLE_QUERIES.map((q) => (
          <button key={q} onClick={() => { setInput(q) }}
            className="text-xs px-3 py-1.5 rounded-full bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-slate-500 dark:text-slate-400 hover:border-primary-300 hover:text-primary-600 dark:hover:border-primary-600 dark:hover:text-primary-400 transition-colors"
          >
            <Sparkles className="w-3 h-3 inline mr-1" />{q}
          </button>
        ))}
      </div>

      {/* Input */}
      <form onSubmit={handleSend} className="flex gap-2 mt-3">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask anything about your hospital data…"
          disabled={loading}
          className="flex-1 px-4 py-3 rounded-xl border border-slate-200 dark:border-slate-600 bg-white dark:bg-slate-800 text-slate-800 dark:text-white placeholder-slate-400 text-sm focus:outline-none focus:ring-2 focus:ring-primary-400 disabled:opacity-60"
        />
        <button
          type="submit" disabled={!input.trim() || loading}
          className="flex items-center gap-1.5 px-5 py-3 rounded-xl bg-primary-600 hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed text-white font-semibold text-sm transition-colors shadow-sm"
        >
          <Send className="w-4 h-4" />
        </button>
      </form>

      {/* Ambiguity modal */}
      <AmbiguityModal
        open={!!ambiguous}
        originalQuery={ambiguous?.originalQuery}
        attemptNumber={refinementCount + 1}
        maxAttempts={MAX_REFINEMENTS}
        onSubmit={handleAmbiguitySubmit}
        onClose={() => setAmbiguous(null)}
      />
    </div>
  )
}
