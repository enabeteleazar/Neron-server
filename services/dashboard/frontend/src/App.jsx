import React, { useState, useEffect } from "react";
import "./App.css";

// API dynamique (localhost ou serveur)
const API_URL =
  window.location.hostname === "localhost"
    ? "http://localhost:5000/api"
    : `http://${window.location.hostname}:5000/api`;

// État système par défaut (ANTI-CRASH)
const DEFAULT_SYSTEM_DATA = {
  cpu: { percent: 0 },
  ram: { percent: 0 },
  load: { load1: 0, load5: 0, load15: 0 },
  disk: { percent: 0 },
  network: { rx: "0 MB", tx: "0 MB" },
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
      const res = await fetch(`${API_URL}/system`);
      if (!res.ok) throw new Error("Erreur API système");

      const data = await res.json();

      setSystemData({
        cpu: { percent: Number(data?.cpu?.percent) || 0 },
        ram: { percent: Number(data?.ram?.percent) || 0 },
        load: {
          load1: Number(data?.load?.load1) || 0,
          load5: Number(data?.load?.load5) || 0,
          load15: Number(data?.load?.load15) || 0,
        },
        disk: { percent: Number(data?.disk?.percent) || 0 },
        network: {
          rx: data?.network?.rx ?? "0 MB",
          tx: data?.network?.tx ?? "0 MB",
        },
        status: data?.status ?? "unknown",
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
    }, 5000);

    return () => clearInterval(interval);
  }, []);

  // Fonction pour déterminer le niveau d’utilisation
  const getUsageLevel = (percent) => {
    if (percent >= 80) return "high";
    if (percent >= 60) return "medium";
    return "low";
  };

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

      {/* ===== ÉTAT GLOBAL DU SERVEUR ===== */}
      <section className="dashboard-section">
        <h2>État global du serveur</h2>
        <div className="server-tile-container">
          <div className="server-tile-header">
            <h3 className="server-tile-title">Serveur principal</h3>
            <span
              className={`server-status ${
                systemData.status === "online" ? "online" : "offline"
              }`}
            >
              <span className="status-dot" />
              {systemData.status === "online" ? "En ligne" : "Hors ligne"}
            </span>
          </div>
          <div className="server-metrics">
            <div className="server-metric">
              <div className="server-metric-label">CPU</div>
              <div className="server-metric-value">
                {(systemData.cpu?.percent ?? 0).toFixed(1)}%
              </div>
            </div>
            <div className="server-metric">
              <div className="server-metric-label">RAM</div>
              <div className="server-metric-value">
                {(systemData.ram?.percent ?? 0).toFixed(1)}%
              </div>
            </div>
            <div className="server-metric">
              <div className="server-metric-label">Disque</div>
              <div className="server-metric-value">
                {(systemData.disk?.percent ?? 0).toFixed(1)}%
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ===== MÉTRIQUES SYSTÈME ===== */}
      <section className="dashboard-section">
        <h2>Métriques système détaillées</h2>
        <div className="system-overview">
          {/* CPU */}
          <div className="metric-card">
            <div className="metric-label">Processeur</div>
            <div className="metric-value">{(systemData.cpu?.percent ?? 0).toFixed(1)}%</div>
            <div className="metric-bar">
              <div
                className={`metric-bar-fill level-${getUsageLevel(systemData.cpu?.percent ?? 0)}`}
                style={{ width: `${systemData.cpu?.percent ?? 0}%` }}
              />
            </div>
          </div>

          {/* RAM */}
          <div className="metric-card">
            <div className="metric-label">Mémoire RAM</div>
            <div className="metric-value">{(systemData.ram?.percent ?? 0).toFixed(1)}%</div>
            <div className="metric-bar">
              <div
                className={`metric-bar-fill level-${getUsageLevel(systemData.ram?.percent ?? 0)}`}
                style={{ width: `${systemData.ram?.percent ?? 0}%` }}
              />
            </div>
          </div>

          {/* Disque */}
          <div className="metric-card">
            <div className="metric-label">Disque</div>
            <div className="metric-value">{(systemData.disk?.percent ?? 0).toFixed(1)}%</div>
            <div className="metric-bar">
              <div
                className={`metric-bar-fill level-${getUsageLevel(systemData.disk?.percent ?? 0)}`}
                style={{ width: `${systemData.disk?.percent ?? 0}%` }}
              />
            </div>
          </div>

          {/* Charge système */}
          <div className="metric-card">
            <div className="metric-label">Charge (1m)</div>
            <div className="metric-value">{(systemData.load?.load1 ?? 0).toFixed(2)}</div>
            <div className="metric-subvalue">
              5m: {(systemData.load?.load5 ?? 0).toFixed(2)} | 15m: {(systemData.load?.load15 ?? 0).toFixed(2)}
            </div>
          </div>

          {/* Réseau RX */}
          <div className="metric-card">
            <div className="metric-label">Réseau ↓</div>
            <div className="metric-value">{systemData.network?.rx ?? "0 MB"}</div>
            <div className="metric-subvalue">Réception</div>
          </div>

          {/* Réseau TX */}
          <div className="metric-card">
            <div className="metric-label">Réseau ↑</div>
            <div className="metric-value">{systemData.network?.tx ?? "0 MB"}</div>
            <div className="metric-subvalue">Émission</div>
          </div>
        </div>
      </section>

      {/* ===== SERVICES HOMEBOX ===== */}
      <section className="dashboard-section">
        <h2>Services Docker ({containers.length})</h2>
        {loading ? (
          <div className="loading-message">Chargement des services...</div>
        ) : containers.length === 0 ? (
          <div className="no-containers">Aucun conteneur détecté</div>
        ) : (
          <div className="tile-grid">
            {containers.map((container, idx) => (
              <div
                key={container.id ?? idx}
                className={`service-tile ${container.state === "running" ? "" : "status-down"}`}
              >
                <div className="service-tile-header">
                  <h3 className="service-tile-title">{container.name ?? container.Names ?? `#${idx}`}</h3>
                  <span className={`service-status ${container.state === "running" ? "running" : "stopped"}`}>
                    <span className="status-dot" />
                    {container.state === "running" ? "Actif" : "Arrêté"}
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
      </section>
    </div>
  );
}

export default App;
