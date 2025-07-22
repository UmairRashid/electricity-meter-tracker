import React from 'react'
import { BrowserRouter as Router, Routes, Route, Link, useLocation } from 'react-router-dom'
import Home from './components/Home'
import Report from './components/Report'
import Configure from './components/Configure'

function Navigation() {
  const location = useLocation()
  
  return (
    <nav className="nav">
      <Link 
        to="/" 
        className={location.pathname === '/' ? 'active' : ''}
      >
        Home
      </Link>
      <Link 
        to="/report" 
        className={location.pathname === '/report' ? 'active' : ''}
      >
        Report
      </Link>
      <Link 
        to="/configure" 
        className={location.pathname === '/configure' ? 'active' : ''}
      >
        Configure
      </Link>
    </nav>
  )
}

function App() {
  return (
    <Router>
      <div className="container">
        <header className="header">
          <h1>Electricity Meter Tracker</h1>
        </header>
        
        <Navigation />
        
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/report" element={<Report />} />
          <Route path="/configure" element={<Configure />} />
        </Routes>
      </div>
    </Router>
  )
}

export default App