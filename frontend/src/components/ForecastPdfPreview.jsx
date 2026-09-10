import { useEffect, useRef, useState } from 'react'

export default function ForecastPdfPreview({ report, onClose }) {
  const dialog = useRef(null)
  const frame = useRef(null)
  const [url, setUrl] = useState('')
  const [ready, setReady] = useState(false)
  const [error, setError] = useState('')

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
    try {
      await report.pdf.save(report.filename, { returnPromise: true })
    } catch {
      setError('Unable to download the PDF. Please try again.')
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

  return <dialog ref={dialog} onCancel={onClose} aria-labelledby="pdf-preview-title" className="fixed inset-0 m-0 h-[100dvh] max-h-none w-screen max-w-none overflow-hidden rounded-none border-0 bg-slate-50 p-0 backdrop:bg-slate-950/60">
    <div className="flex h-full min-h-0 flex-col">
      <header className="flex shrink-0 flex-wrap items-center justify-between gap-3 border-b border-slate-200 bg-white p-4 sm:px-6">
        <div><h2 id="pdf-preview-title" className="text-lg font-bold text-slate-900">Forecast PDF preview</h2><p className="mt-1 text-xs text-slate-500">{report.filename} · A4 · 1 page</p></div>
        <div className="flex items-center gap-2">
          <button type="button" onClick={download} className="rounded-lg bg-emerald-800 px-4 py-2 text-sm font-semibold text-white hover:bg-emerald-900 focus-visible:outline-emerald-600">Download PDF</button>
          <button type="button" disabled={!ready} onClick={print} className="rounded-lg border border-slate-200 px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50 disabled:opacity-40">Print</button>
          <button type="button" onClick={onClose} aria-label="Close PDF preview" className="rounded-lg px-3 py-2 text-sm font-semibold text-slate-500 hover:bg-slate-100">Close</button>
        </div>
      </header>
      {error && <p role="alert" className="px-6 py-3 text-sm text-amber-800">{error}</p>}
      {url && <iframe ref={frame} title="Demand forecast PDF" src={`${url}#page=1&view=Fit&navpanes=0`} onLoad={() => setReady(true)} className="min-h-0 w-full flex-1 basis-0 border-0" />}
      <p className="shrink-0 px-6 py-3 text-xs text-slate-500">Download saves the PDF directly. Print opens your browser’s print dialog.</p>
    </div>
  </dialog>
}
