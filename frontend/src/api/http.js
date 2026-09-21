export const API_BASE_URL = import.meta.env.VITE_API_URL ?? 'http://127.0.0.1:8000'

const TOKEN_KEY = 'omni_access_token'

export function getAccessToken() {
  return window.localStorage.getItem(TOKEN_KEY)
}

export function setAccessToken(token) {
  if (token) window.localStorage.setItem(TOKEN_KEY, token)
  else window.localStorage.removeItem(TOKEN_KEY)
}

export async function apiFetch(input, options = {}) {
  const token = getAccessToken()
  const headers = new Headers(options.headers || {})
  if (token) headers.set('Authorization', `Bearer ${token}`)

  const response = await fetch(input, { ...options, headers })
  const url = String(input)
  if (response.status === 401 && !url.includes('/auth/login') && !url.includes('/auth/register')) {
    setAccessToken(null)
    window.dispatchEvent(new CustomEvent('omni:session-expired'))
  }
  return response
}

export async function responseData(response, fallback) {
  let data = null
  try {
    data = await response.json()
  } catch {
    // Preserve the HTTP fallback for non-JSON server errors.
  }
  if (!response.ok) {
    const detail = data?.detail
    const message = Array.isArray(detail)
      ? detail.map((item) => item.msg).join(' ')
      : typeof detail === 'string' ? detail : fallback
    throw new Error(message || fallback)
  }
  return data
}
