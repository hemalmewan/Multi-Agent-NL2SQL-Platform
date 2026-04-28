import { createContext, useContext, useEffect, useState } from 'react'

const QueryContext = createContext(null)

const STORAGE_KEY = 'medicore-query-history'

function load() {
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY)) ?? []
  } catch {
    return []
  }
}

export function QueryProvider({ children }) {
  const [history, setHistory] = useState(load)

  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(history))
  }, [history])

  function addEntry(entry) {
    setHistory((prev) => [
      {
        id: Date.now(),
        timestamp: new Date().toISOString(),
        query: entry.query,
        status: entry.status,
        totalTokens: entry.total_tokens ?? 0,
        tokenCost: entry.token_cost ?? 0,
        latencyMs: entry.latency_ms ?? 0,
      },
      ...prev,
    ].slice(0, 200))
  }

  function clearHistory() {
    setHistory([])
  }

  const stats = {
    totalQueries: history.length,
    totalTokens: history.reduce((s, h) => s + h.totalTokens, 0),
    totalCost: history.reduce((s, h) => s + h.tokenCost, 0),
    avgLatency:
      history.length > 0
        ? Math.round(history.reduce((s, h) => s + h.latencyMs, 0) / history.length)
        : 0,
    avgTokens:
      history.length > 0
        ? Math.round(history.reduce((s, h) => s + h.totalTokens, 0) / history.length)
        : 0,
  }

  return (
    <QueryContext.Provider value={{ history, addEntry, clearHistory, stats }}>
      {children}
    </QueryContext.Provider>
  )
}

export function useQueryHistory() {
  return useContext(QueryContext)
}
