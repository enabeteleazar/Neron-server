import React, { useState, useEffect } from "react";
import ServerTile from "./components/services/ServerTile";
import TileGrid from "./components/services/TileGrid";
import Section from "./components/layout/Section";
import SystemOverview from "./components/system/SystemOverview";
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

      // Sécurisation profonde
      setSystemData({
        cpu: {
          percent: Number(data?.cpu?.percent) || 0,
        },
        ram: {
          percent: Number(data?.ram?.percent) || 0,
        },
        load: {
          load1: Number(data?.load?.load1) || 0,
          load5: Number(data?.load?.load5) || 0,
          load15: Number(data?.load?.load15) || 0,
        },
        disk: {
          percent: Number(data?.disk?.percent) || 0,
        },
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

  return (
    <div className="dashboard-container">
      {/* HEADER */}
      <header className="dashboard-header">
        <h1 className="dashboard-title">HomeBox Dashboard</h1>
        <div className="dashboard-info">
          <span className="last-update">
            Dernière mise à jour : {lastUpdate.toLocaleTimeString()}
          </span>
          {error && <span className="error-badge">⚠️ {error}</span>}
        </div>
      </header>

      {/* ÉTAT GLOBAL */}
      <Section title="État global du serveur">
        <ServerTile
          cpu={systemData?.cpu?.percent ?? 0}
          ram={systemData?.ram?.percent ?? 0}
          status={systemData?.status ?? "unknown"}
        />
      </Section>

      {/* MÉTRIQUES SYSTÈME */}
      <Section title="Métriques système">
        <SystemOverview data={systemData ?? DEFAULT_SYSTEM_DATA} />
      </Section>

      {/* SERVICES */}
      <Section title="Services HomeBox">
        {loading ? (
          <div className="loading-message">Chargement des services...</div>
        ) : containers.length === 0 ? (
          <div className="no-containers">
            Aucun conteneur détecté
          </div>
        ) : (
          <TileGrid containers={containers} />
        )}
      </Section>
    </div>
  );
}

export default App;
