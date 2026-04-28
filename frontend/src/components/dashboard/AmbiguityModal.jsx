import { useState, useEffect, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { HelpCircle, X, Send, Lightbulb, AlertCircle, Sparkles } from 'lucide-react'

const EXAMPLE_HINTS = [
  'Show monthly revenue for cardiology in 2024',
  'Top 5 doctors by patient count last quarter',
  'Diagnoses trend for patients aged 40–60 this year',
]

export default function AmbiguityModal({ open, originalQuery, attemptNumber = 1, maxAttempts = 3, onSubmit, onClose }) {
  const [refined, setRefined] = useState('')
  const textareaRef = useRef(null)

  // Auto-focus textarea when modal opens
  useEffect(() => {
    if (open) {
      setRefined('')
      setTimeout(() => textareaRef.current?.focus(), 120)
    }
  }, [open])

  function handleSubmit(e) {
    e.preventDefault()
    if (refined.trim()) {
      onSubmit(refined.trim())
      setRefined('')
    }
  }

  function applyHint(hint) {
    setRefined(hint)
    textareaRef.current?.focus()
  }

  return (
    <AnimatePresence>
      {open && (
        <div className="fixed inset-0 z-50 flex items-center justify-center px-4">

          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.18 }}
            className="absolute inset-0 bg-slate-900/50 backdrop-blur-sm"
            onClick={onClose}
          />

          {/* Modal card */}
          <motion.div
            initial={{ opacity: 0, scale: 0.92, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.92, y: 20 }}
            transition={{ type: 'spring', stiffness: 380, damping: 28 }}
            className="relative z-10 w-full max-w-lg"
          >
            {/* Glow ring */}
            <div className="absolute -inset-px rounded-2xl bg-gradient-to-br from-amber-400/40 via-orange-300/20 to-amber-400/40 blur-sm" />

            <div className="relative bg-white dark:bg-slate-800 rounded-2xl shadow-2xl overflow-hidden">

              {/* Coloured top bar */}
              <div className="h-1.5 w-full bg-gradient-to-r from-amber-400 via-orange-400 to-amber-500" />

              <div className="p-6">

                {/* Header */}
                <div className="flex items-start justify-between mb-5">
                  <div className="flex items-center gap-3">
                    <div className="w-11 h-11 rounded-2xl bg-amber-100 dark:bg-amber-900/40 flex items-center justify-center shadow-inner">
                      <HelpCircle className="w-6 h-6 text-amber-600 dark:text-amber-400" />
                    </div>
                    <div>
                      <h3 className="text-base font-bold text-slate-800 dark:text-white leading-tight">
                        A Little More Detail?
                      </h3>
                      <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                        Attempt {attemptNumber} of {maxAttempts} — we need clarification to answer accurately.
                      </p>
                    </div>
                  </div>
                  <button
                    onClick={onClose}
                    className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 transition-colors p-1 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-700"
                  >
                    <X className="w-4 h-4" />
                  </button>
                </div>

                {/* Alert strip */}
                <div className="flex items-start gap-2.5 px-3.5 py-3 rounded-xl bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-700/50 mb-4">
                  <AlertCircle className="w-4 h-4 text-amber-600 dark:text-amber-400 mt-0.5 flex-shrink-0" />
                  <p className="text-xs text-amber-800 dark:text-amber-300 leading-relaxed">
                    Your query was a bit broad. Adding context like a&nbsp;
                    <span className="font-semibold">time range</span>,&nbsp;
                    <span className="font-semibold">department</span>, or&nbsp;
                    <span className="font-semibold">specific metric</span> helps
                    Medicore give you a precise answer.
                  </p>
                </div>

                {/* Original query pill */}
                {originalQuery && (
                  <div className="mb-4 px-3.5 py-2.5 rounded-xl bg-slate-50 dark:bg-slate-700/60 border border-slate-200 dark:border-slate-600">
                    <span className="text-xs font-semibold text-slate-400 dark:text-slate-500 uppercase tracking-wide block mb-0.5">
                      Your original query
                    </span>
                    <p className="text-sm text-slate-700 dark:text-slate-200 italic">
                      "{originalQuery}"
                    </p>
                  </div>
                )}

                {/* Refinement form */}
                <form onSubmit={handleSubmit} className="flex flex-col gap-3">
                  <div className="relative">
                    <textarea
                      ref={textareaRef}
                      value={refined}
                      onChange={(e) => setRefined(e.target.value)}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) handleSubmit(e)
                      }}
                      placeholder="e.g. Show monthly revenue for cardiology in 2024…"
                      rows={3}
                      className="w-full px-4 py-3 rounded-xl border border-slate-200 dark:border-slate-600 bg-white dark:bg-slate-700 text-slate-800 dark:text-white text-sm placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-amber-400 dark:focus:ring-amber-500 resize-none transition-shadow"
                    />
                    <span className="absolute bottom-2.5 right-3 text-xs text-slate-300 dark:text-slate-600 select-none pointer-events-none">
                      ⌘↵ to send
                    </span>
                  </div>

                  {/* Hint chips */}
                  <div>
                    <p className="text-xs text-slate-400 dark:text-slate-500 flex items-center gap-1 mb-1.5">
                      <Lightbulb className="w-3 h-3" /> Try one of these:
                    </p>
                    <div className="flex flex-wrap gap-1.5">
                      {EXAMPLE_HINTS.map((hint) => (
                        <button
                          key={hint}
                          type="button"
                          onClick={() => applyHint(hint)}
                          className="text-xs px-2.5 py-1 rounded-full bg-amber-50 dark:bg-amber-900/30 text-amber-700 dark:text-amber-400 border border-amber-200 dark:border-amber-700/50 hover:bg-amber-100 dark:hover:bg-amber-800/40 transition-colors"
                        >
                          <Sparkles className="w-2.5 h-2.5 inline mr-1 opacity-70" />
                          {hint}
                        </button>
                      ))}
                    </div>
                  </div>

                  {/* Actions */}
                  <div className="flex justify-end gap-2 pt-1">
                    <button
                      type="button"
                      onClick={onClose}
                      className="px-4 py-2 rounded-lg text-sm font-medium text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors"
                    >
                      Cancel
                    </button>
                    <button
                      type="submit"
                      disabled={!refined.trim()}
                      className="flex items-center gap-1.5 px-5 py-2 rounded-lg bg-gradient-to-r from-amber-500 to-orange-500 hover:from-amber-600 hover:to-orange-600 disabled:opacity-40 disabled:cursor-not-allowed text-white text-sm font-semibold shadow-sm transition-all"
                    >
                      <Send className="w-3.5 h-3.5" />
                      Submit Refined Query
                    </button>
                  </div>
                </form>

              </div>
            </div>
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  )
}
