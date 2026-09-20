import test from 'node:test'
import assert from 'node:assert/strict'
import { createChatReport, isManagementReportRequest, isReportNavigationRequest, reportSource, managementReportScope } from './chatReports.js'

test('inventory reports paginate large registers and long recommendations', async () => {
  const results = Array.from({ length: 75 }, (_, index) => ({
    material_code: `FAB-${index}`, material_name: 'Cotton fabric',
    current_stock: 3200, reorder_level: 3500, shortage: 300,
    status: 'LOW_STOCK', unit: 'meters',
    recommendation: index === 0 ? 'Review replenishment. '.repeat(350) : 'Consider replenishment',
  }))
  const pdf = await createChatReport({ intent: 'inventory_list', status: 'success', results })
  assert.ok(pdf.getNumberOfPages() > 3)
  assert.ok(pdf.getNumberOfPages() < 30)
  assert.ok(pdf.output('arraybuffer').byteLength > 3000)
})

test('failed forecasts and empty inventory still export valid reports', async () => {
  for (const data of [
    { intent: 'demand_forecast', status: 'error', answer: 'Missing months — correct records • retry.', result: { sku: 'GAR-003', status: 'error', forecast: null } },
    { intent: 'inventory_list', status: 'success', results: [], answer: 'No materials found.' },
  ]) {
    const pdf = await createChatReport(data)
    assert.ok(pdf.getNumberOfPages() >= 1)
    assert.ok(pdf.output().startsWith('%PDF-'))
  }
})

test('management reports render combined sections and saved metadata', async () => {
  const pdf = await createChatReport({
    _id: 'saved-1', title: 'Factory management report', status: 'partial', intent: 'management_report',
    answer: 'Inventory is available; forecast is blocked.', generated_at: '2026-09-20T00:00:00Z',
    sections: [{ title: 'Inventory', status: 'success', captured_at: '2026-09-20T00:00:00Z', summary: 'One material.',
      metrics: [{ label: 'Materials', value: 1 }], tables: [{ title: 'Stock', columns: [{ key: 'name', label: 'Material' }, { key: 'stock', label: 'On hand' }], rows: [{ name: 'Cotton', stock: 25 }] }] }],
    findings: [{ source: 'forecast', priority: 'high', text: 'Missing months' }],
    recommendations: [{ source: 'forecast', text: 'Correct demand records.' }],
    notes: 'Current-state snapshot.', summary_method: 'Evidence-based rules',
  })
  assert.ok(pdf.getNumberOfPages() >= 1)
  assert.ok(pdf.output().startsWith('%PDF-'))
})

test('chat routes management, schedules, and download follow-ups separately', () => {
  assert.equal(isManagementReportRequest('Create a combined management report'), true)
  assert.equal(isManagementReportRequest('How much fabric is available?'), false)
  assert.equal(isManagementReportRequest('Create inventory and production report'), true)
  assert.deepEqual(managementReportScope('Create inventory and production report').domains, ['inventory', 'production'])
  assert.equal(isReportNavigationRequest('Schedule monthly reports'), true)
  assert.equal(isReportNavigationRequest('Show saved reports'), true)
  const source = { intent: 'inventory_list', results: [] }
  assert.equal(reportSource([{ type: 'agent', data: source }, { type: 'agent', data: { intent: 'report_navigation' } }]), source)
})
