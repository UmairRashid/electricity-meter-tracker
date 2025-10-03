import React, { useState, useEffect } from 'react'
import { fetchBaseReadings, setBaseReadings as submitBaseReadings, updateEndDate, deleteOldData, deleteReadingByDate, fetchReadingDates } from '../utils/api'
import { useApiMutation } from '../hooks/useApi'
import { validateBaseReadings } from '../utils/validation'
import LoadingSpinner from './common/LoadingSpinner'

function Configure() {
  const [baseReadings, setBaseReadings] = useState({
    meter1_base: '',
    meter2_base: '',
    meter3_base: '',
    base_date: ''
  })
  const [currentBaseReadings, setCurrentBaseReadings] = useState(null)
  const [endDate, setEndDate] = useState('')
  const [isLoading, setIsLoading] = useState(true)
  const [message, setMessage] = useState('')
  const [messageType, setMessageType] = useState('')
  const [endDateMessage, setEndDateMessage] = useState('')
  const [endDateMessageType, setEndDateMessageType] = useState('')
  const [deleteDate, setDeleteDate] = useState('')
  const [availableDates, setAvailableDates] = useState([])

  useEffect(() => {
    const loadInitialData = async () => {
      setIsLoading(true)
      const [baseReadingsData] = await Promise.all([
        fetchCurrentBaseReadings(),
        fetchAvailableDates()
      ])
      
      // If no existing base readings, set form defaults to current date
      if (!baseReadingsData) {
        const today = new Date().toISOString().split('T')[0]
        const nextMonth = new Date()
        nextMonth.setMonth(nextMonth.getMonth() + 1)
        const endDateDefault = nextMonth.toISOString().split('T')[0]
        
        setBaseReadings(prev => ({
          ...prev,
          base_date: today
        }))
        setEndDate(endDateDefault)
      }
      setIsLoading(false)
    }
    loadInitialData()
  }, [])

  const fetchCurrentBaseReadings = async () => {
    try {
      const data = await fetchBaseReadings()
      if (data) {
        setCurrentBaseReadings(data)
        // Pre-populate base readings form (without end_date)
        setBaseReadings(prev => ({
          ...prev,
          base_date: data.base_date
        }))
        // Set end date separately
        setEndDate(data.end_date)
      }
      return data
    } catch (error) {
      console.error('Error fetching current base readings:', error)
      return null
    }
  }

  const fetchAvailableDates = async () => {
    try {
      const data = await fetchReadingDates()
      if (data && data.dates) {
        setAvailableDates(data.dates)
      }
    } catch (error) {
      console.error('Error fetching available dates:', error)
    }
  }

  const handleInputChange = (e) => {
    const { name, value } = e.target
    setBaseReadings(prev => ({
      ...prev,
      [name]: value
    }))
  }

  const { mutate: submitBaseMutation, loading: isSubmitting } = useApiMutation()
  const { mutate: updateEndDateMutation, loading: isUpdatingEndDate } = useApiMutation()

  const handleSubmit = async (e) => {
    e.preventDefault()
    setMessage('')

    try {
      // Validate base readings
      const validation = validateBaseReadings(baseReadings)
      if (!validation.isValid) {
        throw new Error(validation.errors[0])
      }

      const baseData = {
        meter1_base: validation.values.meter1,
        meter2_base: validation.values.meter2,
        meter3_base: validation.values.meter3,
        base_date: baseReadings.base_date
      }

      await submitBaseMutation(submitBaseReadings, baseData)
      setMessage('Base readings configured successfully!')
      setMessageType('success')
      
      // Clear the form after successful submission
      const today = new Date().toISOString().split('T')[0]
      
      setBaseReadings({
        meter1_base: '',
        meter2_base: '',
        meter3_base: '',
        base_date: today
      })
      
      // Also fetch from server to ensure consistency
      setTimeout(() => {
        fetchCurrentBaseReadings()
      }, 500)
    } catch (error) {
      setMessage(error.message || 'Error setting base readings. Please try again.')
      setMessageType('error')
    }
  }

  const handleEndDateUpdate = async (e) => {
    e.preventDefault()
    setEndDateMessage('')

    try {
      if (!currentBaseReadings) {
        throw new Error('No base readings found. Please set base readings first.')
      }

      // Validate that end_date is not older than base_date
      if (endDate < currentBaseReadings.base_date) {
        throw new Error('End date cannot be older than base date')
      }

      await updateEndDateMutation(updateEndDate, endDate)
      setEndDateMessage('End date updated successfully! Metrics will be recalculated.')
      setEndDateMessageType('success')
      
      // Update the current base readings state
      setCurrentBaseReadings(prev => ({
        ...prev,
        end_date: endDate
      }))
      
      // Also fetch from server to ensure consistency
      setTimeout(() => {
        fetchCurrentBaseReadings()
      }, 500)
    } catch (error) {
      setEndDateMessage(error.message || 'Error updating end date. Please try again.')
      setEndDateMessageType('error')
    }
  }

  const { mutate: deleteMutation, loading: isDeleting } = useApiMutation()
  const { mutate: deleteSingleMutation, loading: isDeletingSingle } = useApiMutation()

  const handleDeleteOldData = async () => {
    if (!currentBaseReadings) {
      setMessage('No base readings found to reference for deletion.')
      setMessageType('error')
      return
    }

    if (!confirm(`Are you sure you want to delete all data older than ${currentBaseReadings.base_date}? This action cannot be undone.`)) {
      return
    }

    setMessage('')

    try {
      const result = await deleteMutation(deleteOldData, currentBaseReadings.base_date)
      setMessage(`Successfully deleted ${result.deleted_count} old records.`)
      setMessageType('success')
    } catch (error) {
      setMessage('Error deleting old data. Please try again.')
      setMessageType('error')
    }
  }

  const handleDeleteSingleDay = async () => {
    if (!deleteDate) {
      setMessage('Please select a date to delete.')
      setMessageType('error')
      return
    }

    if (!confirm(`Are you sure you want to delete the reading for ${deleteDate}? This action cannot be undone.`)) {
      return
    }

    setMessage('')

    try {
      await deleteSingleMutation(deleteReadingByDate, deleteDate)
      setMessage(`Successfully deleted reading for ${deleteDate}.`)
      setMessageType('success')
      setDeleteDate('')
      // Refresh available dates after deletion
      await fetchAvailableDates()
    } catch (error) {
      if (error.message.includes('No reading found')) {
        setMessage(`No reading found for ${deleteDate}.`)
        setMessageType('error')
      } else {
        setMessage('Error deleting reading. Please try again.')
        setMessageType('error')
      }
    }
  }

  if (isLoading) {
    return (
      <div className="form-container">
        <LoadingSpinner message="Loading configuration..." />
        <p>Please wait while we load your configuration data.</p>
      </div>
    )
  }

  return (
    <div className="form-container">
      <h2>Configure Base Readings</h2>
      <p>Set the starting meter readings to track consumption from this point forward.</p>
      
      {message && (
        <div className={`${messageType}-message`}>
          {message}
        </div>
      )}

      {currentBaseReadings && (
        <div style={{
          background: '#e3f2fd',
          padding: '15px',
          borderRadius: '8px',
          marginBottom: '20px',
          border: '1px solid #2196f3'
        }}>
          <h4 style={{margin: '0 0 10px 0', color: '#1976d2'}}>Current Base Configuration</h4>
          <p style={{margin: '5px 0'}}>
            <strong>Period:</strong> {currentBaseReadings.base_date} to {currentBaseReadings.end_date}
          </p>
          <p style={{margin: '5px 0'}}>
            <strong>Meter 1:</strong> {currentBaseReadings.meter1_base} units | 
            <strong> Meter 2:</strong> {currentBaseReadings.meter2_base} units | 
            <strong> Meter 3:</strong> {currentBaseReadings.meter3_base} units
          </p>
        </div>
      )}
      
      <form onSubmit={handleSubmit}>
        <div className="meter-inputs">
          <div className="input-group">
            <label htmlFor="base_date">Base Date:</label>
            <input
              type="date"
              id="base_date"
              name="base_date"
              value={baseReadings.base_date}
              onChange={handleInputChange}
              required
            />
          </div>

          <div className="input-group">
            <label htmlFor="meter1_base">Meter 1 Base Reading:</label>
            <input
              type="number"
              id="meter1_base"
              name="meter1_base"
              value={baseReadings.meter1_base}
              onChange={handleInputChange}
              min="0"
              required
            />
          </div>

          <div className="input-group">
            <label htmlFor="meter2_base">Meter 2 Base Reading:</label>
            <input
              type="number"
              id="meter2_base"
              name="meter2_base"
              value={baseReadings.meter2_base}
              onChange={handleInputChange}
              min="0"
              required
            />
          </div>

          <div className="input-group">
            <label htmlFor="meter3_base">Meter 3 Base Reading:</label>
            <input
              type="number"
              id="meter3_base"
              name="meter3_base"
              value={baseReadings.meter3_base}
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
          {isSubmitting ? 'Setting...' : 'Set Base Readings'}
        </button>
      </form>

      {/* End Date Update Panel */}
      {currentBaseReadings && (
        <div style={{marginTop: '30px', paddingTop: '20px', borderTop: '2px solid #eee'}}>
          <h3 style={{color: '#17a2b8', marginBottom: '15px'}}>Update Tracking Period</h3>
          
          {endDateMessage && (
            <div className={`${endDateMessageType}-message`} style={{marginBottom: '15px'}}>
              {endDateMessage}
            </div>
          )}

          <div style={{padding: '20px', background: '#e3f2fd', borderRadius: '8px', border: '1px solid #2196f3', marginBottom: '20px'}}>
            <h4 style={{color: '#1976d2', marginBottom: '10px'}}>Current Period</h4>
            <p style={{margin: '5px 0', color: '#333'}}>
              <strong>Base Date:</strong> {currentBaseReadings.base_date} | <strong>End Date:</strong> {currentBaseReadings.end_date}
            </p>
            <p style={{margin: '5px 0', color: '#333'}}>
              <strong>Total Days:</strong> {(() => {
                const baseDate = new Date(currentBaseReadings.base_date)
                const endDate = new Date(currentBaseReadings.end_date)
                const diffTime = Math.abs(endDate - baseDate)
                const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24)) + 1 // +1 to include both dates
                return diffDays
              })()} days
            </p>
            <p style={{margin: '5px 0', fontSize: '14px', color: '#666'}}>
              Change the end date to extend or modify your tracking period. All usage metrics will be recalculated automatically.
            </p>
          </div>

          <form onSubmit={handleEndDateUpdate} style={{marginBottom: '20px'}}>
            <div style={{display: 'flex', alignItems: 'center', gap: '15px', flexWrap: 'wrap'}}>
              <div>
                <label htmlFor="end_date_update" style={{display: 'block', marginBottom: '5px', fontWeight: '500'}}>
                  New End Date:
                </label>
                <input
                  type="date"
                  id="end_date_update"
                  value={endDate}
                  onChange={(e) => setEndDate(e.target.value)}
                  min={currentBaseReadings?.base_date}
                  required
                  style={{
                    padding: '10px',
                    border: '1px solid #ced4da',
                    borderRadius: '4px',
                    fontSize: '14px'
                  }}
                />
              </div>
              <div>
                <button 
                  type="submit" 
                  disabled={isUpdatingEndDate || !endDate}
                  style={{
                    background: '#17a2b8', 
                    color: 'white', 
                    padding: '10px 20px', 
                    border: 'none', 
                    borderRadius: '4px', 
                    cursor: (isUpdatingEndDate || !endDate) ? 'not-allowed' : 'pointer',
                    opacity: (isUpdatingEndDate || !endDate) ? 0.6 : 1,
                    fontSize: '14px',
                    fontWeight: '500',
                    marginTop: '20px'
                  }}
                >
                  {isUpdatingEndDate ? 'Updating...' : 'Recalculate'}
                </button>
              </div>
            </div>
          </form>
        </div>
      )}

      {currentBaseReadings && (
        <div style={{marginTop: '30px', paddingTop: '20px', borderTop: '2px solid #eee'}}>
          <h3 style={{color: '#dc3545', marginBottom: '15px'}}>Data Management</h3>
          
          {/* Delete Single Day Section */}
          <div style={{marginBottom: '30px', padding: '20px', background: '#f8f9fa', borderRadius: '8px', border: '1px solid #dee2e6'}}>
            <h4 style={{color: '#495057', marginBottom: '10px'}}>Delete Specific Day</h4>
            <p style={{marginBottom: '15px', color: '#6c757d', fontSize: '14px'}}>
              Remove a single day's meter reading. This is useful for correcting mistakes or removing duplicate entries.
            </p>
            {availableDates.length > 0 ? (
              <div style={{display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap'}}>
                <select
                  value={deleteDate}
                  onChange={(e) => setDeleteDate(e.target.value)}
                  style={{
                    padding: '8px 12px',
                    border: '1px solid #ced4da',
                    borderRadius: '4px',
                    fontSize: '14px',
                    minWidth: '150px'
                  }}
                >
                  <option value="">Select a date to delete</option>
                  {availableDates.map(date => (
                    <option key={date} value={date}>{date}</option>
                  ))}
                </select>
                <button 
                  onClick={handleDeleteSingleDay}
                  disabled={isDeletingSingle || !deleteDate}
                  style={{
                    background: '#ffc107', 
                    color: '#212529', 
                    padding: '8px 16px', 
                    border: 'none', 
                    borderRadius: '4px', 
                    cursor: (isDeletingSingle || !deleteDate) ? 'not-allowed' : 'pointer',
                    opacity: (isDeletingSingle || !deleteDate) ? 0.6 : 1,
                    fontSize: '14px',
                    fontWeight: '500'
                  }}
                >
                  {isDeletingSingle ? 'Deleting...' : 'Delete Day'}
                </button>
              </div>
            ) : (
              <p style={{color: '#6c757d', fontSize: '14px', fontStyle: 'italic', margin: 0}}>
                No meter readings available to delete.
              </p>
            )}
          </div>

          {/* Delete Old Data Section */}
          <div style={{padding: '20px', background: '#fff5f5', borderRadius: '8px', border: '1px solid #fed7d7'}}>
            <h4 style={{color: '#c53030', marginBottom: '10px'}}>Delete Old Data</h4>
            <p style={{marginBottom: '15px', color: '#666', fontSize: '14px'}}>
              Delete all meter readings older than the current base date ({currentBaseReadings.base_date}).
              This will clean up old data and keep only relevant consumption tracking data.
            </p>
            <button 
              onClick={handleDeleteOldData}
              disabled={isDeleting}
              style={{
                background: '#dc3545', 
                color: 'white', 
                padding: '10px 20px', 
                border: 'none', 
                borderRadius: '4px', 
                cursor: isDeleting ? 'not-allowed' : 'pointer',
                opacity: isDeleting ? 0.6 : 1,
                fontSize: '14px',
                fontWeight: '500'
              }}
            >
              {isDeleting ? 'Deleting...' : 'Delete Old Data'}
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

export default Configure