import { useState, useEffect } from 'react'
import axios from 'axios'
import './App.css'

function App() {
  const [health, setHealth] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    axios.get('http://localhost:8000/health')
      .then(response => {
        setHealth(JSON.stringify(response.data, null, 2))
      })
      .catch(err => {
        setError(err.message)
      })
  }, [])

  return (
    <div className="container">
      <h1>BenchProof Runtime UI</h1>
      <div className="status-box">
        <h2>Backend Status</h2>
        {health ? (
          <pre className="success">{health}</pre>
        ) : error ? (
          <p className="error">Error: {error}</p>
        ) : (
          <p>Connecting to backend...</p>
        )}
      </div>
    </div>
  )
}

export default App
