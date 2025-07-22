import React from 'react'

const LoadingSpinner = ({ message = 'Loading...' }) => {
  return (
    <div style={{
      display: 'flex',
      justifyContent: 'center',
      alignItems: 'center',
      padding: '20px',
      fontSize: '16px',
      color: '#666'
    }}>
      <div style={{
        width: '20px',
        height: '20px',
        border: '2px solid #f3f3f3',
        borderTop: '2px solid #007bff',
        borderRadius: '50%',
        animation: 'spin 1s linear infinite',
        marginRight: '10px'
      }}></div>
      {message}
    </div>
  )
}

export default LoadingSpinner