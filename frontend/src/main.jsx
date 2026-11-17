import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import './styles/tokens.css'
import './styles/base.css'
import './styles/components.css'
import './styles/app.css'

// Earlier builds let the service worker cache /api responses — decrypted
// report bodies included — in Cache Storage. The worker no longer does, but an
// installed client keeps the old cache until its entries age out, so clear it
// once on load. Removing the runtime rule only stops new writes.
if (typeof caches !== 'undefined') {
  caches.delete('api-cache').catch(() => {
    /* Cache Storage is unavailable in some private modes; nothing to clear. */
  })
}

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
