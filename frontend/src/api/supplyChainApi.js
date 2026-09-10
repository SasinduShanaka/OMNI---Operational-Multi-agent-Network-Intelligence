const API_BASE_URL = 'http://127.0.0.1:8000/supply-chain'

export const supplyChainApi = {
  // Start the pipeline: Sourcing + PO Draft
  startPipeline: async (data) => {
    try {
      const response = await fetch(`${API_BASE_URL}/run`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(data),
      })
      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || 'Failed to start pipeline')
      }
      return await response.json()
    } catch (error) {
      console.error('Error starting pipeline:', error)
      throw error
    }
  },

  // Approve a pending PO
  approvePo: async (runId, approvedBy) => {
    try {
      const response = await fetch(`${API_BASE_URL}/approve/${runId}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ approved_by: approvedBy }),
      })
      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || 'Failed to approve PO')
      }
      return await response.json()
    } catch (error) {
      console.error('Error approving PO:', error)
      throw error
    }
  },

  // Reject a pending PO
  rejectPo: async (runId) => {
    try {
      const response = await fetch(`${API_BASE_URL}/reject/${runId}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
      })
      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || 'Failed to reject PO')
      }
      return await response.json()
    } catch (error) {
      console.error('Error rejecting PO:', error)
      throw error
    }
  },

  // Track an active shipment
  trackShipment: async (shipmentId) => {
    try {
      const response = await fetch(`${API_BASE_URL}/track/${shipmentId}`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      })
      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || 'Failed to track shipment')
      }
      return await response.json()
    } catch (error) {
      console.error('Error tracking shipment:', error)
      throw error
    }
  }
}
