import React, { useState, useEffect } from "react";
import "./App.css";
import { fetchSystem, fetchDocker, fetchHealth, toggleContainer } from "./services/api/api";

/* ======================
   CONSTANTES
====================== */
const DEFAULT_SYSTEM_DATA = {
  cpu: { percent: 0, temperature: null, count: 0, freq_mhz: null },
  ram: { percent: 0, used_mb: 0, total_mb: 0, available_mb: 0 },
  swap: { percent: 0, used_mb: 0, total_mb: 0 },
  disk: { percent: 0, used_gb: 0, total_gb: 0, free_gb: 0 },
  status: "unknown",
  uptime_seconds: 0,
  process_count: 0
};

function App() {
  const [systemData, setSystemData] = useState(DEFAULT_SYSTEM_DATA);
  const [containers, setContainers] = useState([]);
  const [dockerSummary, setDockerSummary] = useState({ 
    total: 0, running: 0, stopped: 0, paused: 0 
  });
  const [healthData, setHealthData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [lastUpdate, setLastUpdate] = useState(new Date());
  const [activePage, setActivePage] = useState("dashboard");

  /* ======================
     FETCH SYSTEM
  ====================== */
  const loadSystem = async () => {
    try {
      const data = await fetchSystem();
      if (!data) throw new Error("System API unavailable");
      
      setSystemData(data);
      setError(null);
    } catch (err) {
      console.error("System load error:", err);
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
      setContainers(data.containers);
      setDockerSummary(data.summary);
      setError(null);
    } catch (err) {
      console.error("Docker load error:", err);
      setError("Services Docker indisponibles");
      setContainers([]);
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
      setHealthData(data);
    } catch (err) {
      console.error("Health load error:", err);
      setHealthData({ 
        status: "unavailable", 
        services: { ok: [], down: [] },
        system: {},
        docker: {}
      });
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
    }, 1000);

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
    if (!temp) return "temp-unknown";
    if (temp >= 85) return "temp-critical";
    if (temp >= 70) return "temp-warning";
    return "temp-normal";
  };

  const formatUptime = (seconds) => {
    const days = Math.floor(seconds / 86400);
    const hours = Math.floor((seconds % 86400) / 3600);
    const mins = Math.floor((seconds % 3600) / 60);
    return `${days}j ${hours}h ${mins}m`;
  };

  /* ======================
     ACTION DOCKER
  ====================== */
  const handleToggleContainer = async (containerId, currentStatus) => {
    try {
      const action = currentStatus === "running" ? "stop" : "start";
      await toggleContainer(containerId, action);
      await loadDocker();
    } catch (err) {
      setError(err.message);
      setTimeout(() => setError(null), 3000);
    }
  };

  /* ======================
     RENDER
  ====================== */
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

      {/* ===== NAVBAR ===== */}
      <nav className="dashboard-navbar">
        <ul className="navbar-list">
          <li 
            className={activePage === "dashboard" ? "active" : ""} 
            onClick={() => setActivePage("dashboard")}
          >
            📊 Dashboard
          </li>
          <li 
            className={activePage === "docker" ? "active" : ""} 
            onClick={() => setActivePage("docker")}
          >
            🐳 Docker ({dockerSummary.running}/{dockerSummary.total})
          </li>
          <li 
            className={activePage === "health" ? "active" : ""} 
            onClick={() => setActivePage("health")}
          >
            🏥 Health
          </li>
        </ul>
      </nav>

      {/* ======================
          PAGE: DASHBOARD
      ======================== */}
      {activePage === "dashboard" && (
        <section className="dashboard-section">
          <h2>État global du serveur</h2>
          
          <div className="server-metrics">
            {/* CPU */}
            <div className="server-metric">
              <div className="server-metric-label">💻 CPU</div>
              <div className="server-metric-value">
                {systemData.cpu.percent.toFixed(1)} %
              </div>
              <div className="metric-sub">
                {systemData.cpu.count} cores
                {systemData.cpu.freq_mhz && ` @ ${systemData.cpu.freq_mhz} MHz`}
              </div>
              <div className="metric-bar">
                <div
                  className={`metric-bar-fill level-${getUsageLevel(systemData.cpu.percent)}`}
                  style={{ width: `${systemData.cpu.percent}%` }}
                />
              </div>
            </div>

            {/* RAM */}
            <div className="server-metric">
              <div className="server-metric-label">🧠 RAM</div>
              <div className="server-metric-value">
                {systemData.ram.percent.toFixed(1)} %
              </div>
              <div className="metric-sub">
                {systemData.ram.used_mb} / {systemData.ram.total_mb} MB
              </div>
              <div className="metric-bar">
                <div
                  className={`metric-bar-fill level-${getUsageLevel(systemData.ram.percent)}`}
                  style={{ width: `${systemData.ram.percent}%` }}
                />
              </div>
            </div>

            {/* DISK */}
            <div className="server-metric">
              <div className="server-metric-label">💾 Disque</div>
              <div className="server-metric-value">
                {systemData.disk.percent.toFixed(1)} %
              </div>
              <div className="metric-sub">
                {systemData.disk.used_gb} / {systemData.disk.total_gb} GB
              </div>
              <div className="metric-bar">
                <div
                  className={`metric-bar-fill level-${getUsageLevel(systemData.disk.percent)}`}
                  style={{ width: `${systemData.disk.percent}%` }}
                />
              </div>
            </div>

            {/* TEMPÉRATURE */}
            <div className="server-metric">
              <div className="server-metric-label">🌡️ Température CPU</div>
              <div className={`server-metric-value ${getTempClass(systemData.cpu.temperature)}`}>
                {systemData.cpu.temperature ? `${systemData.cpu.temperature.toFixed(1)} °C` : "N/A"}
              </div>
            </div>

            {/* UPTIME */}
            <div className="server-metric">
              <div className="server-metric-label">⏱️ Uptime</div>
              <div className="server-metric-value">
                {formatUptime(systemData.uptime_seconds)}
              </div>
            </div>

            {/* STATUS */}
            <div className="server-metric">
              <div className="server-metric-label">🔧 État Backend</div>
              <div className={`server-metric-value status-${systemData.status}`}>
                {systemData.status}
              </div>
            </div>
          </div>
        </section>
      )}

      {/* ======================
          PAGE: DOCKER
      ======================== */}
      {activePage === "docker" && (
        <section className="dashboard-section">
          <h2>
            Services Docker ({dockerSummary.total}) — 
            <span className="running-count"> {dockerSummary.running} actifs</span>
          </h2>

          {loading ? (
            <div className="loading-message">⏳ Chargement...</div>
          ) : containers.length === 0 ? (
            <div className="no-containers">📦 Aucun conteneur trouvé</div>
          ) : (
            <div className="tile-grid">
              {containers.map((c) => (
                <div 
                  key={c.id} 
                  className={`service-tile ${c.status === "running" ? "status-up" : "status-down"}`}
                >
                  <div className="service-tile-header">
                    <h3 className="service-tile-title">{c.name}</h3>
                    <span className={`service-status ${c.status === "running" ? "running" : "stopped"}`}>
                      <span className="status-dot" />
                      {c.status === "running" ? "Actif" : "Arrêté"}
                    </span>
                  </div>

                  <div className="service-tile-body">
                    <div className="service-info">
                      <span className="service-info-label">Image</span>
                      <span className="service-info-value">{c.image}</span>
                    </div>
                    <div className="service-info">
                      <span className="service-info-label">Port</span>
                      <span className="service-info-value">{c.port}</span>
                    </div>
                    <div className="service-info">
                      <span className="service-info-label">Uptime</span>
                      <span className="service-info-value">{c.uptime}</span>
                    </div>

                    <div className="service-actions">
                      <button 
                        onClick={() => handleToggleContainer(c.id, c.status)}
                        disabled={c.status === "running"}
                        className="btn-start"
                      >
                        ▶️ Start
                      </button>
                      <button 
                        onClick={() => handleToggleContainer(c.id, c.status)}
                        disabled={c.status !== "running"}
                        className="btn-stop"
                      >
                        ⏸️ Stop
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>
      )}

      {/* ======================
          PAGE: HEALTH
      ======================== */}
      {activePage === "health" && (
        <section className="dashboard-section">
          <h2>🏥 Health des services</h2>

          {!healthData ? (
            <div className="loading-message">⏳ Chargement Health...</div>
          ) : (
            <>
              {/* Services OK */}
              {healthData.services.ok.length > 0 && (
                <div className="health-group">
                  <h3>✅ Services opérationnels ({healthData.services.ok.length})</h3>
                  <div className="tile-grid">
                    {healthData.services.ok.map((service) => (
                      <div key={service} className="service-tile status-up">
                        <div className="service-tile-header">
                          <h3 className="service-tile-title">{service}</h3>
                          <span className="service-status running">
                            <span className="status-dot" />
                            OK
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Services DOWN */}
              {healthData.services.down.length > 0 && (
                <div className="health-group">
                  <h3>❌ Services indisponibles ({healthData.services.down.length})</h3>
                  <div className="tile-grid">
                    {healthData.services.down.map((service) => (
                      <div key={service} className="service-tile status-down">
                        <div className="service-tile-header">
                          <h3 className="service-tile-title">{service}</h3>
                          <span className="service-status stopped">
                            <span className="status-dot" />
                            DOWN
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Docker Health */}
              <div className="health-group">
                <h3>🐳 Docker Status</h3>
                <div className="health-docker">
                  <div className="health-item">
                    <span className="health-label">Disponible</span>
                    <span className={`health-value ${healthData.docker.available ? 'ok' : 'ko'}`}>
                      {healthData.docker.available ? "✅ Oui" : "❌ Non"}
                    </span>
                  </div>
                  <div className="health-item">
                    <span className="health-label">Containers</span>
                    <span className="health-value">
                      {healthData.docker.containers_running} / {healthData.docker.containers_total}
                    </span>
                  </div>
                </div>
              </div>

              {/* System Health */}
              {healthData.system && (
                <div className="health-group">
                  <h3>💻 Santé Système</h3>
                  <div className="health-docker">
                    <div className="health-item">
                      <span className="health-label">CPU</span>
                      <span className={`health-value ${healthData.system.cpu_ok ? 'ok' : 'ko'}`}>
                        {healthData.system.cpu_percent}% {healthData.system.cpu_ok ? "✅" : "⚠️"}
                      </span>
                    </div>
                    <div className="health-item">
                      <span className="health-label">RAM</span>
                      <span className={`health-value ${healthData.system.memory_ok ? 'ok' : 'ko'}`}>
                        {healthData.system.memory_percent}% {healthData.system.memory_ok ? "✅" : "⚠️"}
                      </span>
                    </div>
                    <div className="health-item">
                      <span className="health-label">Disque</span>
                      <span className={`health-value ${healthData.system.disk_ok ? 'ok' : 'ko'}`}>
                        {healthData.system.disk_percent}% {healthData.system.disk_ok ? "✅" : "⚠️"}
                      </span>
                    </div>
                  </div>
                </div>
              )}
            </>
          )}
        </section>
      )}
    </div>
  );
}

export default App;
