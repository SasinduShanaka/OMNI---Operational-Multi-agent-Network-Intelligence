import React from 'react'

function number(value) {
  return value === null || value === undefined || value === '' || !Number.isFinite(Number(value))
    ? 'Not available'
    : Number(value).toLocaleString(undefined, { maximumFractionDigits: 2 })
}

export function MaterialEvidence({ result }) {
  const materials = (result.materials || []).map((item) => {
    const request = item.request || item
    const response = item.response || item
    return {
      ...request, ...response,
      status: response.inventory_status || response.status,
      unit: response.unit || request.unit || '',
      shortage: response.shortage ?? (response.available_quantity != null && request.required_quantity != null
        ? Math.max(0, request.required_quantity - response.available_quantity) : null),
    }
  })

  return (
    <section className="min-w-0 border-t border-slate-200 py-4">
      <h4 className="text-sm font-semibold text-slate-900">Materials required</h4>
      <p className="mt-1 text-xs text-slate-500">
        {result.product_name || result.sku} | {number(result.required_quantity ?? result.quantity)} finished units
      </p>
      {materials.length ? (
        <div className="mt-3 overflow-x-auto" tabIndex={0} aria-label="Bill of materials and stock availability">
          <table className="w-full min-w-[610px] text-left text-xs">
            <thead className="border-y border-slate-200 bg-slate-50 text-slate-600">
              <tr>{['Material', 'Per unit', 'Required', 'Available', 'Shortage', 'Stock check'].map((label) => (
                <th key={label} scope="col" className="px-3 py-2 font-medium">{label}</th>
              ))}</tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {materials.map((item, index) => (
                <tr key={`${item.material_code}-${index}`}>
                  <th scope="row" className="px-3 py-3 font-medium text-slate-800">
                    {item.material_name || item.material_code}
                    <span className="mt-1 block font-normal text-slate-500">{item.material_code} | {item.unit}</span>
                  </th>
                  <td className="px-3 py-3 tabular-nums">{number(item.qty_per_unit)}</td>
                  <td className="px-3 py-3 tabular-nums">{number(item.required_quantity)}</td>
                  <td className="px-3 py-3 tabular-nums">{number(item.available_quantity)}</td>
                  <td className={`px-3 py-3 tabular-nums ${item.shortage > 0 ? 'font-semibold text-red-700' : ''}`}>{number(item.shortage)}</td>
                  <td className="px-3 py-3">{item.status === 'SHORTAGE' ? 'Shortage' : item.status === 'SUFFICIENT' ? 'Available' : 'Needs review'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : <p className="mt-3 text-sm text-amber-800">{result.message || 'No bill of materials was returned. Availability has not been verified.'}</p>}
    </section>
  )
}

const verdicts = {
  FEASIBLE: ['Can fulfill with current resources', 'bg-emerald-50 text-emerald-800 border-emerald-200'],
  AT_RISK: ['At risk: changes are needed', 'bg-amber-50 text-amber-900 border-amber-200'],
  INFEASIBLE: ['Cannot fulfill as currently planned', 'bg-red-50 text-red-800 border-red-200'],
}

export default function PlanningEvidence({ result, setActivePage }) {
  const production = result.production || result
  const capacity = production.capacity || {}
  const forecast = result.forecast
  const [verdict, tone] = verdicts[production.status] || ['Cannot confirm yet', 'bg-amber-50 text-amber-900 border-amber-200']
  const options = production.reallocation?.options || []
  const factors = production.factors || []

  return (
    <section aria-label="Order feasibility evidence" className="mt-4 min-w-0 text-sm text-slate-700">
      <div className={`border-l-4 p-4 ${tone}`}>
        <h3 className="text-base font-semibold">{verdict}</h3>
        <p className="mt-1">{production.product_name || result.product_name || result.sku} | {number(production.required_quantity ?? result.required_quantity)} units | Due {production.required_date || result.required_date || 'date needed'}</p>
        {production.checked_at && <p className="mt-2 text-xs">Checked {new Date(production.checked_at).toLocaleString()} | {production.data_source || 'Factory records'}</p>}
      </div>

      <section className="py-4">
        <h4 className="text-sm font-semibold text-slate-900">Capacity and timing</h4>
        <dl className="mt-3 grid grid-cols-2 gap-x-5 gap-y-4 lg:grid-cols-3">
          {[
            ['Production line', capacity.line_name || capacity.line_id || 'Not available'],
            ['Working days remaining', number(capacity.working_days)],
            ['Spare capacity / day', number(capacity.spare_capacity_per_day)],
            ['Can produce by deadline', number(capacity.producible_quantity)],
            ['Capacity shortfall', number(capacity.shortfall)],
            ['At full line capacity', number(capacity.producible_at_full_capacity)],
          ].map(([label, value]) => <div key={label} className="min-w-0"><dt className="text-xs text-slate-500">{label}</dt><dd className="mt-1 break-words font-medium text-slate-900">{value}</dd></div>)}
        </dl>
        {capacity.message && <p className="mt-3 text-xs text-slate-600">{capacity.message}</p>}
      </section>

      <MaterialEvidence result={production} />

      {forecast && <section className="border-t border-slate-200 py-4">
        <h4 className="text-sm font-semibold text-slate-900">Demand outlook</h4>
        <p className="mt-2">{forecast.status === 'success'
          ? `${number(forecast.forecast)} units next period. Trend: ${forecast.trend || 'not available'}.`
          : forecast.message || 'Demand forecast is unavailable for this product.'}</p>
      </section>}

      {factors.length > 0 && <details className="border-t border-slate-200 py-4" open={production.status !== 'FEASIBLE'}>
        <summary className="cursor-pointer font-semibold text-slate-900">Reasons and supporting evidence</summary>
        <ul className="mt-3 list-disc space-y-2 pl-5 text-sm">{factors.map((factor, index) => <li key={index}>{factor}</li>)}</ul>
      </details>}

      <section className="border-t border-slate-200 py-4">
        <h4 className="text-sm font-semibold text-slate-900">Next steps</h4>
        <ul className="mt-3 list-disc space-y-2 pl-5">
          {production.status === 'FEASIBLE' && <li>The check passed. Stock has not been reserved and no production schedule has been changed.</li>}
          {production.status === 'NO_BOM' && <li>Add a bill of materials for this product, then check the order again.</li>}
          {production.blocking_materials?.length > 0 && <li>Review the material shortages and purchase-order results below. Supplier delivery must leave enough time for production.</li>}
          {capacity.shortfall > 0 && <li>Review the capacity gap with the production manager, or agree on a smaller quantity or later delivery date.</li>}
          {!verdicts[production.status] && production.status !== 'NO_BOM' && <li>{production.message || 'Provide the missing product, quantity, date, or production setup before committing to the order.'}</li>}
          {options.length > 0 && <li>Alternative lines are proposals only. A manager must review their suitability and approve any schedule change.</li>}
        </ul>
        {options.length > 0 && <div className="mt-3 divide-y divide-slate-100">
          {options.map((option) => <div key={option.line_id} className="flex flex-wrap justify-between gap-2 py-2 text-xs">
            <span className="font-medium">{option.line_name || option.line_id}</span>
            <span>Up to {number(option.absorbable_quantity)} units | {option.requires_retooling ? 'Retooling needed' : 'Product supported'} | Not applied</span>
          </div>)}
        </div>}
        <div className="mt-4 flex flex-wrap gap-3">
          <button type="button" onClick={() => setActivePage('production')} className="rounded-lg border border-slate-300 px-3 py-2 text-xs font-medium hover:bg-slate-50">Review line planning</button>
          <button type="button" onClick={() => setActivePage('inventory')} className="rounded-lg border border-slate-300 px-3 py-2 text-xs font-medium hover:bg-slate-50">Review inventory</button>
        </div>
      </section>
    </section>
  )
}
