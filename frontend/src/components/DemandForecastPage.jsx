import { useEffect, useRef, useState } from 'react'
import DemandDashboard from './DemandDashboard'

const API_BASE_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

function DemandForecastPage({ setActivePage }) {
  const initialRequestStarted = useRef(false)
  const [sku, setSku] = useState('')
  const [products, setProducts] = useState([])
  const [periods, setPeriods] = useState(3)
  const [result, setResult] = useState(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState('')

  async function requestForecast(requestedSku = sku, requestedPeriods = periods) {
    setIsLoading(true)
    setError('')
    setResult(null)
    try {
      const response = await fetch(`${API_BASE_URL}/forecast`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ sku: requestedSku, periods: Number(requestedPeriods), save_audit: true }),
      })
      const data = await response.json()
      if (!response.ok) throw new Error(data?.detail?.message || 'Forecast request failed.')
      setResult(data)
    } catch (requestError) {
      setError(requestError.message || 'Unable to reach the Demand Forecast Agent.')
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    if (initialRequestStarted.current) return
    initialRequestStarted.current = true
    async function loadProducts() {
      try {
        const response = await fetch(`${API_BASE_URL}/forecast/products`)
        const data = await response.json()
        if (!response.ok) throw new Error(data?.detail?.message || 'Unable to load forecast products.')
        setProducts(data.products)
        if (!data.products.length) {
          setError('No products found in demand history. Add demand records in MongoDB and reload this page.')
          setIsLoading(false)
          return
        }
        const initialSku = data.products.find((product) => product.sku === 'GAR-001')?.sku || data.products[0].sku
        setSku(initialSku)
        await requestForecast(initialSku, 3)
      } catch (requestError) {
        setError(requestError.message || 'Unable to load forecast products.')
        setIsLoading(false)
      }
    }
    loadProducts()
  }, [])

  return <DemandDashboard sku={sku} setSku={setSku} periods={periods} setPeriods={setPeriods} products={products} result={result} isLoading={isLoading} error={error} requestForecast={requestForecast} setActivePage={setActivePage} />
}

export default DemandForecastPage
