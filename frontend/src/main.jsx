import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { Toaster } from 'react-hot-toast'
import { ThemeProvider } from './context/ThemeContext'
import { QueryProvider } from './context/QueryContext'
import App from './App'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <BrowserRouter>
      <ThemeProvider>
        <QueryProvider>
          <App />
          <Toaster
            position="top-right"
            toastOptions={{
              className: 'text-sm font-medium',
              duration: 4000,
              style: {
                borderRadius: '12px',
                padding: '10px 14px',
              },
            }}
          />
        </QueryProvider>
      </ThemeProvider>
    </BrowserRouter>
  </React.StrictMode>
)
