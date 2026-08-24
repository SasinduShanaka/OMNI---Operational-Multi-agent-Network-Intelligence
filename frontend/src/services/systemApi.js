const API_BASE_URL =
  import.meta.env.VITE_API_URL ?? 'http://localhost:8000'


// ============================================================
// SYSTEM HEALTH
// ============================================================

export async function fetchSystemHealth() {

  const response = await fetch(`${API_BASE_URL}/`)

  if (!response.ok) {
    throw new Error(`Health request failed: ${response.status}`)
  }

  return response.json()
}


// ============================================================
// OPERATIONS AGENT
// ============================================================

export async function askOperationsAgent(message) {

  const response = await fetch(`${API_BASE_URL}/ask`, {

    method: 'POST',

    headers: {
      'Content-Type': 'application/json'
    },

    body: JSON.stringify({
      message: message
    })

  })


  if (!response.ok) {

    throw new Error(
      `Operations Agent request failed: ${response.status}`
    )

  }


  return response.json()
}