import { API_BASE_URL, apiFetch, responseData, setAccessToken } from './http'

async function authenticate(path, payload) {
  const response = await apiFetch(`${API_BASE_URL}/auth/${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  const result = await responseData(response, `Unable to ${path}.`)
  setAccessToken(null)
  return result.user
}

export const authApi = {
  login: (email, password) => authenticate('login', { email, password }),
  register: (name, email, password) => authenticate('register', { name, email, password }),
  currentUser: async () => {
    const response = await apiFetch(`${API_BASE_URL}/auth/me`)
    return (await responseData(response, 'Unable to restore your session.')).user
  },
  logout: async () => {
    try {
      await apiFetch(`${API_BASE_URL}/auth/logout`, { method: 'POST' })
    } finally {
      setAccessToken(null)
    }
  },
}
