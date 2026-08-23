const API_BASE_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

export async function fetchSystemHealth() {
  const response = await fetch(`${API_BASE_URL}/health`)

  if (!response.ok) {
    throw new Error(`Health request failed: ${response.status}`)
  }

  return response.json()
}
