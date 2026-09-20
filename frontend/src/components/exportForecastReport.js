const number = (value) => value == null ? 'N/A' : Number(value).toLocaleString('en-US', { maximumFractionDigits: 1 })
const month = (value) => new Date(`${value.slice(0, 10)}T00:00:00`).toLocaleDateString('en-US', { month: 'short', year: 'numeric' })

// One-page A4 summary with vector text and a compact demand chart.
export async function createForecastPdf(result) {
  const { jsPDF } = await import('jspdf')
  const pdf = new jsPDF({ unit: 'mm', format: 'a4', compress: true })
  const green = '#1e40af'
  const muted = '#64748b'
  const text = (value, x, y, size = 9, color = green, bold = false, options = {}) => {
    pdf.setFont('helvetica', bold ? 'bold' : 'normal')
    pdf.setFontSize(size)
    pdf.setTextColor(color)
    pdf.text(String(value), x, y, options)
  }
  const box = (x, y, w, h, color) => {
    pdf.setFillColor(color)
    pdf.roundedRect(x, y, w, h, 2, 2, 'F')
  }
  const rule = (y) => { pdf.setDrawColor('#e2e8f0'); pdf.setLineWidth(0.2); pdf.line(14, y, 196, y) }
  // Keep arrays as separate text lines rather than converting them to commas.
  const paragraph = (value, x, y, width, size = 8, color = muted) => {
    pdf.setFont('helvetica', 'normal'); pdf.setFontSize(size); pdf.setTextColor(color)
    const lines = pdf.splitTextToSize(String(value), width)
    pdf.text(lines, x, y)
    return lines.length * size * 0.405
  }
  pdf.setProperties({ title: `${result.sku} - Demand forecast`, author: 'OMNI', subject: 'Demand planning report' })
  text('OMNI.', 14, 19, 19, green, true)
  text('DEMAND INTELLIGENCE / PLANNING REPORT', 196, 18, 7, muted, true, { align: 'right' })
  rule(23)
  text('Your demand outlook.', 14, 34, 23, green, true)
  paragraph(`${result.sku} | ${result.product_name}`, 14, 41, 180, 9)
  text(`Generated ${new Date(result.generated_at).toLocaleString('en-US')}`, 14, 47, 7, muted)
  box(14, 52, 182, 29, green)
  text('NEXT-MONTH FORECAST', 20, 59, 7, '#bfdbfe', true)
  text(number(result.forecast), 20, 71, 24, '#ffffff', true)
  text(`units | ${month(result.forecast_period)}`, 20, 77, 7, '#bfdbfe')
  text('PLANNING HORIZON', 147, 59, 7, '#bfdbfe', true)
  text(`${result.predictions.length} months`, 147, 70, 17, '#ffffff', true)
  text(`${result.trend} trend`, 147, 77, 7, '#bfdbfe')
  const total = result.predictions.reduce((sum, point) => sum + point.quantity, 0)
  const accuracy = result.accuracy || {}
  const percent = (value) => value == null ? 'N/A' : `${number(value)}%`
  const metrics = [['HORIZON TOTAL', number(total), 'projected units'], ['ACCURACY SCORE', percent(accuracy.accuracy_percent), 'derived from 100 - WAPE'], ['FORECAST ERROR / WAPE', percent(accuracy.wape_percent), 'lower error is better']]
  metrics.forEach(([label, value, detail], index) => {
    const x = 14 + index * 62
    box(x, 85, 58, 22, '#f0f9ff')
    text(label, x + 4, 91, 6.5, muted, true)
    text(value, x + 4, 98, 15, green, true)
    text(detail, x + 4, 103, 6.5, muted)
  })
  text('01 / Demand trajectory', 14, 115, 11, green, true)
  text('Emerald: actual | Dashed amber: forecast', 196, 115, 6.5, muted, false, { align: 'right' })
  const points = [...result.history, ...result.predictions]
  const max = Math.max(1, ...points.map((point) => point.quantity)) * 1.15
  const x = (i) => 29 + i / Math.max(1, points.length - 1) * 160
  const y = (value) => 160 - value / max * 37
  const boundary = result.history.length ? (x(result.history.length - 1) + x(result.history.length)) / 2 : 29
  box(boundary, 120, 194 - boundary, 40, '#eff6ff')
  for (let i = 0; i <= 4; i++) {
    pdf.setDrawColor('#e2e8f0'); pdf.setLineWidth(0.15); pdf.setLineDashPattern([0.5, 1], 0)
    pdf.line(29, y(max * i / 4), 194, y(max * i / 4))
    text(number(max * i / 4), 26, y(max * i / 4) + 1, 5.5, muted, false, { align: 'right' })
  }
  points.forEach((point, i) => {
    if (i > 0) {
      const projected = i >= result.history.length
      pdf.setDrawColor(projected ? '#0369a1' : '#2563eb'); pdf.setLineWidth(0.55)
      pdf.setLineDashPattern(projected ? [1.4, 1] : [], 0)
      pdf.line(x(i - 1), y(points[i - 1].quantity), x(i), y(point.quantity))
    }
    if (i % Math.max(1, Math.ceil(points.length / 6)) === 0) text(month(point.date), x(i), 165, 5.5, muted, false, { align: 'center' })
  })
  pdf.setLineDashPattern([], 0)
  text(`History: ${month(result.history_start)} - ${month(result.history_end)}. Shading marks future months, not a confidence interval.`, 14, 170, 6.3, muted)
  box(14, 175, 182, 17, '#f8fafc')
  text('PLANNING RECOMMENDATION', 18, 180, 6.5, '#475569', true)
  paragraph(result.recommendation, 18, 185, 174, 7)
  text('02 / Monthly production outlook', 14, 200, 11, green, true)
  // Two table columns cap the row count at six for a 12-month report.
  const columns = result.predictions.length > 6 ? 2 : 1
  const split = columns === 2 ? Math.ceil(result.predictions.length / 2) : result.predictions.length
  for (let column = 0; column < columns; column++) {
    const left = 14 + column * 94
    const width = columns === 2 ? 88 : 182
    box(left, 204, width, 6, '#f0f9ff')
    text('MONTH', left + 3, 208, 6.5, muted, true)
    text('FORECAST UNITS', left + width - 3, 208, 6.5, muted, true, { align: 'right' })
    result.predictions.slice(column * split, (column + 1) * split).forEach((point, i) => {
      const yy = 215 + i * 4.5
      text(month(point.date), left + 3, yy, 7)
      text(number(point.quantity), left + width - 3, yy, 7, green, true, { align: 'right' })
    })
  }
  const tableEnd = 215 + split * 4.5
  rule(tableEnd)
  text('Total planned demand', 17, tableEnd + 5, 7.5, green, true)
  text(number(total), 193, tableEnd + 5, 7.5, green, true, { align: 'right' })
  const notesY = tableEnd + 13
  text('03 / Data quality', 14, notesY, 10, green, true)
  text('04 / Demand history', 108, notesY, 10, green, true)
  box(14, notesY + 3, 88, 24, '#f8fafc')
  box(108, notesY + 3, 88, 24, '#f8fafc')
  const quality = result.data_quality
  const qualityLabels = { passed: 'Checks passed', needs_review: 'Needs review', blocked: 'Forecast blocked' }
  text(quality ? qualityLabels[quality.status] || quality.status : 'Quality information unavailable', 18, notesY + 8, 7, green, true)
  text(`Checked: ${number(quality?.records_checked)} | Usable: ${number(quality?.valid_records)}`, 18, notesY + 13, 6.5, muted)
  text(`Excluded: ${number(quality?.invalid_records)} | Usable months: ${number(quality?.usable_months)}`, 18, notesY + 18, 6.5, muted)
  text(quality ? `${quality.issues?.length ?? 0} issues | ${quality.can_forecast ? 'Enough history to forecast' : 'Review required'}` : 'Run a data quality check for details.', 18, notesY + 23, 6.5, muted)
  text(`${month(result.history_start)} - ${month(result.history_end)} | ${result.history_points} months`, 112, notesY + 8, 6.5, green, true)
  text(`Average: ${number(result.average_historical_demand)} units/month`, 112, notesY + 12, 6.5, muted)
  const recentHistory = result.history.slice(-3)
  text(`Latest ${recentHistory.length} recorded months`, 112, notesY + 16, 6, muted)
  recentHistory.forEach((point, index) => {
    const left = 112 + index * 27
    text(month(point.date), left, notesY + 20, 6, muted)
    text(`${number(point.quantity)} units`, left, notesY + 24, 6, green, true)
  })
  rule(285)
  text('OMNI | Source: MongoDB demand history', 14, 290, 6.5, muted)
  text(`${result.sku} | 1 / 1`, 196, 290, 6.5, muted, false, { align: 'right' })
  return pdf
}

export default async function exportForecastReport(result) {
  const pdf = await createForecastPdf(result)
  await pdf.save(`${result.sku}-demand-forecast.pdf`, { returnPromise: true })
}
