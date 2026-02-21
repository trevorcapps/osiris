import React from 'react';
import ReactDOM from 'react-dom/client';
import "cesium/Build/Cesium/Widgets/widgets.css";
import App from './App';

window.CESIUM_BASE_URL = '/cesium/';

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
