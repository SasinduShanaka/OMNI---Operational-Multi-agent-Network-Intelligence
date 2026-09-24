export const API_BASE_URL = import.meta.env.VITE_API_URL ?? `http://${window.location.hostname}:8000`

const TOKEN_KEY = 'omni_access_token'

export function getAccessToken() {
  return null
}

export function setAccessToken() {
  // Remove tokens left by older versions; new sessions use an HTTP-only cookie.
  window.localStorage.removeItem(TOKEN_KEY)
}

export async function apiFetch(input, options = {}) {
  const headers = new Headers(options.headers || {})

  const response = await fetch(input, { ...options, headers, credentials: 'include' })
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
