const API_BASE_URL = `${import.meta.env.VITE_API_URL ?? 'http://127.0.0.1:8000'}/supply-chain`

export const supplyChainApi = {
  getPipelineStatus: async (runId) => {
    const response = await fetch(`${API_BASE_URL}/status/${encodeURIComponent(runId)}`)
    const result = await response.json()
    if (!response.ok) throw new Error(result.detail || 'Could not refresh the purchase order.')
    return result
  },
  // Start the pipeline: Sourcing + PO Draft (Legacy / Manual)
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

  // Start pipeline via Natural Language (Agentic) - legacy single-shot
  chatPipeline: async (data) => {
    try {
      const response = await fetch(`${API_BASE_URL}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      })
      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || 'Failed to process chat message')
      }
      return await response.json()
    } catch (error) {
      console.error('Error processing chat:', error)
      throw error
    }
  },

  // Multi-turn requirements gathering
  gatherRequirements: async (conversationHistory) => {
    try {
      const response = await fetch(`${API_BASE_URL}/gather`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ conversation_history: conversationHistory }),
      })
      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || 'Failed to gather requirements')
      }
      return await response.json()
    } catch (error) {
      console.error('Error gathering requirements:', error)
      throw error
    }
  },

  // Find matching suppliers from real DB
  findSuppliers: async (requirements) => {
    try {
      const response = await fetch(`${API_BASE_URL}/find-suppliers`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(requirements),
      })
      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || 'Failed to find suppliers')
      }
      return await response.json()
    } catch (error) {
      console.error('Error finding suppliers:', error)
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

  // Update a supplier's intelligence details
  updateSupplier: async (supplierId, data) => {
    try {
      const response = await fetch(`${API_BASE_URL}/suppliers/${supplierId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      })
      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || 'Failed to update supplier')
      }
      return await response.json()
    } catch (error) {
      console.error('Error updating supplier:', error)
      throw error
    }
  },

  deleteSupplier: async (supplierId) => {
    const response = await fetch(`${API_BASE_URL}/suppliers/${supplierId}`, {
      method: 'DELETE',
    })
    if (!response.ok) throw new Error('Failed to delete supplier')
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

  // Track a shipment dynamically using LangChain
  trackShipment: async (shipmentId) => {
    const response = await fetch(`${API_BASE_URL}/shipments/${shipmentId}/track`)
    if (!response.ok) throw new Error('Failed to track shipment')
    return response.json()
  },

  // Manual DB approve (for seeded POs)
  manualApprovePo: async (poId) => {
    const response = await fetch(`${API_BASE_URL}/purchase-orders/${poId}/approve`, {
      method: 'PUT',
    })
    if (!response.ok) throw new Error('Failed to approve PO')
    return response.json()
  },

  // Manual DB reject (for seeded POs)
  manualRejectPo: async (poId) => {
    const response = await fetch(`${API_BASE_URL}/purchase-orders/${poId}/reject`, {
      method: 'PUT',
    })
    if (!response.ok) throw new Error('Failed to reject PO')
    return response.json()
  },

  deletePurchaseOrder: async (poId) => {
    const response = await fetch(`${API_BASE_URL}/purchase-orders/${poId}`, {
      method: 'DELETE',
    })
    if (!response.ok) throw new Error('Failed to delete PO')
    return response.json()
  },

  updateShipmentStatus: async (shipmentId, status) => {
    const response = await fetch(`${API_BASE_URL}/shipments/${shipmentId}/status`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ status }),
    })
    if (!response.ok) throw new Error('Failed to update shipment status')
    return response.json()
  },

  deleteShipment: async (shipmentId) => {
    const response = await fetch(`${API_BASE_URL}/shipments/${shipmentId}`, {
      method: 'DELETE',
    })
    if (!response.ok) throw new Error('Failed to delete shipment')
    return response.json()
  },

  // Re-send PO email to supplier (for approved POs in PurchaseOrdersTab)
  resendPoEmail: async (poId, notes = '') => {
    const response = await fetch(`${API_BASE_URL}/resend-po-email/${poId}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ notes }),
    })
    if (!response.ok) {
      const err = await response.json()
      throw new Error(err.detail || 'Failed to resend PO email')
    }
    return response.json()
  },
}

