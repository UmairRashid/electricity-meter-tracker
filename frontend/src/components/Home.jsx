import React, { useState, useEffect } from 'react'
import { fetchBaseReadings, fetchLatestReadings, submitReadings } from '../utils/api'
import { useApiMutation } from '../hooks/useApi'
import { validateMeterReadings, validateCurrentVsBaseReadings } from '../utils/validation'
import LoadingSpinner from './common/LoadingSpinner'

function Home() {
  const [baseReadings, setBaseReadings] = useState({
    base_date: ''
  })
  const [readings, setReadings] = useState({
    meter1_current: '',
    meter2_current: '',
    meter3_current: '',
    reading_date: ''
  })
  const [hasBaseReadings, setHasBaseReadings] = useState(false)
  const [isLoading, setIsLoading] = useState(true)
  const [message, setMessage] = useState('')
  const [messageType, setMessageType] = useState('')

  useEffect(() => {
    const loadInitialData = async () => {
      setIsLoading(true)
      await Promise.all([fetchBaseReadingsData(), fetchLatestReadingsData()])
      setReadings(prev => ({
        ...prev,
        reading_date: new Date().toISOString().split('T')[0]
      }))
      setIsLoading(false)
    }
    loadInitialData()
  }, [])

  const fetchBaseReadingsData = async () => {
    try {
      const data = await fetchBaseReadings()
      if (data) {
        setBaseReadings({
          base_date: data.base_date
        })
        setHasBaseReadings(true)
      }
    } catch (error) {
      console.error('Error fetching base readings:', error)
    }
  }

  const fetchLatestReadingsData = async () => {
    try {
      const data = await fetchLatestReadings()
      setReadings(prev => ({
        ...prev,
        meter1_current: data.meter1_current.toString(),
        meter2_current: data.meter2_current.toString(),
        meter3_current: data.meter3_current.toString(),
        reading_date: data.reading_date
      }))
    } catch (error) {
      console.error('Error fetching latest readings:', error)
    }
  }

  const handleInputChange = (e) => {
    const { name, value } = e.target
    setReadings(prev => ({
      ...prev,
      [name]: value
    }))
  }

  const { mutate, loading: isSubmitting } = useApiMutation()

  const handleSubmit = async (e) => {
    e.preventDefault()
    setMessage('')

    try {
      // Validate readings
      const validation = validateMeterReadings(readings)
      if (!validation.isValid) {
        throw new Error(validation.errors[0])
      }

      // Fetch base readings for validation
      const baseData = await fetchBaseReadings()
      if (baseData) {
        const baseValidation = validateCurrentVsBaseReadings(validation.values, baseData)
        if (!baseValidation.isValid) {
          throw new Error(baseValidation.errors[0])
        }
      }

      const readingsData = {
        meter1_current: validation.values.meter1,
        meter2_current: validation.values.meter2,
        meter3_current: validation.values.meter3,
        reading_date: readings.reading_date
      }

      await mutate(submitReadings, readingsData)
      setMessage('Readings saved successfully!')
      setMessageType('success')
    } catch (error) {
      setMessage(error.message || 'Error saving readings. Please try again.')
      setMessageType('error')
    }
  }

  if (isLoading) {
    return (
      <div className="form-container">
        <LoadingSpinner message="Loading meter data..." />
      </div>
    )
  }

  return (
    <div>
      {message && (
        <div className={`${messageType}-message`}>
          {message}
        </div>
      )}

      {!hasBaseReadings ? (
        <div className="form-container">
          <h2>Setup Required</h2>
          <p>Before you can start tracking daily readings, you need to configure your base meter readings.</p>
          <div style={{textAlign: 'center', marginTop: '30px'}}>
            <a 
              href="/configure" 
              style={{
                display: 'inline-block',
                padding: '15px 30px',
                backgroundColor: '#007bff',
                color: 'white',
                textDecoration: 'none',
                borderRadius: '5px',
                fontSize: '16px'
              }}
            >
              Go to Configure Page
            </a>
          </div>
        </div>
      ) : (
        <div className="form-container">
          <h2>Daily Meter Readings</h2>
          <p>Base readings set on: <strong>{baseReadings.base_date}</strong></p>
          
          <form onSubmit={handleSubmit}>
            <div className="meter-inputs">
              <div className="input-group">
                <label htmlFor="reading_date">Reading Date:</label>
                <input
                  type="date"
                  id="reading_date"
                  name="reading_date"
                  value={readings.reading_date}
                  onChange={handleInputChange}
                  required
                />
              </div>

              <div className="input-group">
                <label htmlFor="meter1_current">Current Meter 1 Reading:</label>
                <input
                  type="number"
                  id="meter1_current"
                  name="meter1_current"
                  value={readings.meter1_current}
                  onChange={handleInputChange}
                  min="0"
                  required
                />
              </div>

              <div className="input-group">
                <label htmlFor="meter2_current">Current Meter 2 Reading:</label>
                <input
                  type="number"
                  id="meter2_current"
                  name="meter2_current"
                  value={readings.meter2_current}
                  onChange={handleInputChange}
                  min="0"
                  required
                />
              </div>

              <div className="input-group">
                <label htmlFor="meter3_current">Current Meter 3 Reading:</label>
                <input
                  type="number"
                  id="meter3_current"
                  name="meter3_current"
                  value={readings.meter3_current}
                  onChange={handleInputChange}
                  min="0"
                  required
                />
              </div>
            </div>

            <button 
              type="submit" 
              className="submit-btn"
              disabled={isSubmitting}
            >
              {isSubmitting ? 'Saving...' : 'Submit Readings'}
            </button>
          </form>
        </div>
      )}
    </div>
  )
}

export default Home