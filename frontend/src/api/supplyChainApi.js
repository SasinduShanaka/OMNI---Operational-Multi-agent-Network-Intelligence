const API_BASE_URL = 'http://127.0.0.1:8000/supply-chain'

export const supplyChainApi = {
  // Start the pipeline: Sourcing + PO Draft
  startPipeline: async (data) => {
    try {
      const response = await fetch(`${API_BASE_URL}/run`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
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
        headers: { 'Content-Type': 'application/json' },
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
        headers: { 'Content-Type': 'application/json' },
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

  // Track an active shipment (calls the AI tracking agent)
  trackShipment: async (shipmentId) => {
    try {
      const response = await fetch(`${API_BASE_URL}/track/${shipmentId}`)
      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || 'Failed to track shipment')
      }
      return await response.json()
    } catch (error) {
      console.error('Error tracking shipment:', error)
      throw error
    }
  },

  // ----------------------------------------------------------------
  // Data listing endpoints (direct database reads)
  // ----------------------------------------------------------------

  // Get all suppliers from mock-erp.db
  getSuppliers: async () => {
    const response = await fetch(`${API_BASE_URL}/suppliers`)
    if (!response.ok) throw new Error('Failed to fetch suppliers')
    return response.json()
  },

  // Get all purchase orders with supplier + production plan details
  getPurchaseOrders: async () => {
    const response = await fetch(`${API_BASE_URL}/purchase-orders`)
    if (!response.ok) throw new Error('Failed to fetch purchase orders')
    return response.json()
  },

  // Get all shipments with carrier details from mock-tms.db
  getShipments: async () => {
    const response = await fetch(`${API_BASE_URL}/shipments`)
    if (!response.ok) throw new Error('Failed to fetch shipments')
    return response.json()
  },
}
