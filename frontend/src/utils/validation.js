// Validation utility functions

export const validateMeterReadings = (readings) => {
  const errors = []
  
  // Check for required fields
  if (!readings.reading_date) {
    errors.push('Please select a reading date.')
  }
  
  const meter1 = parseInt(readings.meter1_current) || 0
  const meter2 = parseInt(readings.meter2_current) || 0
  const meter3 = parseInt(readings.meter3_current) || 0
  
  // Check for negative values
  if (meter1 < 0 || meter2 < 0 || meter3 < 0) {
    errors.push('Meter readings cannot be negative.')
  }
  
  return {
    isValid: errors.length === 0,
    errors,
    values: { meter1, meter2, meter3 }
  }
}

export const validateBaseReadings = (readings) => {
  const errors = []
  
  // Check for required fields
  if (!readings.base_date) {
    errors.push('Please select a base date.')
  }
  
  const meter1 = parseInt(readings.meter1_base) || 0
  const meter2 = parseInt(readings.meter2_base) || 0
  const meter3 = parseInt(readings.meter3_base) || 0
  
  // Check for negative values
  if (meter1 < 0 || meter2 < 0 || meter3 < 0) {
    errors.push('Base readings cannot be negative.')
  }
  
  // Check that at least one reading is greater than zero
  if (meter1 === 0 && meter2 === 0 && meter3 === 0) {
    errors.push('At least one base reading must be greater than zero.')
  }
  
  return {
    isValid: errors.length === 0,
    errors,
    values: { meter1, meter2, meter3 }
  }
}

export const validateCurrentVsBaseReadings = (current, base) => {
  const errors = []
  
  if (current.meter1 < base.meter1_base || 
      current.meter2 < base.meter2_base || 
      current.meter3 < base.meter3_base) {
    errors.push('Current readings cannot be less than base readings. Please check your values.')
  }
  
  return {
    isValid: errors.length === 0,
    errors
  }
}