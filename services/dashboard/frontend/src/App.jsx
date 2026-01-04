import React, { useState, useEffect } from "react";
import "./App.css";
import { fetchSystem, fetchDocker, fetchHealth } from "./services/api";

/* ======================
   CONSTANTES
====================== */
const DEFAULT_SYSTEM_DATA = {
  cpu: { percent: 0, temperature: 0 },
  ram: { percent: 0 },
  disk: { percent: 0 },
  status: "unknown",
};

function App() {
  const [systemData, setSystemData] = useState(DEFAULT_SYSTEM_DATA);
  const [containers, setContainers] = useState([]);
  const [dockerSummary, setDockerSummary] = useState({ total: 0, running: 0, stopped: 0, paused: 0 });
  const [healthData, setHealthData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [lastUpdate, setLastUpdate] = useState(new Date());

  /* ======================
     FETCH SYSTEM
  ====================== */
  const loadSystem = async () => {
    try {
      const data = await fetchSystem();
      console.log("SYSTEM API RAW:", data);

      setSystemData({
        cpu: {
          percent: data?.cpu?.percent ?? 0,
          temperature: data?.cpu?.temperature ?? 0
        },
        ram: data?.ram ?? { percent: 0 },
        disk: data?.disk ?? { percent: 0 },
        status: data?.status ?? "unknown",
      });

      setError(null);
    } catch (err) {
      console.error("System API error:", err);
      setError("Système indisponible");
      setSystemData(DEFAULT_SYSTEM_DATA);
    }
  };

  /* ======================
     FETCH DOCKER
  ====================== */
  const loadDocker = async () => {
    try {
      const data = await fetchDocker();
      console.log("DOCKER API RAW:", data);

      const list = Array.isArray(data.containers) ? data.containers : [];
      setContainers(list);

      if (data?.summary) {
        setDockerSummary(data.summary);
      }

      setError(null);
    } catch (err) {
      console.error("Docker API error:", err);
      setError("Services Docker indisponibles");
      setContainers([]);
      setDockerSummary({ total: 0, running: 0, stopped: 0, paused: 0 });
    } finally {
      setLoading(false);
      setLastUpdate(new Date());
    }
  };

  /* ======================
     FETCH HEALTH
  ====================== */
  const loadHealth = async () => {
    try {
      const data = await fetchHealth();
      console.log("HEALTH API RAW:", data);
      setHealthData(data);
    } catch (err) {
      console.error("Health API error:", err);
      setHealthData({ status: "unavailable" });
    }
  };

  /* ======================
     INIT + INTERVAL
  ====================== */
  useEffect(() => {
    loadSystem();
    loadDocker();
    loadHealth();

    const interval = setInterval(() => {
      loadSystem();
      loadDocker();
      loadHealth();
    }, 500);

    return () => clearInterval(interval);
  }, []);

  /* ======================
     HELPERS UI
  ====================== */
  const getUsageLevel = (percent) => {
    if (percent >= 80) return "high";
    if (percent >= 60) return "medium";
    return "low";
  };

  const getTempClass = (temp) => {
    if (temp >= 85) return "temp-critical";
    if (temp >= 70) return "temp-warning";
    return "temp-normal";
  };

  /* ======================
     RENDER
  ====================== */
  return (
    <div className="dashboard-container">
      {/* ===== HEADER ===== */}
      <header className="dashboard-header">
        <h1 className="dashboard-title">HomeBox Dashboard</h1>
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
        <div className="server-metrics">
          {["cpu", "ram", "disk"].map((key) => (
            <div className="server-metric" key={key}>
              <div className="server-metric-label">{key.toUpperCase()}</div>
              <div className="server-metric-value">
                {(systemData[key]?.percent ?? 0).toFixed(1)} %
              </div>
              <div className="metric-bar">
                <div
                  className={`metric-bar-fill level-${getUsageLevel(systemData[key]?.percent ?? 0)}`}
                  style={{ width: `${systemData[key]?.percent ?? 0}%` }}
                />
              </div>
            </div>
          ))}
          <div className="server-metric">
            <div className="server-metric-label">Température CPU</div>
            <div className={`server-metric-value ${getTempClass(systemData.cpu?.temperature)}`}>
              {(systemData.cpu?.temperature ?? 0).toFixed(1)} °C
            </div>
          </div>
          <div className="server-metric">
            <div className="server-metric-label">État Backend</div>
            <div className="server-metric-value">{systemData.status}</div>
          </div>
        </div>
      </section>

      {/* ======================
          SERVICES DOCKER
      ======================== */}
      <section className="dashboard-section">
        <h2>
          Services Docker ({dockerSummary.total}) — {dockerSummary.running} actifs
        </h2>
        {loading ? (
          <div className="loading-message">Chargement...</div>
        ) : containers.length === 0 ? (
          <div className="no-containers">Aucun conteneur</div>
        ) : (
          <div className="tile-grid">
            {containers.map((c, i) => (
              <div
                key={c.id ?? i}
                className={`service-tile ${c.status === "running" ? "status-up" : "status-down"}`}
              >
                <div className="service-tile-header">
                  <h3 className="service-tile-title">{c.name}</h3>
                  <span
                    className={`service-status ${c.status === "running" ? "running" : "stopped"}`}
                  >
                    <span className="status-dot" />
                    {c.status === "running" ? "Actif" : "Arrêté"}
                  </span>
                </div>
                <div className="service-tile-body">
                  <div className="service-info">
                    <span className="service-info-label">Image</span>
                    <span className="service-info-value">{c.image ?? "-"}</span>
                  </div>
                  <div className="service-info">
                    <span className="service-info-label">CPU</span>
                    <span className="service-info-value">{c.stats?.cpu ?? 0}%</span>
                  </div>
                  <div className="service-info">
                    <span className="service-info-label">RAM</span>
                    <span className="service-info-value">{c.stats?.memory ?? "0 MB"}</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      {/* ======================
          HEALTH DES SERVICES
      ======================== */}
      <section className="dashboard-section">
        <h2>Health des services</h2>

        {healthData && healthData.services ? (
          <div className="tile-grid">
            {Object.entries(healthData.services).map(([service, status]) => {
              const isUp = status === "ok";
              console.log(`[HEALTH] ${service} => ${status}`);

              return (
                <div
                  key={service}
                  className={`service-tile ${isUp ? "status-up" : "status-down"}`}
                >
                  <div className="service-tile-header">
                    <h3 className="service-tile-title">{service.toUpperCase()}</h3>
                    <span
                      className={`service-status ${isUp ? "running" : "stopped"}`}
                    >
                      <span className="status-dot" />
                      {isUp ? "OK" : "KO"}
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        ) : (
          <div className="loading-message">Chargement Health…</div>
        )}
      </section>
    </div>
  );
}

export default App;
