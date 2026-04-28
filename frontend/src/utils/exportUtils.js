export function exportCSV(data, filename = 'medicore-results.csv') {
  if (!data || data.length === 0) return
  const headers = Object.keys(data[0])
  const rows = data.map((row) =>
    headers.map((h) => JSON.stringify(row[h] ?? '')).join(',')
  )
  const csv = [headers.join(','), ...rows].join('\n')
  const blob = new Blob([csv], { type: 'text/csv' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}

export function exportChartPNG(plotlyRef, filename = 'medicore-chart.png') {
  if (!plotlyRef?.current) return
  import('plotly.js-dist-min').then((Plotly) => {
    Plotly.downloadImage(plotlyRef.current.el, {
      format: 'png',
      filename,
      width: 1200,
      height: 600,
    })
  })
}
