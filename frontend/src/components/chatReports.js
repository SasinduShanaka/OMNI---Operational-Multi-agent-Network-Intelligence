export function isReportRequest(text) {
  return /\b(download|export|pdf|reports?)\b/i.test(text)
}

export function managementReportScope(text) {
  const areas = [
    ['inventory', /\b(inventory|stock|fabric)\b/i],
    ['forecast', /\b(forecast|demand)\b/i],
    ['production', /\b(production|capacity)\b/i],
    ['supply_chain', /\b(supply chain|shipments?|procurement|suppliers?)\b/i],
  ]
  const selected = areas.filter(([, pattern]) => pattern.test(text)).map(([key]) => key)
  return {
    title: 'Factory management report',
    domains: selected.length && !/\ball (agents|areas)\b/i.test(text) ? selected : areas.map(([key]) => key),
    skus: [...new Set(text.toUpperCase().match(/GAR-\d{3}\b/g) || [])],
  }
}

export function isManagementReportRequest(text) {
  const scope = managementReportScope(text)
  const namedAreas = /\b(inventory|stock|fabric|forecast|demand|production|capacity|supply chain|shipments?|procurement|suppliers?)\b/i.test(text)
  return /\breports?\b/i.test(text) && (/\b(management|combined|comprehensive|all agents|all areas|factory|executive)\b/i.test(text) || (namedAreas && scope.domains.length > 1))
}

export function isReportNavigationRequest(text) {
  return /\breports?\b/i.test(text) && /\b(schedule|scheduled|daily|monthly|history|saved|previous reports)\b/i.test(text)
}

// A product picker is only a request for the information needed to make a
// forecast. It is not useful report content and must never produce a PDF.
export function hasReportContent(data) {
  if (!data || data.status === 'needs_information' || data.suggested_products?.length) return false
  return Boolean(
    data.sections ||
    data.result ||
    data.data ||
    data.comparisons?.length ||
    data.results?.length
  )
}

export function reportSource(messages) {
  const previous = [...messages].reverse().find((item) => item.type === 'agent' && item.data && (
    item.data.reportSource ||
    (!['report_download', 'report_navigation', 'unknown'].includes(item.data.intent) && hasReportContent(item.data))
  ))
  return previous?.data?.reportSource || previous?.data
}

export function reportQuery(text) {
  return text.replace(/\b(download|export|generate|create|give|send|me|please|a|an|the|pdf|report|as|file)\b/gi, ' ').replace(/\s+/g, ' ').trim()
}

export function isFollowupReport(text) {
  return isReportRequest(text) && !/\b(stock|inventory|fabric|forecast|demand|production|supplier|shipment|procurement|GAR-\d+|MAT-\d+)\b/i.test(text)
}

const label = (text) => text.replaceAll('_', ' ').replace(/\b\w/g, (c) => c.toUpperCase())

// Built-in PDF fonts need normalized punctuation; unsupported bullets previously
// triggered wide character spacing. Keep all layout measurements on normalized text.
const clean = (value) => String(value ?? 'Not available')
  .replace(/[\u2010-\u2015\u2212]/g, '-')
  .replace(/[\u2018\u2019]/g, "'").replace(/[\u201c\u201d]/g, '"')
  .replace(/[\u2022\u25cf\u25aa]/g, '-').replace(/\u2026/g, '...')
  .replace(/[^\x20-\x7e\xa0-\xff\n]/g, '')
const number = (value) => typeof value === 'number' && Number.isFinite(value)
  ? value.toLocaleString('en-US', { maximumFractionDigits: 2 }) : 'N/A'

