import config from '../config'

const API_BASE = config.API_BASE_URL

// Generic API call utility
export const apiCall = async (endpoint, options = {}) => {
  const {
    method = 'GET',
    body = null,
    headers = {
      'Content-Type': 'application/json',
    },
    ...otherOptions
  } = options

  try {
    const response = await fetch(`${API_BASE}${endpoint}`, {
      method,
      headers,
      body: body ? JSON.stringify(body) : null,
      ...otherOptions,
    })

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}))
      throw new Error(errorData.detail || `HTTP error! status: ${response.status}`)
    }

    return await response.json()
  } catch (error) {
    console.error(`API call failed for ${endpoint}:`, error)
    throw error
  }
}

// Specific API functions
export const fetchReadings = () => apiCall('/readings')
export const fetchLatestReadings = () => apiCall('/readings/latest')
export const fetchBaseReadings = () => apiCall('/base-readings/latest')
export const fetchConsumptionSummary = () => apiCall('/consumption-summary')
export const fetchUsageMetrics = () => apiCall('/usage-metrics')
export const fetchReadingDates = () => apiCall('/readings/dates')
export const fetchReadingByDate = (date) => apiCall(`/readings/${date}`)

export const submitReadings = (readings) => apiCall('/readings', {
  method: 'POST',
  body: readings,
})

export const setBaseReadings = (baseReadings) => apiCall('/base-readings', {
  method: 'POST',
  body: baseReadings,
})

export const deleteOldData = (cutoffDate) => apiCall(`/readings/delete-old-data?cutoff_date=${cutoffDate}`, {
  method: 'DELETE',
})

export const deleteReadingByDate = (date) => apiCall(`/readings/${date}`, {
  method: 'DELETE',
})