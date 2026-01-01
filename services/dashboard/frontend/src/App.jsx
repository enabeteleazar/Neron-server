import React, { useState, useEffect } from "react";
import "./App.css";

// API dynamique (localhost ou serveur)
const API_URL = "http://192.168.1.130:5000/api"; // IP du backend

// État système par défaut (ANTI-CRASH)
const DEFAULT_SYSTEM_DATA = {
  cpu_percent: 0,
  ram_percent: 0,
  disk_percent: 0,
  status: "unknown",
};

function App() {
  const [systemData, setSystemData] = useState(DEFAULT_SYSTEM_DATA);
  const [containers, setContainers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [lastUpdate, setLastUpdate] = useState(new Date());

  const fetchSystemData = async () => {
    try {
      const ok = await fetch(`${API_URL}/system`);
      if (!ok) throw new Error("Erreur API système");

      const data = await ok.json();

      setSystemData({
        cpu_percent: data.cpu_percent || 0,
        ram_percent: data.ram_percent || 0,
        disk_percent: Number(data.disk_percent) || 0,
        temp: data.temp ?? 0,
        status: data.status ?? "unknown",
      });

      setError(null);
    } catch (err) {
      console.error("System API error:", err);
      setError("Système indisponible");
      setSystemData(DEFAULT_SYSTEM_DATA);
    }
  };

  const fetchContainers = async () => {
    try {
      const res = await fetch(`${API_URL}/docker`);
      if (!res.ok) throw new Error("Erreur API Docker");

      const data = await res.json();
      setContainers(Array.isArray(data) ? data : []);
      setError(null);
    } catch (err) {
      console.error("Docker API error:", err);
      setError("Services indisponibles");
      setContainers([]);
    } finally {
      setLoading(false);
      setLastUpdate(new Date());
    }
  };

  useEffect(() => {
    fetchSystemData();
    fetchContainers();

    const interval = setInterval(() => {
      fetchSystemData();
      fetchContainers();
    }, 500);

    return () => clearInterval(interval);
  }, []);

  // Fonction pour déterminer le niveau d’utilisation
  const getUsageLevel = (percent) => {
    if (percent >= 80) return "high";
    if (percent >= 60) return "medium";
    return "low";
  };



  /* ===============================
      RENDERING DU DASHBOARD 
    ================================
  */

  return (
    <div className="dashboard-container">
      {/* ===== HEADER ===== */}
      <header className="dashboard-header">
        <h1 className="dashboard-title">🏠 HomeBox Dashboard</h1>
        <div className="dashboard-info">
          <span className="last-update">🕐 {lastUpdate.toLocaleTimeString()}</span>
          {error && <span className="error-badge">⚠️ {error}</span>}
        </div>
      </header>


      {/* ======================
          ÉTAT GLOBAL DU SERVEUR 
        ======================== */}
      <section className="dashboard-section">
        <h2>État global du serveur</h2>
        <div className="server-tile-container">
          <div className="server-tile-header">
            <h3 className="server-tile-title">Serveur principal</h3>
          
          </div>
          <div className="server-metrics">
            <div className="server-metric">
              <div className="server-metric-label">CPU</div>
              <div className="server-metric-value">
                {(systemData.cpu_percent ?? 0).toFixed(1)} %
              </div>
              <div className="metric-bar">
                <div
                  className={`metric-bar-fill level-${getUsageLevel(systemData.cpu_percent)}`}
                  style={{ width: `${systemData.cpu_percent ?? 0}%` }}
                />
              </div>
            </div>
            <div className="server-metric">
              <div className="server-metric-label">RAM</div>
              <div className="server-metric-value">
                {(systemData.ram_percent ?? 0).toFixed(1)} %
              </div>
              <div className="metric-bar">
                <div
                  className={`metric-bar-fill level-${getUsageLevel(systemData.ram_percent)}`}
                  style={{ width: `${systemData.ram_percent ?? 0}%` }}
                />
              </div>
            </div>
              <div className="server-metric">
              <div className="server-metric-label">Temperature</div>
              <div className="server-metric-value">
                {(systemData.temp ?? 0).toFixed(1)} °C
              </div>
            </div>
            <div className="server-metric">
              <div className="server-metric-label">Disque</div>
              <div className="server-metric-value">
                {(systemData.disk_percent ?? 0).toFixed(1)} %
              </div>
              <div className="metric-bar">
                <div
                  className={`metric-bar-fill level-${getUsageLevel(systemData.disk_percent)}`}
                  style={{ width: `${systemData.disk_percent ?? 0}%` }}
                />
              </div>
            </div>
            <div className="server-metric">
              <div className="server-metric-label">Etat</div>
              <div className="server-metric-value">
                {(systemData.status ?? "unknown")}
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ======================
          SERVICES DOCKER 
        ======================== */}
      <section className="dashboard-section">
        <h2>Services Docker ({containers.length})</h2>
        <div className="server-tile-container">
        {loading ? (
          <div className="loading-message">Chargement des services...</div>
        ) : containers.length === 0 ? (
          <div className="no-containers">Aucun conteneur détecté</div>
        ) : (
          <div className="tile-grid">
            {containers.map((container, idx) => (
              <div
                key={container.id ?? idx}
                className={`service-tile ${container.state === "up" ? "" : "status-down"}`}
              >
                <div className="service-tile-header">
                  <h3 className="service-tile-title">{container.name ?? container.Names ?? `#${idx}`}</h3>
                  <span className={`service-status ${container.status === "up" ? "running" : "stopped"}`}>
                    <span className="status-dot" />
                    {container.status === "running" ? "Actif" : "Arrêté"}
                  </span>
                </div>
                <div className="service-tile-body">
                  <div className="service-info">
                    <span className="service-info-label">Image</span>
                    <span className="service-info-value">{container.image ?? "-"}</span>
                  </div>
                  {Array.isArray(container.ports) && container.ports.length > 0 && (
                    <div className="service-info">
                      <span className="service-info-label">Ports</span>
                      <span className="service-info-value">{container.ports.join(", ")}</span>
                    </div>
                  )}
                  <div className="service-info">
                    <span className="service-info-label">CPU</span>
                    <span className="service-info-value">{container.stats?.cpu ?? "0"}%</span>
                  </div>
                  <div className="service-info">
                    <span className="service-info-label">RAM</span>
                    <span className="service-info-value">{container.stats?.memory ?? "0 MB"}</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
        </div>
      </section>
    </div>
  );
}

export default App;
