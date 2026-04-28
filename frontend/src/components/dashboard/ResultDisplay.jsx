import { useRef } from 'react'
import { motion } from 'framer-motion'
import { Download, Code2, Lightbulb, Table2 } from 'lucide-react'
import PlotlyChart from '../common/PlotlyChart'
import { exportCSV, exportChartPNG } from '../../utils/exportUtils'

function SQLBlock({ sql }) {
  return (
    <details className="group">
      <summary className="flex items-center gap-1.5 text-xs font-medium text-slate-500 dark:text-slate-400 cursor-pointer hover:text-primary-600 dark:hover:text-primary-400 transition-colors select-none list-none">
        <Code2 className="w-3.5 h-3.5" />
        View SQL
        <span className="ml-auto group-open:rotate-180 transition-transform">▾</span>
      </summary>
      <pre className="mt-2 p-3 rounded-lg bg-slate-900 dark:bg-slate-950 text-green-400 text-xs overflow-x-auto leading-relaxed">
        {sql}
      </pre>
    </details>
  )
}

function InsightBox({ text }) {
  if (!text) return null
  return (
    <div className="flex gap-2 mt-3 p-3 rounded-lg bg-teal-50 dark:bg-teal-900/20 border border-teal-100 dark:border-teal-800">
      <Lightbulb className="w-4 h-4 text-teal-600 dark:text-teal-400 flex-shrink-0 mt-0.5" />
      <p className="text-sm text-teal-800 dark:text-teal-300 leading-relaxed">{text}</p>
    </div>
  )
}

function TableView({ data, columns, onExport }) {
  if (!data || data.length === 0) return <p className="text-sm text-slate-400">No data rows.</p>
  const cols = columns ?? Object.keys(data[0])
  return (
    <div>
      <div className="flex justify-end mb-2">
        <button
          onClick={onExport}
          className="flex items-center gap-1.5 text-xs text-slate-500 hover:text-primary-600 dark:text-slate-400 dark:hover:text-primary-400 transition-colors"
        >
          <Download className="w-3.5 h-3.5" /> Download CSV
        </button>
      </div>
      <div className="overflow-x-auto rounded-xl border border-slate-200 dark:border-slate-700">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-slate-50 dark:bg-slate-700">
              {cols.map((c) => (
                <th key={c} className="px-4 py-2.5 text-left font-semibold text-slate-600 dark:text-slate-300 whitespace-nowrap">
                  {c}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {data.map((row, i) => (
              <tr key={i} className="border-t border-slate-100 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-700/50 transition-colors">
                {cols.map((c) => (
                  <td key={c} className="px-4 py-2.5 text-slate-700 dark:text-slate-300 whitespace-nowrap">
                    {String(row[c] ?? '—')}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

export default function ResultDisplay({ result }) {
  const chartRef = useRef(null)
  if (!result) return null

  const { sql_query, visualization } = result

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}
      className="mt-4 bg-white dark:bg-slate-800 rounded-2xl shadow-card p-5 flex flex-col gap-4"
    >
      {/* SQL toggle */}
      {sql_query && <SQLBlock sql={sql_query} />}

      {/* Visualization */}
      {visualization && (
        <>
          {visualization.type === 'chart' && (
            <div>
              <PlotlyChart
                ref={chartRef}
                figure={visualization.figure}
                onExport={() => exportChartPNG(chartRef, 'medicore-chart.png')}
              />
              <InsightBox text={visualization.insights} />
            </div>
          )}

          {visualization.type === 'table' && (
            <div>
              <div className="flex items-center gap-2 mb-3">
                <Table2 className="w-4 h-4 text-slate-500" />
                <span className="text-sm font-medium text-slate-600 dark:text-slate-300">
                  {visualization.content} rows returned
                </span>
              </div>
              <TableView
                data={visualization.data}
                columns={visualization.columns}
                onExport={() => exportCSV(visualization.data)}
              />
            </div>
          )}

          {visualization.type === 'text' && (
            <div className="p-4 rounded-xl bg-primary-50 dark:bg-primary-900/20 border border-primary-100 dark:border-primary-800">
              <p className="text-sm text-primary-800 dark:text-primary-200 leading-relaxed">
                {visualization.content}
              </p>
            </div>
          )}
        </>
      )}

      {!visualization && result.status === 'success' && (
        <p className="text-sm text-slate-400 dark:text-slate-500">Query executed — no visualisation available for this result.</p>
      )}

      {/* Meta */}
      <div className="flex flex-wrap gap-4 pt-2 border-t border-slate-100 dark:border-slate-700">
        {result.latency_ms !== undefined && (
          <span className="text-xs text-slate-400">⏱ {result.latency_ms} ms</span>
        )}
        {result.total_tokens !== undefined && (
          <span className="text-xs text-slate-400">🔢 {result.total_tokens} tokens</span>
        )}
        {result.token_cost !== undefined && (
          <span className="text-xs text-slate-400">💰 ${result.token_cost.toFixed(5)}</span>
        )}
      </div>
    </motion.div>
  )
}
