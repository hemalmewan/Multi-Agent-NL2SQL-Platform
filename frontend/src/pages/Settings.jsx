import { motion } from 'framer-motion'
import {
  Clock, DollarSign, Hash, BarChart2, Activity,
  Trash2, TrendingUp,
} from 'lucide-react'
import { useQueryHistory } from '../context/QueryContext'
import { StaticPlotlyChart } from '../components/common/PlotlyChart'

const fadeUp = {
  hidden: { opacity: 0, y: 16 },
  show:   { opacity: 1, y: 0, transition: { duration: 0.4 } },
}
const stagger = { show: { transition: { staggerChildren: 0.08 } } }

function MetricCard({ icon, label, value, sub, color }) {
  return (
    <motion.div variants={fadeUp}
      className="bg-white dark:bg-slate-800 rounded-2xl shadow-card p-5 flex items-start gap-4"
    >
      <div className={`w-11 h-11 rounded-xl flex items-center justify-center flex-shrink-0 ${color}`}>
        {icon}
      </div>
      <div>
        <p className="text-xs text-slate-500 dark:text-slate-400 font-medium">{label}</p>
        <p className="text-2xl font-bold text-slate-800 dark:text-white mt-0.5">{value}</p>
        {sub && <p className="text-xs text-slate-400 mt-0.5">{sub}</p>}
      </div>
    </motion.div>
  )
}

function UsageTrend({ history }) {
  if (history.length < 2) return null

  const last20 = history.slice(0, 20).reverse()
  const labels = last20.map((_, i) => `Q${i + 1}`)

  return (
    <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-card p-5">
      <h3 className="text-base font-semibold text-slate-800 dark:text-white mb-1 flex items-center gap-2">
        <TrendingUp className="w-4 h-4 text-primary-600" /> Token Usage (last 20 queries)
      </h3>
      <p className="text-xs text-slate-400 mb-4">Each bar represents one query's total token consumption.</p>
      <StaticPlotlyChart
        data={[{
          type: 'bar',
          x: labels,
          y: last20.map((h) => h.totalTokens),
          marker: { color: '#2563eb' },
          name: 'Tokens',
        }]}
        layout={{ yaxis: { title: 'Tokens' }, margin: { l: 48, r: 12, t: 20, b: 36 } }}
      />
    </div>
  )
}

function HistoryTable({ history, onClear }) {
  if (history.length === 0) return (
    <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-card p-8 text-center text-slate-400 text-sm">
      No query history yet. Head to the Dashboard and ask a question!
    </div>
  )

  return (
    <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-card overflow-hidden">
      <div className="flex items-center justify-between px-5 py-4 border-b border-slate-100 dark:border-slate-700">
        <h3 className="font-semibold text-slate-800 dark:text-white flex items-center gap-2">
          <Activity className="w-4 h-4 text-primary-600" /> Query History
        </h3>
        <button onClick={onClear}
          className="flex items-center gap-1.5 text-xs text-red-500 hover:text-red-700 dark:hover:text-red-400 transition-colors"
        >
          <Trash2 className="w-3.5 h-3.5" /> Clear
        </button>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-slate-50 dark:bg-slate-700/50">
              {['Query', 'Status', 'Tokens', 'Cost', 'Latency', 'Time'].map((h) => (
                <th key={h} className="px-4 py-2.5 text-left text-xs font-semibold text-slate-500 dark:text-slate-400 whitespace-nowrap">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {history.slice(0, 50).map((row) => (
              <tr key={row.id} className="border-t border-slate-100 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-700/30 transition-colors">
                <td className="px-4 py-2.5 text-slate-700 dark:text-slate-300 max-w-xs truncate">{row.query}</td>
                <td className="px-4 py-2.5">
                  <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${
                    row.status === 'success' ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400' :
                    row.status === 'ambiguous' ? 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400' :
                    'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400'
                  }`}>
                    {row.status}
                  </span>
                </td>
                <td className="px-4 py-2.5 text-slate-600 dark:text-slate-300">{row.totalTokens.toLocaleString()}</td>
                <td className="px-4 py-2.5 text-slate-600 dark:text-slate-300">${row.tokenCost.toFixed(5)}</td>
                <td className="px-4 py-2.5 text-slate-600 dark:text-slate-300">{row.latencyMs} ms</td>
                <td className="px-4 py-2.5 text-slate-400 whitespace-nowrap text-xs">
                  {new Date(row.timestamp).toLocaleString()}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

export default function Settings() {
  const { history, stats, clearHistory } = useQueryHistory()

  const metrics = [
    {
      icon: <Hash className="w-5 h-5 text-primary-600" />,
      label: 'Total Queries',
      value: stats.totalQueries.toLocaleString(),
      color: 'bg-primary-50 dark:bg-primary-900/30',
    },
    {
      icon: <Clock className="w-5 h-5 text-teal-600" />,
      label: 'Avg Latency',
      value: `${stats.avgLatency} ms`,
      sub: 'per query',
      color: 'bg-teal-50 dark:bg-teal-900/30',
    },
    {
      icon: <BarChart2 className="w-5 h-5 text-violet-600" />,
      label: 'Avg Tokens',
      value: stats.avgTokens.toLocaleString(),
      sub: 'per query',
      color: 'bg-violet-50 dark:bg-violet-900/30',
    },
    {
      icon: <DollarSign className="w-5 h-5 text-amber-600" />,
      label: 'Total Cost',
      value: `$${stats.totalCost.toFixed(4)}`,
      sub: `${stats.totalTokens.toLocaleString()} tokens total`,
      color: 'bg-amber-50 dark:bg-amber-900/30',
    },
  ]

  return (
    <main className="min-h-screen bg-medical-bg dark:bg-slate-900 py-10">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 space-y-10">
        <div>
          <h1 className="text-3xl font-extrabold text-slate-900 dark:text-white tracking-tight">Settings</h1>
          <p className="mt-1 text-slate-500 dark:text-slate-400">Monitor your AI usage, token consumption, and query history.</p>
        </div>

        {/* Metric cards */}
        <motion.div
          initial="hidden" animate="show" variants={stagger}
          className="grid sm:grid-cols-2 lg:grid-cols-4 gap-5"
        >
          {metrics.map((m, i) => <MetricCard key={i} {...m} />)}
        </motion.div>

        {/* Trend chart */}
        <UsageTrend history={history} />

        {/* History table */}
        <HistoryTable history={history} onClear={clearHistory} />
      </div>
    </main>
  )
}
