import React, { useState, useEffect } from 'react'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  Tooltip,
  Legend,
} from 'chart.js'
import { Line, Bar } from 'react-chartjs-2'
import { fetchReadings, fetchConsumptionSummary, fetchUsageMetrics, fetchReadingDates, fetchReadingByDate } from '../utils/api'
import { useApi } from '../hooks/useApi'
import LoadingSpinner from './common/LoadingSpinner'

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  Tooltip,
  Legend
)

function Report() {
  const { data: readings = [], loading: readingsLoading, error: readingsError } = useApi(fetchReadings)
  const { data: consumptionSummary, loading: consumptionLoading, error: consumptionError } = useApi(fetchConsumptionSummary)
  const { data: usageMetrics, loading: usageLoading, error: usageError } = useApi(fetchUsageMetrics)
  const { data: readingDates, loading: datesLoading, error: datesError } = useApi(fetchReadingDates)

  // State for meter reading lookup
  const [selectedDate, setSelectedDate] = useState('')
  const [selectedReading, setSelectedReading] = useState(null)
  const [lookupLoading, setLookupLoading] = useState(false)
  const [lookupError, setLookupError] = useState('')

  const isLoading = readingsLoading || consumptionLoading || usageLoading
  const hasError = readingsError || consumptionError || usageError

  // Show error if any API call fails
  if (hasError) {
    return (
      <div className="form-container">
        <h2>Error Loading Data</h2>
        <div className="error-message">
          {readingsError && <p>Readings: {readingsError}</p>}
          {consumptionError && <p>Consumption: {consumptionError}</p>}
          {usageError && <p>Usage Metrics: {usageError}</p>}
        </div>
        <button onClick={() => window.location.reload()}>Reload Page</button>
      </div>
    )
  }

  // Calculate daily consumption (units consumed in each day)
  const getDailyConsumption = () => {
    if (!readings || readings.length === 0) return []
    
    try {
      const dailyData = []
      for (let i = 0; i < readings.length; i++) {
        const current = readings[i]
        
        // Validate current reading has required fields
        if (!current || 
            typeof current.meter1_consumption !== 'number' || 
            typeof current.meter2_consumption !== 'number' || 
            typeof current.meter3_consumption !== 'number') {
          console.warn('Invalid reading data at index', i, current)
          continue
        }
        
        if (i === 0) {
          // First day consumption is same as total consumption
          dailyData.push({
            date: current.reading_date,
            meter1_daily: current.meter1_consumption,
            meter2_daily: current.meter2_consumption,
            meter3_daily: current.meter3_consumption
          })
        } else {
          const previous = readings[i-1]
          // Daily consumption = today's total - yesterday's total
          dailyData.push({
            date: current.reading_date,
            meter1_daily: Math.max(0, current.meter1_consumption - previous.meter1_consumption),
            meter2_daily: Math.max(0, current.meter2_consumption - previous.meter2_consumption),
            meter3_daily: Math.max(0, current.meter3_consumption - previous.meter3_consumption)
          })
        }
      }
      return dailyData
    } catch (error) {
      console.error('Error calculating daily consumption:', error)
      return []
    }
  }

  const dailyConsumption = getDailyConsumption()

  // Handle date selection for meter reading lookup
  const handleDateSelection = async (date) => {
    if (!date) {
      setSelectedReading(null)
      setLookupError('')
      return
    }

    setLookupLoading(true)
    setLookupError('')
    setSelectedReading(null)

    try {
      const reading = await fetchReadingByDate(date)
      setSelectedReading(reading)
    } catch (error) {
      setLookupError(error.message || 'Failed to fetch reading for selected date')
    } finally {
      setLookupLoading(false)
    }
  }

  // Handle date change
  const handleDateChange = (e) => {
    const date = e.target.value
    setSelectedDate(date)
    handleDateSelection(date)
  }

  // Helper function to get color based on usage percentage
  const getUsageColor = (percentage) => {
    if (percentage >= 90) return '#dc3545' // Red
    if (percentage >= 80) return '#fd7e14' // Orange
    if (percentage >= 70) return '#ffc107' // Yellow
    return '#28a745' // Green
  }

  // Helper function to get alert level
  const getAlertLevel = (percentage) => {
    if (percentage >= 90) return 'danger'
    if (percentage >= 80) return 'warning'
    if (percentage >= 70) return 'info'
    return 'success'
  }

  // Progress Bar Component
  const ProgressBar = ({ label, current, limit, color }) => {
    const percentage = Math.min((current / limit) * 100, 100)
    return (
      <div className="progress-container-mobile" style={{ marginBottom: '15px' }}>
        <div className="progress-label" style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '5px', flexWrap: 'wrap' }}>
          <span style={{ fontWeight: 'bold' }}>{label}</span>
          <span>{current}/{limit} units ({percentage.toFixed(1)}%)</span>
        </div>
        <div style={{ 
          width: '100%', 
          height: '20px', 
          backgroundColor: '#e9ecef', 
          borderRadius: '10px',
          overflow: 'hidden'
        }}>
          <div style={{
            width: `${percentage}%`,
            height: '100%',
            backgroundColor: color,
            transition: 'width 0.5s ease'
          }}></div>
        </div>
      </div>
    )
  }

  // Alert Banner Component
  const AlertBanner = ({ type, message }) => {
    const colors = {
      danger: { bg: '#f8d7da', border: '#f5c6cb', text: '#721c24' },
      warning: { bg: '#fff3cd', border: '#ffeaa7', text: '#856404' },
      info: { bg: '#d1ecf1', border: '#bee5eb', text: '#0c5460' },
      success: { bg: '#d4edda', border: '#c3e6cb', text: '#155724' }
    }
    
    const color = colors[type] || colors.info
    
    return (
      <div className="alert-banner-mobile" style={{
        padding: '15px',
        margin: '10px 0',
        backgroundColor: color.bg,
        border: `1px solid ${color.border}`,
        borderRadius: '5px',
        color: color.text,
        fontWeight: 'bold'
      }}>
        {message}
      </div>
    )
  }


  // Only create chart data if readings exist and are not loading
  const totalChartData = readings && readings.length > 0 ? {
    labels: readings.map(reading => reading.reading_date),
    datasets: [
      {
        label: 'Meter 1 Total Consumption',
        data: readings.map(reading => reading.meter1_consumption),
        borderColor: 'rgb(255, 99, 132)',
        backgroundColor: 'rgba(255, 99, 132, 0.2)',
        tension: 0.1,
        fill: false
      },
      {
        label: 'Meter 2 Total Consumption',
        data: readings.map(reading => reading.meter2_consumption),
        borderColor: 'rgb(54, 162, 235)',
        backgroundColor: 'rgba(54, 162, 235, 0.2)',
        tension: 0.1,
        fill: false
      },
      {
        label: 'Meter 3 Total Consumption',
        data: readings.map(reading => reading.meter3_consumption),
        borderColor: 'rgb(255, 205, 86)',
        backgroundColor: 'rgba(255, 205, 86, 0.2)',
        tension: 0.1,
        fill: false
      }
    ]
  } : null

  const dailyChartData = dailyConsumption && dailyConsumption.length > 0 ? {
    labels: dailyConsumption.map(day => day.date),
    datasets: [
      {
        label: 'Meter 1 Daily Usage',
        data: dailyConsumption.map(day => day.meter1_daily),
        backgroundColor: 'rgba(255, 99, 132, 0.7)',
        borderColor: 'rgb(255, 99, 132)',
        borderWidth: 1
      },
      {
        label: 'Meter 2 Daily Usage',
        data: dailyConsumption.map(day => day.meter2_daily),
        backgroundColor: 'rgba(54, 162, 235, 0.7)',
        borderColor: 'rgb(54, 162, 235)',
        borderWidth: 1
      },
      {
        label: 'Meter 3 Daily Usage',
        data: dailyConsumption.map(day => day.meter3_daily),
        backgroundColor: 'rgba(255, 205, 86, 0.7)',
        borderColor: 'rgb(255, 205, 86)',
        borderWidth: 1
      }
    ]
  } : null

  const totalChartOptions = {
    responsive: true,
    plugins: {
      legend: {
        position: 'top',
      },
      title: {
        display: true,
        text: 'Total Electricity Consumption Over Time'
      }
    },
    scales: {
      y: {
        beginAtZero: true,
        title: {
          display: true,
          text: 'Total Consumption (Units)'
        }
      },
      x: {
        title: {
          display: true,
          text: 'Date'
        }
      }
    }
  }

  const dailyChartOptions = {
    responsive: true,
    plugins: {
      legend: {
        position: 'top',
      },
      title: {
        display: true,
        text: 'Daily Electricity Usage (Stacked)'
      }
    },
    scales: {
      x: {
        stacked: true,
        title: {
          display: true,
          text: 'Date'
        }
      },
      y: {
        stacked: true,
        beginAtZero: true,
        title: {
          display: true,
          text: 'Daily Usage (Units)'
        }
      }
    }
  }



  // Add error display for debugging
  if (readingsError || consumptionError || usageError) {
    return (
      <div>
        <h3>Error Loading Report Data</h3>
        {readingsError && <p>Readings Error: {readingsError}</p>}
        {consumptionError && <p>Consumption Error: {consumptionError}</p>}
        {usageError && <p>Usage Metrics Error: {usageError}</p>}
        <button onClick={() => window.location.reload()}>Reload Page</button>
      </div>
    )
  }

  return (
    <div>
      {/* Usage Alerts */}
      {usageMetrics && !usageError && (
        <>
          {(usageMetrics.usage_percentage?.total || 0) >= 90 && (
            <AlertBanner type="danger" message="⚠️ CRITICAL: You've used 90%+ of your monthly limit!" />
          )}
          {(usageMetrics.usage_percentage?.total || 0) >= 80 && (usageMetrics.usage_percentage?.total || 0) < 90 && (
            <AlertBanner type="warning" message="⚠️ WARNING: You've used 80%+ of your monthly limit!" />
          )}
          {(usageMetrics.usage_percentage?.total || 0) >= 70 && (usageMetrics.usage_percentage?.total || 0) < 80 && (
            <AlertBanner type="info" message="ℹ️ INFO: You've used 70%+ of your monthly limit." />
          )}
          {(usageMetrics.monthly_projection?.total || 0) > 600 && (
            <AlertBanner type="warning" message="📊 PROJECTION: At current rate, you'll exceed your monthly limit!" />
          )}
        </>
      )}

      {/* Monthly Usage Dashboard */}
      {usageMetrics && !usageError && (
        <div className="filter-container">
          <h3>Usage Dashboard</h3>
          <p><strong>Tracking Period:</strong> {usageMetrics.tracking_period?.base_date || 'N/A'} to {usageMetrics.tracking_period?.end_date || 'N/A'} | <strong>Current Date:</strong> {usageMetrics.tracking_period?.current_date || 'N/A'}</p>
          
          {/* Summary Cards */}
          <div className="desktop-grid-6 tablet-grid-3 mobile-grid-2" style={{marginTop: '20px'}}>
            <div className="mobile-card" style={{background: '#e9ecef', padding: '20px', borderRadius: '10px', boxShadow: '0 2px 10px rgba(0,0,0,0.1)', textAlign: 'center'}}>
              <h4 style={{color: '#333', margin: '0 0 10px 0'}}>Total Consumed</h4>
              <p style={{fontSize: '24px', fontWeight: 'bold', margin: '0', color: getUsageColor(usageMetrics.usage_percentage?.total || 0)}}>
                {usageMetrics.total_consumed?.total || 0}
              </p>
              <p style={{color: '#666', margin: '5px 0 0 0'}}>of 600 units</p>
            </div>
            
            <div className="mobile-card" style={{background: '#e9ecef', padding: '20px', borderRadius: '10px', boxShadow: '0 2px 10px rgba(0,0,0,0.1)', textAlign: 'center'}}>
              <h4 style={{color: '#333', margin: '0 0 10px 0'}}>Remaining</h4>
              <p style={{fontSize: '24px', fontWeight: 'bold', margin: '0', color: (usageMetrics.remaining?.total || 0) > 0 ? '#28a745' : '#dc3545'}}>
                {usageMetrics.remaining?.total || 0}
              </p>
              <p style={{color: '#666', margin: '5px 0 0 0'}}>units left</p>
            </div>
            
            <div className="mobile-card" style={{background: '#e9ecef', padding: '20px', borderRadius: '10px', boxShadow: '0 2px 10px rgba(0,0,0,0.1)', textAlign: 'center'}}>
              <h4 style={{color: '#333', margin: '0 0 10px 0'}}>Daily Average Used</h4>
              <p style={{fontSize: '24px', fontWeight: 'bold', margin: '0', color: '#17a2b8'}}>
                {usageMetrics.daily_avg_used?.total || 0}
              </p>
              <p style={{color: '#666', margin: '5px 0 0 0'}}>units/day</p>
            </div>
            
            <div className="mobile-card" style={{background: '#e9ecef', padding: '20px', borderRadius: '10px', boxShadow: '0 2px 10px rgba(0,0,0,0.1)', textAlign: 'center'}}>
              <h4 style={{color: '#333', margin: '0 0 10px 0'}}>Daily Average Remaining</h4>
              <p style={{fontSize: '24px', fontWeight: 'bold', margin: '0', color: '#6c757d'}}>
                {usageMetrics.daily_avg_remaining?.total || 0}
              </p>
              <p style={{color: '#666', margin: '5px 0 0 0'}}>units/day</p>
            </div>
            
            <div className="mobile-card" style={{background: '#e9ecef', padding: '20px', borderRadius: '10px', boxShadow: '0 2px 10px rgba(0,0,0,0.1)', textAlign: 'center'}}>
              <h4 style={{color: '#333', margin: '0 0 10px 0'}}>Days Elapsed</h4>
              <p style={{fontSize: '24px', fontWeight: 'bold', margin: '0', color: '#343a40'}}>
                {usageMetrics.tracking_period?.days_elapsed || 0}
              </p>
              <p style={{color: '#666', margin: '5px 0 0 0'}}>days passed</p>
            </div>
            
            <div className="mobile-card" style={{background: '#e9ecef', padding: '20px', borderRadius: '10px', boxShadow: '0 2px 10px rgba(0,0,0,0.1)', textAlign: 'center'}}>
              <h4 style={{color: '#333', margin: '0 0 10px 0'}}>Days Remaining</h4>
              <p style={{fontSize: '24px', fontWeight: 'bold', margin: '0', color: '#495057'}}>
                {usageMetrics.tracking_period?.days_remaining || 0}
              </p>
              <p style={{color: '#666', margin: '5px 0 0 0'}}>days left</p>
            </div>
          </div>

          {/* Progress Bars */}
          <div style={{marginTop: '30px'}}>
            <h4>Usage Progress</h4>
            <ProgressBar 
              label="Total Usage" 
              current={usageMetrics.total_consumed?.total || 0} 
              limit={600} 
              color='#6c757d'
            />
            <ProgressBar 
              label="Meter 1" 
              current={usageMetrics.total_consumed?.meter1 || 0} 
              limit={200} 
              color={getUsageColor(usageMetrics.usage_percentage?.meter1 || 0)}
            />
            <ProgressBar 
              label="Meter 2" 
              current={usageMetrics.total_consumed?.meter2 || 0} 
              limit={200} 
              color={getUsageColor(usageMetrics.usage_percentage?.meter2 || 0)}
            />
            <ProgressBar 
              label="Meter 3" 
              current={usageMetrics.total_consumed?.meter3 || 0} 
              limit={200} 
              color={getUsageColor(usageMetrics.usage_percentage?.meter3 || 0)}
            />
          </div>
        </div>
      )}


      {/* Meter Information */}
      <div className="chart-container" style={{marginTop: '30px'}}>
        <h3 style={{marginBottom: '20px'}}>Meter Information</h3>
        <div className="mobile-card" style={{
          background: '#f8f9fa',
          padding: '20px',
          borderRadius: '10px',
          boxShadow: '0 2px 10px rgba(0,0,0,0.1)',
          marginBottom: '30px',
          maxWidth: '800px',
          margin: '0 auto 30px auto'
        }}>
          <ul style={{listStyle: 'none', padding: '0', margin: '0'}}>
            <li style={{padding: '10px 0', borderBottom: '1px solid #e9ecef'}}>
              <span style={{color: 'rgb(255, 99, 132)', fontWeight: 'bold'}}>Meter 1:</span> SinglePhase (New) - Switch: 100
            </li>
            <li style={{padding: '10px 0', borderBottom: '1px solid #e9ecef'}}>
              <span style={{color: 'rgb(54, 162, 235)', fontWeight: 'bold'}}>Meter 2:</span> SinglePhase (Old) - Switch: 202
            </li>
            <li style={{padding: '10px 0', borderBottom: '1px solid #e9ecef'}}>
              <span style={{color: 'rgb(255, 205, 86)', fontWeight: 'bold'}}>Meter 3:</span> ThreePhase - Switch: 2N1 (N = phase)
            </li>
            <li style={{padding: '10px 0'}}>
              <span style={{color: '#28a745', fontWeight: 'bold'}}>Generator Switch Setting:</span> 241
            </li>
          </ul>
        </div>
      </div>

      {/* Original Charts */}
      <div className="chart-container" style={{marginTop: '30px'}}>
        <h3 style={{marginBottom: '30px'}}>Detailed Usage Charts</h3>
        
        {/* Individual Meter Cards */}
        {usageMetrics && !usageError && (
          <div className="desktop-grid-3 tablet-grid-3 mobile-grid-1" style={{marginBottom: '30px'}}>
            <div className="mobile-card" style={{background: '#e9ecef', padding: '20px', borderRadius: '10px', boxShadow: '0 2px 10px rgba(0,0,0,0.1)', textAlign: 'center'}}>
              <h4 style={{color: 'rgb(255, 99, 132)', margin: '0 0 10px 0'}}>Meter 1</h4>
              <p style={{fontSize: '24px', fontWeight: 'bold', margin: '0', color: '#000'}}>
                {usageMetrics.total_consumed?.meter1 || 0}
              </p>
            </div>
            
            <div className="mobile-card" style={{background: '#e9ecef', padding: '20px', borderRadius: '10px', boxShadow: '0 2px 10px rgba(0,0,0,0.1)', textAlign: 'center'}}>
              <h4 style={{color: 'rgb(54, 162, 235)', margin: '0 0 10px 0'}}>Meter 2</h4>
              <p style={{fontSize: '24px', fontWeight: 'bold', margin: '0', color: '#000'}}>
                {usageMetrics.total_consumed?.meter2 || 0}
              </p>
            </div>
            
            <div className="mobile-card" style={{background: '#e9ecef', padding: '20px', borderRadius: '10px', boxShadow: '0 2px 10px rgba(0,0,0,0.1)', textAlign: 'center'}}>
              <h4 style={{color: 'rgb(255, 205, 86)', margin: '0 0 10px 0'}}>Meter 3</h4>
              <p style={{fontSize: '24px', fontWeight: 'bold', margin: '0', color: '#000'}}>
                {usageMetrics.total_consumed?.meter3 || 0}
              </p>
            </div>
          </div>
        )}
        
        {isLoading ? (
          <LoadingSpinner message="Loading chart data..." />
        ) : readingsError ? (
          <p>Error loading readings data: {readingsError}</p>
        ) : readings.length > 0 && totalChartData && dailyChartData ? (
          <>
            <div className="mobile-hide-charts">
              <Line data={totalChartData} options={totalChartOptions} />
              
              <div style={{marginTop: '40px'}}>
                <Bar data={dailyChartData} options={dailyChartOptions} />
              </div>
            </div>
          </>
        ) : (
          <p>No consumption data available. Set base readings and add some daily readings first!</p>
        )}
      </div>

      {/* Meter Reading Lookup Section */}
      <div className="chart-container" style={{marginTop: '40px'}}>
        <h3 style={{marginBottom: '20px'}}>Meter Reading Lookup</h3>
        <p style={{color: '#666', marginBottom: '20px'}}>Select a date to view the actual meter readings for that specific day.</p>
        
        <div className="filter-container">
          <div style={{marginBottom: '20px'}}>
            <label htmlFor="date-select" style={{display: 'block', marginBottom: '10px', fontWeight: 'bold'}}>
              Select Date:
            </label>
            <select
              id="date-select"
              value={selectedDate}
              onChange={handleDateChange}
              style={{
                padding: '10px',
                fontSize: '16px',
                border: '2px solid #ddd',
                borderRadius: '5px',
                width: '200px',
                backgroundColor: 'white'
              }}
              disabled={datesLoading}
            >
              <option value="">-- Choose a date --</option>
              {readingDates?.dates?.map(date => (
                <option key={date} value={date}>
                  {date}
                </option>
              ))}
            </select>
          </div>

          {lookupLoading && (
            <LoadingSpinner message="Loading reading data..." />
          )}

          {lookupError && (
            <div style={{
              padding: '15px',
              backgroundColor: '#f8d7da',
              border: '1px solid #f5c6cb',
              borderRadius: '5px',
              color: '#721c24',
              marginBottom: '20px'
            }}>
              Error: {lookupError}
            </div>
          )}

          {selectedReading && !lookupLoading && (
            <div className="mobile-card" style={{
              background: '#e9ecef',
              padding: '25px',
              borderRadius: '10px',
              boxShadow: '0 2px 10px rgba(0,0,0,0.1)',
              maxWidth: '800px',
              margin: '0 auto'
            }}>
              <h4 style={{color: '#333', marginBottom: '20px', textAlign: 'center'}}>
                Meter Readings for {selectedReading.reading_date}
              </h4>
              
              <div className="desktop-grid-3 tablet-grid-3 mobile-grid-1" style={{gap: '15px'}}>
                <div style={{
                  background: 'white',
                  padding: '15px',
                  borderRadius: '8px',
                  textAlign: 'center',
                  border: '2px solid rgb(255, 99, 132)'
                }}>
                  <h5 style={{color: 'rgb(255, 99, 132)', margin: '0 0 10px 0'}}>Meter 1</h5>
                  <p style={{fontSize: '20px', fontWeight: 'bold', margin: '5px 0', color: '#000'}}>
                    Current: {selectedReading.meter1_current}
                  </p>
                  <p style={{fontSize: '16px', margin: '5px 0', color: '#666'}}>
                    Consumed: {selectedReading.meter1_consumption} units
                  </p>
                </div>
                
                <div style={{
                  background: 'white',
                  padding: '15px',
                  borderRadius: '8px',
                  textAlign: 'center',
                  border: '2px solid rgb(54, 162, 235)'
                }}>
                  <h5 style={{color: 'rgb(54, 162, 235)', margin: '0 0 10px 0'}}>Meter 2</h5>
                  <p style={{fontSize: '20px', fontWeight: 'bold', margin: '5px 0', color: '#000'}}>
                    Current: {selectedReading.meter2_current}
                  </p>
                  <p style={{fontSize: '16px', margin: '5px 0', color: '#666'}}>
                    Consumed: {selectedReading.meter2_consumption} units
                  </p>
                </div>
                
                <div style={{
                  background: 'white',
                  padding: '15px',
                  borderRadius: '8px',
                  textAlign: 'center',
                  border: '2px solid rgb(255, 205, 86)'
                }}>
                  <h5 style={{color: 'rgb(255, 205, 86)', margin: '0 0 10px 0'}}>Meter 3</h5>
                  <p style={{fontSize: '20px', fontWeight: 'bold', margin: '5px 0', color: '#000'}}>
                    Current: {selectedReading.meter3_current}
                  </p>
                  <p style={{fontSize: '16px', margin: '5px 0', color: '#666'}}>
                    Consumed: {selectedReading.meter3_consumption} units
                  </p>
                </div>
              </div>
              
              <div style={{
                marginTop: '20px',
                padding: '15px',
                background: 'white',
                borderRadius: '8px',
                textAlign: 'center'
              }}>
                <p style={{margin: '5px 0', color: '#666'}}>
                  <strong>Total Consumed:</strong> {(selectedReading.meter1_consumption + selectedReading.meter2_consumption + selectedReading.meter3_consumption).toLocaleString()} units
                </p>
                <p style={{margin: '5px 0', fontSize: '14px', color: '#999'}}>
                  Reading taken at: {new Date(selectedReading.timestamp).toLocaleTimeString('en-US', { 
                    timeZone: Intl.DateTimeFormat().resolvedOptions().timeZone,
                    hour12: false 
                  })}
                </p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default Report