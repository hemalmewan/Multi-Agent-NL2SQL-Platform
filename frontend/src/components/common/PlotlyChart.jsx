import { useRef, forwardRef } from 'react'
import Plot from 'react-plotly.js'
import { Download } from 'lucide-react'

const LAYOUT_BASE = {
  autosize: true,
  margin: { l: 48, r: 24, t: 40, b: 48 },
  paper_bgcolor: 'transparent',
  plot_bgcolor: 'transparent',
  font: { family: 'Inter, system-ui, sans-serif', size: 12 },
  legend: { orientation: 'h', y: -0.2 },
}

const MEDICAL_COLORS = [
  '#2563eb', '#14b8a6', '#8b5cf6', '#f59e0b',
  '#10b981', '#ef4444', '#06b6d4', '#f97316',
]

const PlotlyChart = forwardRef(function PlotlyChart(
  { figure, title, description, onExport },
  ref
) {
  if (!figure) return null

  const layout = {
    ...LAYOUT_BASE,
    ...(figure.layout ?? {}),
    title: undefined,
    colorway: MEDICAL_COLORS,
  }

  const data = (figure.data ?? []).map((trace) => ({
    ...trace,
    marker: {
      ...trace.marker,
      colorscale: trace.marker?.colorscale ?? undefined,
    },
  }))

  return (
    <div ref={ref} className="w-full">
      {onExport && (
        <div className="flex justify-end mb-2">
          <button
            onClick={onExport}
            className="flex items-center gap-1.5 text-xs text-slate-500 hover:text-primary-600 dark:text-slate-400 dark:hover:text-primary-400 transition-colors"
          >
            <Download className="w-3.5 h-3.5" />
            Export PNG
          </button>
        </div>
      )}
      <Plot
        ref={ref}
        data={data}
        layout={layout}
        config={{ responsive: true, displayModeBar: false }}
        useResizeHandler
        style={{ width: '100%', height: '320px' }}
      />
    </div>
  )
})

export default PlotlyChart

/* ── Static chart built from raw JS data (for pre-built charts) ───────────── */
export function StaticPlotlyChart({ data, layout, title, onExport }) {
  const plotRef = useRef(null)

  const mergedLayout = {
    ...LAYOUT_BASE,
    ...layout,
    title: undefined,
    colorway: MEDICAL_COLORS,
  }

  return (
    <div className="w-full">
      {onExport && (
        <div className="flex justify-end mb-2">
          <button
            onClick={() => onExport(plotRef)}
            className="flex items-center gap-1.5 text-xs text-slate-500 hover:text-primary-600 dark:text-slate-400 dark:hover:text-primary-400 transition-colors"
          >
            <Download className="w-3.5 h-3.5" />
            Export PNG
          </button>
        </div>
      )}
      <Plot
        ref={plotRef}
        data={data}
        layout={mergedLayout}
        config={{ responsive: true, displayModeBar: false }}
        useResizeHandler
        style={{ width: '100%', height: '300px' }}
      />
    </div>
  )
}