// Render the original response snapshot without querying live data.
export async function createChatReport(data) {
  const { jsPDF } = await import('jspdf')
  const pdf = new jsPDF({ unit: 'mm', format: 'a4', compress: true })
  const title = data.title || `${label(data.intent || 'Operations')} Report`
  pdf.setProperties({ title, author: 'OMNI' })
  const colors = { green: '#193e36', gold: '#be8b39', ink: '#243b35', muted: '#687b74', pale: '#f1f6f3', line: '#dce6df' }
  let y = 0
  function text(value, x, top, size = 9, color = colors.ink, bold = false) {
    pdf.setFont('helvetica', bold ? 'bold' : 'normal')
    pdf.setFontSize(size)
    pdf.setTextColor(color)
    pdf.text(clean(value), x, top)
  }
  function rect(x, top, width, height, color) {
    pdf.setFillColor(color)
    pdf.rect(x, top, width, height, 'F')
  }
  function lines(value, width, size = 9) {
    pdf.setFont('helvetica', 'normal')
    pdf.setFontSize(size)
    return pdf.splitTextToSize(clean(value), width)
  }
  function newPage(first = false) {
    if (!first) pdf.addPage()
    rect(0, 0, 210, 3, colors.gold)
    text('OMNI.', 16, 17, 20, colors.green, true)
    text('OPERATIONAL INTELLIGENCE', 112, 15, 8, colors.muted, true)
    text('FACTORY REPORT SERIES', 112, 20, 7, colors.muted)
    rect(16, 25, 178, 0.3, colors.line)
    y = 34
    if (!first) { text(title, 16, y, 10, colors.green, true); y += 10 }
  }
  function ensure(height) { if (y + height > 276) newPage() }
  function write(value) {
    const wrapped = lines(value, 178)
    for (const line of wrapped) {
      ensure(5)
      text(line, 16, y)
      y += 4.8
    }
    y += 3
  }
  function section(name) {
    ensure(20)
    y += 3
    rect(16, y - 3, 2, 5, colors.gold)
    text(name, 21, y + 1, 11, colors.green, true)
    y += 10
  }
  function table(headers, rows, widths) {
    function header() {
      ensure(14)
      rect(16, y, 178, 9, colors.green)
      let x = 16
      headers.forEach((name, i) => { text(name, x + 3, y + 6, 8, '#ffffff', true); x += widths[i] })
      y += 9
    }
    header()
    rows.forEach((row, index) => {
      const cells = row.map((value, i) => lines(value, widths[i] - 6, 8))
      const count = Math.max(...cells.map((cell) => cell.length))
      let offset = 0
      while (offset < count) {
        if (y + 10 > 276) { newPage(); header() }
        const take = Math.min(count - offset, Math.floor((276 - y - 5) / 4))
        const height = take * 4 + 5
        rect(16, y, 178, height, index % 2 ? '#ffffff' : colors.pale)
        let x = 16
        cells.forEach((cell, i) => {
          cell.slice(offset, offset + take).forEach((line, j) => text(line, x + 3, y + 5 + j * 4, 8))
          x += widths[i]
        })
        y += height
        rect(16, y, 178, 0.2, colors.line)
        offset += take
      }
    })
    y += 7
  }
  function metrics(items) {
    ensure(29)
    const width = (178 - (items.length - 1) * 4) / items.length
    items.forEach(([name, value], index) => {
      const x = 16 + index * (width + 4)
      rect(x, y, width, 24, colors.pale)
      rect(x, y, width, 1, colors.gold)
      text(name, x + 4, y + 7, 7, colors.muted, true)
      text(value, x + 4, y + 18, 17, colors.green, true)
    })
    y += 32
  }
  function details(value, name) {
    if (Array.isArray(value)) {
      section(name)
      if (!value.length) write('No records available.')
      value.forEach((item, index) => details(item, `Record ${index + 1}`))
    } else if (value && typeof value === 'object') {
      const scalar = Object.entries(value).filter(([, item]) => item == null || typeof item !== 'object')
      if (scalar.length) {
        section(name)
        table(['FIELD', 'VALUE'], scalar.map(([key, item]) => [label(key), typeof item === 'number' ? number(item) : item]), [55, 123])
      }
      Object.entries(value).filter(([, item]) => item && typeof item === 'object').forEach(([key, item]) => details(item, label(key)))
    } else { write(`${name}: ${value ?? 'Not available'}`) }
  }

  newPage(true)
  const titleLines = lines(title, 166, 23)
  const bannerHeight = 20 + titleLines.length * 9
  rect(16, y, 178, bannerHeight, colors.green)
  text('MANAGEMENT BRIEF', 22, y + 8, 7, '#d8bb83', true)
  titleLines.forEach((line, i) => text(line, 22, y + 20 + i * 9, 23, '#ffffff', true))
  y += bannerHeight + 8
  text(`EXPORTED  ${new Date().toLocaleString('en-GB')}`, 16, y, 7, colors.muted)
  y += 6
  text(`STATUS  ${label(data.status || 'unknown')}   |   SOURCE  ${data.delegated_to || 'Ask Omni'}`, 16, y, 7, colors.muted)
  y += 12

  const inventory = Array.isArray(data.results) && data.results.length > 0
    && data.results.every((item) => item && typeof item === 'object' && 'current_stock' in item && 'material_code' in item)
  if (Array.isArray(data.sections)) {
    write(`Generated: ${data.generated_at || 'Not available'}`)
    section('01 / Executive summary')
    write(data.answer || 'No summary available.')
    if (data.findings?.length) {
      section('02 / Priority findings')
      table(['PRIORITY', 'SOURCE', 'FINDING'], data.findings.map((item) => [item.priority.toUpperCase(), label(item.source), item.text]), [23, 35, 120])
    }
    data.sections.forEach((item, index) => {
      section(`${String(index + 3).padStart(2, '0')} / ${item.title}`)
      write(`Status: ${label(item.status)} | Captured: ${item.captured_at}`)
      write(item.summary)
      if (item.metrics?.length) metrics(item.metrics.map((metric) => [metric.label.toUpperCase(), number(metric.value)]))
      item.tables.forEach((reportTable) => {
        section(reportTable.title)
        if (!reportTable.rows.length) { write('No records returned.'); return }
        const weights = reportTable.columns.map((column) => /note|name|status|destination/i.test(column.key) ? 2 : 1)
        const total = weights.reduce((sum, weight) => sum + weight, 0)
        table(reportTable.columns.map((column) => column.label), reportTable.rows.map((row) => reportTable.columns.map((column) => typeof row[column.key] === 'number' ? number(row[column.key]) : row[column.key])), weights.map((weight) => 178 * weight / total))
      })
    })
    if (data.recommendations?.length) {
      section('Recommended next steps')
      table(['SOURCE', 'ACTION'], data.recommendations.map((item) => [label(item.source), item.text]), [40, 138])
    }
  } else if (inventory) {
    const low = data.results.filter((item) => item.status === 'LOW_STOCK').length
    const out = data.results.filter((item) => item.status === 'OUT_OF_STOCK').length
    metrics([['MATERIALS REVIEWED', String(data.results.length)], ['LOW STOCK', String(low)], ['OUT OF STOCK', String(out)]])
    section('01 / Inventory overview')
    write(`${data.results.length} materials are included in this report. ${low} are flagged as low stock and ${out} as out of stock. Quantities are shown in each material's own unit.`)
    section('02 / Stock register')
    table(['MATERIAL', 'ON HAND', 'REORDER', 'STATUS'], data.results.map((item) => [
      `${item.material_name || item.material_code}\n${item.material_code}`,
      `${number(item.current_stock)}\n${item.unit || 'units'}`,
      `${number(item.reorder_level)}\n${item.unit || 'units'}`,
      label(item.status || 'unknown'),
    ]), [70, 36, 36, 36])
    section('03 / Recommended actions')
    const actions = data.results.filter((item) => item.status === 'LOW_STOCK' || item.status === 'OUT_OF_STOCK')
    if (actions.length) table(['MATERIAL', 'SHORTAGE', 'RECOMMENDATION'], actions.map((item) => [
      `${item.material_name || item.material_code}\n${item.material_code}`,
      `${number(item.shortage)} ${item.unit || 'units'}`,
      item.recommendation || 'Review replenishment requirements.',
    ]), [65, 36, 77])
    else write('No low-stock or out-of-stock flags were returned for these materials.')
    if (data.summary) details(data.summary, 'Additional summary')
  } else {
    const forecast = data.intent === 'demand_forecast' && data.result?.status === 'success' ? data.result : null
    if (forecast) metrics([['NEXT MONTH / UNITS', number(forecast.forecast)], ['HISTORY / MONTHS', number(forecast.history_points)], ['TREND', clean(forecast.trend || 'N/A')]])
    section(data.status === 'error' || data.result?.status === 'error' ? 'Analysis unavailable / Data issues' : 'Executive summary')
    write(data.answer || 'The available analysis is presented below.')
    for (const key of ['summary', 'result', 'results', 'comparisons', 'data', 'risks', 'recommendations']) {
      if (data[key] != null) details(data[key], label(key))
    }
  }
  section('Report notes')
  write(data.notes || 'Prepared from the saved Ask Omni response. Figures reflect that conversation snapshot and have not been refreshed at export. Missing values are marked N/A. Forecasts, where present, are estimates rather than observed demand.')
  if (data.summary_method) write(`Summary method: ${data.summary_method}. Report ID: ${data._id || 'Not available'}`)
  const pages = pdf.getNumberOfPages()
  for (let page = 1; page <= pages; page++) {
    pdf.setPage(page)
    rect(16, 283, 178, 0.3, colors.line)
    text('OMNI / FACTORY INTELLIGENCE', 16, 289, 7, colors.muted, true)
    text(`PAGE ${page} OF ${pages}`, 166, 289, 7, colors.muted)
  }
  return pdf
}

export async function createChatReportPreview(data) {
  const pdf = await createChatReport(data)
  const name = (data.intent || 'operations').replace(/[^a-z0-9_-]/gi, '-')
  return { pdf, filename: `OMNI-${name}-report.pdf`, title: data.title || `${label(data.intent || 'Operations')} Report` }
}

export async function downloadChatReport(data) {
  const report = await createChatReportPreview(data)
  await report.pdf.save(report.filename, { returnPromise: true })
}
