import { useState } from 'react'
import overview from '../assets/overview.png'
import { authApi } from '../api/authApi'

const field = 'mt-1.5 w-full rounded-lg border border-slate-300 bg-white px-3.5 py-3 text-sm text-slate-900 outline-none transition focus:border-blue-600 focus:ring-2 focus:ring-blue-600/15'

export default function AuthPage({ onAuthenticated }) {
  const [mode, setMode] = useState('login')
  const [form, setForm] = useState({ name: '', email: '', password: '', confirmPassword: '' })
  const [showPassword, setShowPassword] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  function update(name, value) {
    setForm((current) => ({ ...current, [name]: value }))
  }

  function changeMode(nextMode) {
    setMode(nextMode)
    setError('')
    setShowPassword(false)
  }

  async function submit(event) {
    event.preventDefault()
    setError('')
    if (mode === 'register' && form.password !== form.confirmPassword) {
      setError('Passwords do not match.')
      return
    }
    setBusy(true)
    try {
      const user = mode === 'login'
        ? await authApi.login(form.email, form.password)
        : await authApi.register(form.name, form.email, form.password)
      onAuthenticated(user)
    } catch (requestError) {
      setError(requestError.message || 'Authentication failed. Please try again.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <main className="relative min-h-[100dvh] overflow-y-auto bg-slate-950">
      <img src={overview} alt="" className="absolute inset-0 h-full w-full object-cover opacity-30" />
      <div className="absolute inset-0 bg-slate-950/75" />

      <div className="relative grid min-h-[100dvh] items-center gap-10 px-5 py-8 lg:grid-cols-[minmax(0,1fr)_420px] lg:px-16 xl:px-24">
        <section className="max-w-2xl text-white">
          <div className="flex items-center gap-3">
            <div className="flex h-11 w-11 items-center justify-center rounded-lg bg-blue-600 text-base font-bold shadow-lg shadow-blue-950/30">O</div>
            <p className="text-lg font-semibold">OMNI management</p>
          </div>
          <h1 className="mt-8 text-4xl font-bold leading-tight sm:text-5xl">Operational intelligence for your factory.</h1>
          <p className="mt-4 max-w-xl text-base leading-7 text-slate-300">Access inventory, demand, production planning, supplier operations, and Ask Omni from one secure workspace.</p>
        </section>

        <section className="w-full rounded-lg border border-white/15 bg-white p-6 shadow-2xl sm:p-8" aria-labelledby="auth-title">
          <div className="mb-6 flex border-b border-slate-200" role="tablist" aria-label="Account access">
            {['login', 'register'].map((item) => (
              <button key={item} type="button" role="tab" aria-selected={mode === item} onClick={() => changeMode(item)} className={`flex-1 border-b-2 px-3 py-3 text-sm font-semibold capitalize ${mode === item ? 'border-blue-600 text-blue-700' : 'border-transparent text-slate-500 hover:text-slate-800'}`}>
                {item === 'login' ? 'Sign in' : 'Create account'}
              </button>
            ))}
          </div>

          <h2 id="auth-title" className="text-2xl font-bold text-slate-900">{mode === 'login' ? 'Welcome back' : 'Create your OMNI account'}</h2>
          <p className="mt-2 text-sm text-slate-500">{mode === 'login' ? 'Sign in to continue to factory operations.' : 'Register to access the management workspace.'}</p>

          <form className="mt-6 space-y-4" onSubmit={submit}>
            {mode === 'register' && <label className="block text-sm font-medium text-slate-700">Full name
              <input className={field} autoComplete="name" value={form.name} onChange={(event) => update('name', event.target.value)} required minLength={2} maxLength={80} />
            </label>}
            <label className="block text-sm font-medium text-slate-700">Email address
              <input className={field} type="email" autoComplete="email" value={form.email} onChange={(event) => update('email', event.target.value)} required maxLength={254} />
            </label>
            <label className="block text-sm font-medium text-slate-700">Password
              <span className="relative mt-1.5 block">
                <input className={`${field} mt-0 pr-16`} type={showPassword ? 'text' : 'password'} autoComplete={mode === 'login' ? 'current-password' : 'new-password'} value={form.password} onChange={(event) => update('password', event.target.value)} required minLength={mode === 'register' ? 8 : 1} maxLength={128} />
                <button type="button" onClick={() => setShowPassword((value) => !value)} className="absolute right-3 top-1/2 -translate-y-1/2 text-xs font-semibold text-blue-700">{showPassword ? 'Hide' : 'Show'}</button>
              </span>
              {mode === 'register' && <span className="mt-1.5 block text-xs font-normal text-slate-500">At least 8 characters, including a letter and a number.</span>}
            </label>
            {mode === 'register' && <label className="block text-sm font-medium text-slate-700">Confirm password
              <input className={field} type={showPassword ? 'text' : 'password'} autoComplete="new-password" value={form.confirmPassword} onChange={(event) => update('confirmPassword', event.target.value)} required minLength={8} maxLength={128} />
            </label>}

            {error && <p role="alert" className="rounded-lg border border-red-200 bg-red-50 px-3 py-2.5 text-sm text-red-700">{error}</p>}

            <button type="submit" disabled={busy} className="w-full rounded-lg bg-blue-700 px-4 py-3 text-sm font-semibold text-white transition hover:bg-blue-800 disabled:cursor-not-allowed disabled:opacity-60">
              {busy ? (mode === 'login' ? 'Signing in...' : 'Creating account...') : (mode === 'login' ? 'Sign in' : 'Create account')}
            </button>
          </form>
        </section>
      </div>
    </main>
  )
}
