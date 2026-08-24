const API_BASE_URL =
  import.meta.env.VITE_API_URL ?? 'http://localhost:8000'


// ----------------------------------------
// Backend health
// ----------------------------------------

export async function fetchSystemHealth() {
  const response = await fetch(`${API_BASE_URL}/`)

  if (!response.ok) {
    throw new Error(`Health request failed: ${response.status}`)
  }

  return response.json()
}


// ----------------------------------------
// Get complete inventory status
// ----------------------------------------

export async function fetchInventoryStatus() {
  const response = await fetch(`${API_BASE_URL}/inventory/status`)

  if (!response.ok) {
    throw new Error(`Inventory request failed: ${response.status}`)
  }

  return response.json()
}


// ----------------------------------------
// Ask Operations Agent
// ----------------------------------------

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
    throw new Error(`Operations request failed: ${response.status}`)
  }

  return response.json()
}


// ----------------------------------------
// Check a specific inventory requirement
// ----------------------------------------

export async function checkInventoryRequirement(
  materialCode,
  requiredQuantity
) {
  const response = await fetch(
    `${API_BASE_URL}/agents/inventory/check`,
    {
      method: 'POST',

      headers: {
        'Content-Type': 'application/json'
      },

      body: JSON.stringify({
        material_code: materialCode,
        required_quantity: requiredQuantity
      })
    }
  )

  if (!response.ok) {
    throw new Error(`Inventory check failed: ${response.status}`)
  }

  return response.json()
}