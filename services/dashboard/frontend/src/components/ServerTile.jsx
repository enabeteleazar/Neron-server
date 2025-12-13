import React from "react";

function ServerTile({ cpu, ram, temp, status }) {
  return (
    <div className="server-tile">
      <div className="server-header">
        <h2>🖥️ Serveur HP - Homebox</h2>
        <div className={`status-dot status-${status}`}></div>
      </div>

      <div className="server-metrics">
        <div className="metric">
          <span className="metric-label">CPU</span>
          <span className="metric-value">{cpu}%</span>
          <div className="metric-bar">
            <div 
              className="metric-bar-fill"
              style={{
                width: `${cpu}%`,
                backgroundColor: cpu > 80 ? '#e03131' : cpu > 60 ? '#f5a623' : '#30c253'
              }}
            ></div>
          </div>
        </div>

        <div className="metric">
          <span className="metric-label">RAM</span>
          <span className="metric-value">{ram}%</span>
          <div className="metric-bar">
            <div 
              className="metric-bar-fill"
              style={{
                width: `${ram}%`,
                backgroundColor: ram > 80 ? '#e03131' : ram > 60 ? '#f5a623' : '#30c253'
              }}
            ></div>
          </div>
        </div>

        <div className="metric">
          <span className="metric-label">Température</span>
          <span className="metric-value">{temp}°C</span>
          <div className="metric-bar">
            <div 
              className="metric-bar-fill"
              style={{
                width: `${Math.min(temp, 100)}%`,
                backgroundColor: temp > 70 ? '#e03131' : temp > 50 ? '#f5a623' : '#30c253'
              }}
            ></div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default ServerTile;
