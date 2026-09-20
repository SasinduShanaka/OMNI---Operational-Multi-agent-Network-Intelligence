import { useEffect, useRef, useState } from 'react'

export default function ForecastPdfPreview({ report, onClose }) {
  const dialog = useRef(null)
  const frame = useRef(null)
  const [url, setUrl] = useState('')
  const [ready, setReady] = useState(false)
  const [error, setError] = useState('')
  const [view, setView] = useState('FitH')
  const [downloading, setDownloading] = useState(false)

  useEffect(() => {
    const objectUrl = URL.createObjectURL(report.pdf.output('blob'))
    setUrl(objectUrl)
    dialog.current.showModal()
    const previousOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    return () => {
      URL.revokeObjectURL(objectUrl)
      document.body.style.overflow = previousOverflow
    }
  }, [report])

  async function download() {
    setError('')
    setDownloading(true)
    try {
      await report.pdf.save(report.filename, { returnPromise: true })
    } catch {
      setError('Unable to download the PDF. Please try again.')
    } finally {
      setDownloading(false)
    }
  }

  function print() {
    setError('')
    try {
      frame.current.contentWindow.focus()
      frame.current.contentWindow.print()
    } catch {
      setError('Use the PDF viewer’s print control, or download the report and print it from your PDF reader.')
    }
  }

  return <dialog ref={dialog} onCancel={onClose} aria-labelledby="pdf-preview-title" className="fixed inset-0 m-0 h-[100dvh] max-h-none w-screen max-w-none overflow-hidden rounded-none border-0 bg-[#eef2f0] p-0 backdrop:bg-slate-950/60">
    <div className="flex h-full min-h-0 flex-col">
      <header className="flex shrink-0 flex-wrap items-center justify-between gap-4 border-b border-slate-200 bg-white px-5 py-4 sm:px-8">
        <div className="flex items-center gap-4"><span aria-hidden="true" className="grid h-11 w-11 place-items-center rounded-xl bg-emerald-900 text-sm font-bold text-white">O.</span><div><p className="text-[9px] font-bold uppercase tracking-[.22em] text-emerald-700">OMNI / Report studio</p><h2 id="pdf-preview-title" className="mt-1 text-lg font-bold tracking-tight text-slate-900">{report.title || 'Demand forecast report'}</h2></div></div>
        <div className="flex flex-wrap items-center gap-2">
          <button type="button" disabled={!ready} onClick={print} className="rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-xs font-semibold text-slate-700 transition hover:bg-slate-50 disabled:opacity-40">Print report</button>
          <button type="button" disabled={downloading} onClick={download} className="rounded-xl bg-emerald-800 px-5 py-2.5 text-xs font-semibold text-white shadow-sm transition hover:bg-emerald-900 disabled:opacity-50">{downloading ? 'Downloading...' : 'Download PDF'}</button>
          <button type="button" onClick={onClose} className="ml-1 rounded-xl px-3 py-2.5 text-xs font-semibold text-slate-500 transition hover:bg-slate-100">Close preview</button>
        </div>
      </header>
      {error && <p role="alert" className="shrink-0 border-b border-amber-200 bg-amber-50 px-6 py-3 text-sm text-amber-800">{error}</p>}
      <div className="flex min-h-0 flex-1">
        <aside className="hidden w-64 shrink-0 flex-col border-r border-slate-200 bg-white p-6 lg:flex">
          <p className="text-[10px] font-bold uppercase tracking-[.18em] text-slate-400">Your document</p>
          <div className="mt-5 rounded-2xl border border-emerald-100 bg-emerald-50/50 p-5"><div aria-hidden="true" className="mx-auto flex h-32 w-24 flex-col gap-2 rounded border border-slate-200 bg-white p-3 shadow-sm"><span className="text-[8px] font-bold text-emerald-900">OMNI.</span><span className="h-6 rounded-sm bg-emerald-900"/><span className="h-1 w-3/4 bg-slate-200"/><span className="h-1 bg-slate-100"/><span className="mt-1 h-6 rounded-sm bg-emerald-50"/><span className="h-1 bg-slate-100"/></div><p className="mt-4 text-center text-xs font-semibold text-emerald-900">{report.title || 'Forecast summary'}</p><p className="mt-1 text-center text-[10px] text-slate-500">PDF preview on the right</p></div>
          <p className="mt-5 break-words text-xs font-semibold leading-5 text-slate-700">{report.filename}</p>
          <dl className="mt-5 space-y-3 text-xs"><div className="flex justify-between"><dt className="text-slate-400">Format</dt><dd className="font-medium text-slate-700">PDF document</dd></div><div className="flex justify-between"><dt className="text-slate-400">Paper</dt><dd className="font-medium text-slate-700">A4 portrait</dd></div><div className="flex justify-between"><dt className="text-slate-400">Pages</dt><dd className="font-medium text-slate-700">{report.pdf.getNumberOfPages()}</dd></div></dl>
          <div className="mt-auto border-t border-slate-100 pt-5"><p className="text-xs font-semibold text-slate-700">Ready to share</p><p className="mt-2 text-xs leading-5 text-slate-500">Download saves the report directly. Use Print report for a paper copy.</p></div>
        </aside>
        <div className="flex min-h-0 min-w-0 flex-1 flex-col">
          <div className="flex shrink-0 flex-wrap items-center justify-between gap-3 border-b border-slate-200/80 bg-[#f7f9f8] px-5 py-3"><span className="text-xs font-medium text-slate-500">Document preview</span><div className="flex rounded-lg border border-slate-200 bg-white p-1" role="group" aria-label="PDF display size">{[['FitH', 'Fit width'], ['Fit', 'Full page']].map(([value, label]) => <button type="button" key={value} aria-pressed={view === value} onClick={() => { setReady(false); setView(value) }} disabled={view === value} className={`rounded-md px-3 py-1.5 text-xs font-semibold ${view === value ? 'bg-emerald-50 text-emerald-800' : 'text-slate-500 hover:bg-slate-50'}`}>{label}</button>)}</div></div>
          {url && <iframe key={view} ref={frame} title={report.title ? `${report.title} PDF preview` : 'Demand forecast PDF'} src={`${url}#page=1&view=${view}&toolbar=0&navpanes=0`} onLoad={() => setReady(true)} className="min-h-0 w-full flex-1 basis-0 border-0 bg-[#eef2f0]" />}
          <footer className="flex shrink-0 justify-between border-t border-slate-200 bg-white px-5 py-2.5 text-[10px] text-slate-400"><span>{report.title ? 'OMNI factory intelligence' : 'OMNI demand intelligence'}</span><span>A4 / {report.pdf.getNumberOfPages()} {report.pdf.getNumberOfPages() === 1 ? 'page' : 'pages'}</span></footer>
        </div>
      </div>
    </div>
  </dialog>
}
