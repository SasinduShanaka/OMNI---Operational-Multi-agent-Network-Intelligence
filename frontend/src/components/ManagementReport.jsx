import { reportDate } from './reportFormatting'

const display = (value) => value == null ? 'N/A' : typeof value === 'number'
  ? value.toLocaleString('en-US', { maximumFractionDigits: 2 }) : String(value).replaceAll('_', ' ')

export function ReportStatus({ status }) {
  return <span className={`rounded-full px-3 py-1 text-xs font-semibold ${status === 'success' ? 'bg-emerald-100 text-emerald-800' : status === 'error' ? 'bg-red-100 text-red-800' : 'bg-amber-100 text-amber-800'}`}>{display(status)}</span>
}

export default function ManagementReport({ report, compact = false }) {
  return <article className="space-y-5">
    <div className="rounded-2xl bg-[#193e36] p-6 text-white">
      <p className="text-xs font-semibold uppercase tracking-widest text-[#dfbf83]">OMNI / Management brief</p>
      <div className="mt-3 flex flex-wrap items-center justify-between gap-3"><h2 className="text-2xl font-semibold">{report.title}</h2><ReportStatus status={report.status} /></div>
      <p className="mt-3 text-xs text-emerald-100">Generated {reportDate(report.generated_at)} · Sri Lanka time</p>
      <p className="mt-4 text-sm leading-7 text-emerald-50">{report.answer}</p>
    </div>
    {report.findings?.length > 0 && <section className="rounded-xl border border-amber-200 bg-amber-50 p-5">
      <h3 className="font-semibold text-slate-900">Needs attention</h3>
      <ul className="mt-3 space-y-3">{report.findings.map((item, index) => <li key={index} className="text-sm text-slate-700"><span className="mr-2 font-semibold uppercase text-amber-800">{item.priority}</span>{item.text}<span className="ml-2 text-xs text-slate-500">({display(item.source)})</span></li>)}</ul>
    </section>}
    {report.sections?.map((section) => <details key={section.key} open={!compact} className="rounded-xl border border-slate-200 bg-white p-5">
      <summary className="cursor-pointer font-semibold text-slate-900">{section.title} <span className="ml-3"><ReportStatus status={section.status} /></span></summary>
      <p className="mt-4 text-sm leading-6 text-slate-600">{section.summary}</p>
      <p className="mt-1 text-xs text-slate-400">Captured {reportDate(section.captured_at)}</p>
      <div className="mt-4 grid gap-3 sm:grid-cols-3">{section.metrics.map((metric) => <div key={metric.label} className="rounded-lg border-t-2 border-[#be8b39] bg-[#f1f6f3] p-4"><p className="text-xs text-slate-500">{metric.label}</p><p className="mt-2 text-2xl font-semibold text-[#193e36]">{display(metric.value)}</p></div>)}</div>
      {section.tables.map((table, index) => <div key={index} className="mt-5">
        <h4 className="mb-2 text-sm font-semibold text-slate-800">{table.title}</h4>
        <div className="overflow-x-auto rounded-lg border border-slate-200"><table className="w-full text-left text-xs">
          <thead className="bg-[#193e36] text-white"><tr>{table.columns.map((column) => <th key={column.key} className="px-3 py-3">{column.label}</th>)}</tr></thead>
          <tbody>{table.rows.map((row, rowIndex) => <tr key={rowIndex} className="border-t border-slate-100 odd:bg-[#f1f6f3]">{table.columns.map((column) => <td key={column.key} className="min-w-20 max-w-md px-3 py-3 align-top text-slate-700">{display(row[column.key])}</td>)}</tr>)}</tbody>
        </table>{!table.rows.length && <p className="p-4 text-sm text-slate-500">No records returned.</p>}</div>
      </div>)}
    </details>)}
    {report.recommendations?.length > 0 && <section className="rounded-xl border border-slate-200 bg-white p-5"><h3 className="font-semibold text-slate-900">Recommended next steps</h3><ol className="mt-3 list-decimal space-y-3 pl-5 text-sm leading-6 text-slate-700">{report.recommendations.map((item, index) => <li key={index}>{item.text}<span className="ml-2 text-xs text-slate-500">({display(item.source)})</span></li>)}</ol></section>}
    <p className="text-xs leading-5 text-slate-500">{report.notes} Summary method: {report.summary_method}.</p>
  </article>
}
