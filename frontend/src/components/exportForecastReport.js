const number = (value) => Number(value).toLocaleString('en-US', { maximumFractionDigits: 1 })
const month = (value) => new Date(`${value.slice(0, 10)}T00:00:00`).toLocaleDateString('en-US', { month: 'short', year: 'numeric' })

// Vector text and chart remain sharp at any zoom; all horizons fit one A4 page.
export async function createForecastPdf(result) {
  const { jsPDF } = await import('jspdf')
  const pdf = new jsPDF({ unit: 'mm', format: 'a4', compress: true })
  const green = '#123d32'
  const muted = '#64776f'
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
  const rule = (y) => { pdf.setDrawColor('#dce6e0'); pdf.setLineWidth(0.2); pdf.line(14, y, 196, y) }
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
  text('NEXT-MONTH FORECAST', 20, 59, 7, '#b4e6d1', true)
  text(number(result.forecast), 20, 71, 24, '#ffffff', true)
  text(`units | ${month(result.forecast_period)}`, 20, 77, 7, '#cae3d8')
  text('PLANNING HORIZON', 147, 59, 7, '#b4e6d1', true)
  text(`${result.predictions.length} months`, 147, 70, 17, '#ffffff', true)
  text(`${result.trend} trend`, 147, 77, 7, '#cae3d8')
  const total = result.predictions.reduce((sum, point) => sum + point.quantity, 0)
  const accuracy = result.accuracy
  const metrics = [['HORIZON TOTAL', number(total), 'projected units'], ['BACKTEST MAPE', `${number(accuracy.mape_percent)}%`, 'lower error is better'], ['VALIDATION', String(accuracy.test_points), 'historical predictions']]
  metrics.forEach(([label, value, detail], index) => {
    const x = 14 + index * 62
    box(x, 85, 58, 22, '#f0f6f2')
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
  box(boundary, 120, 194 - boundary, 40, '#fff5df')
  for (let i = 0; i <= 4; i++) {
    pdf.setDrawColor('#dde5e2'); pdf.setLineWidth(0.15); pdf.setLineDashPattern([0.5, 1], 0)
    pdf.line(29, y(max * i / 4), 194, y(max * i / 4))
    text(number(max * i / 4), 26, y(max * i / 4) + 1, 5.5, muted, false, { align: 'right' })
  }
  points.forEach((point, i) => {
    if (i > 0) {
      const projected = i >= result.history.length
      pdf.setDrawColor(projected ? '#c58717' : '#08785d'); pdf.setLineWidth(0.55)
      pdf.setLineDashPattern(projected ? [1.4, 1] : [], 0)
      pdf.line(x(i - 1), y(points[i - 1].quantity), x(i), y(point.quantity))
    }
    if (i % Math.max(1, Math.ceil(points.length / 6)) === 0) text(month(point.date), x(i), 165, 5.5, muted, false, { align: 'center' })
  })
  pdf.setLineDashPattern([], 0)
  text(`History: ${month(result.history_start)} - ${month(result.history_end)}. Shading marks future months, not a confidence interval.`, 14, 170, 6.3, muted)
  box(14, 175, 182, 17, '#faf8ef')
  text('PLANNING RECOMMENDATION', 18, 180, 6.5, '#907123', true)
  paragraph(result.recommendation, 18, 185, 174, 7)
  text('02 / Monthly production outlook', 14, 200, 11, green, true)
  // Two table columns cap the row count at six for a 12-month report.
  const columns = result.predictions.length > 6 ? 2 : 1
  const split = columns === 2 ? Math.ceil(result.predictions.length / 2) : result.predictions.length
  for (let column = 0; column < columns; column++) {
    const left = 14 + column * 94
    const width = columns === 2 ? 88 : 182
    box(left, 204, width, 6, '#edf4ef')
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
  text('03 / Model & validation', 14, notesY, 10, green, true)
  box(14, notesY + 3, 182, 19, '#f3f6f3')
  text("Holt's linear trend model", 18, notesY + 8, 7.5, green, true)
  text(`Alpha ${result.smoothing_parameters.alpha} | Beta ${result.smoothing_parameters.beta}`, 18, notesY + 13, 6.5, muted)
  text(`RMSE ${number(accuracy.rmse)} | MAE ${number(accuracy.mae)} units`, 18, notesY + 18, 6.5, muted)
  paragraph(`Backtests measure past error, not future certainty. MAPE excludes zero actuals.${accuracy.test_points < 6 ? ' Limited validation history: preliminary metrics.' : ''}`, 108, notesY + 8, 83, 6.5)
  rule(285)
  text('OMNI | Source: MongoDB demand history', 14, 290, 6.5, muted)
  text(`${result.sku} | 1 / 1`, 196, 290, 6.5, muted, false, { align: 'right' })
  return pdf
}

export default async function exportForecastReport(result) {
  const pdf = await createForecastPdf(result)
  await pdf.save(`${result.sku}-demand-forecast.pdf`, { returnPromise: true })
}
