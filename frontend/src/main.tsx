import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <div className="flex items-center justify-center h-screen">
      <h1 className="text-4xl font-bold text-blue-500">Hello, World!</h1>
    </div>
  </StrictMode>
)
