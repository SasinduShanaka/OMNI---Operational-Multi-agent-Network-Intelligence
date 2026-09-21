import React, { useState } from 'react'

const API_BASE_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

export default function SystemReadiness() {
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  async function check() {
    setLoading(true)
    setError('')
    try {
      const response = await fetch(`${API_BASE_URL}/readiness`, { signal: AbortSignal.timeout(12000) })
      if (!response.ok) throw new Error('Service status is unavailable. Check that the backend is running.')
      setResult(await response.json())
    } catch (err) {
      setError(err.name === 'TimeoutError' ? 'The service check timed out. Check the backend and database connection.' : err.message)
    } finally {
      setLoading(false)
    }
  }

  return <details className="mb-4 border-y border-slate-200 py-3 text-xs">
    <summary className="cursor-pointer font-medium text-slate-600">Service status</summary>
    <div className="mt-3">
      <button type="button" disabled={loading} onClick={check} className="rounded-lg border border-slate-300 px-3 py-2 font-medium hover:bg-white disabled:opacity-50">{loading ? 'Checking services...' : 'Check services'}</button>
      {error && <p role="alert" className="mt-2 text-red-700">{error}</p>}
      {result && <>
        <p className="mt-3 text-slate-500">Checked {new Date(result.checked_at).toLocaleString()}</p>
        <dl className="mt-2 grid gap-x-6 sm:grid-cols-2">
          {result.checks.map((item) => <div key={item.name} className="border-t border-slate-200 py-3">
            <dt className="flex flex-wrap justify-between gap-2 font-semibold text-slate-800">{item.name}<span className={item.status === 'ready' ? 'text-emerald-700' : item.status === 'configured' ? 'text-slate-600' : 'text-amber-800'}>{item.status.replaceAll('_', ' ')}</span></dt>
            <dd className="mt-1 text-slate-600">{item.source && `${item.source}: `}{item.message}</dd>
          </div>)}
        </dl>
      </>}
    </div>
  </details>
}
