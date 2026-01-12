import React, { useState, useEffect } from "react";
import Tile from "./components/Tile";
import ServerTile from "./components/ServerTile";
import "./App.css";

// Utiliser l'IP du serveur pour que le navigateur puisse accéder à l'API
// Remplacer par l'IP de votre serveur Homebox
const API_URL = window.location.hostname === "localhost" 
  ? "http://localhost:5000/api"
  : `http://${window.location.hostname}:5000/api`;

function App() {
  const [systemData, setSystemData] = useState({
    cpu_percent: 0,
    ram_percent: 0,
    temp: 0,
    status: "up"
  });
  
  const [containers, setContainers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [lastUpdate, setLastUpdate] = useState(new Date());

  // Fonction pour récupérer les données système
  const fetchSystemData = async () => {
    try {
      const response = await fetch(`${API_URL}/system`);
      if (!response.ok) throw new Error("Erreur API système");
      const data = await response.json();
      setSystemData(data);
    } catch (err) {
      console.error("Erreur système:", err);
      setError(err.message);
    }
  };

  // Fonction pour récupérer les containers Docker
  const fetchContainers = async () => {
    try {
      const response = await fetch(`${API_URL}/docker`);
      if (!response.ok) throw new Error("Erreur API Docker");
      const data = await response.json();
      
      if (data.error) {
        console.error("Erreur Docker:", data.error);
        setContainers([]);
      } else {
        setContainers(data);
      }
      
      setLoading(false);
      setLastUpdate(new Date());
    } catch (err) {
      console.error("Erreur containers:", err);
      setError(err.message);
      setLoading(false);
    }
  };

  // Récupération initiale des données
  useEffect(() => {
    fetchSystemData();
    fetchContainers();

    // Auto-refresh toutes les 5 secondes
    const interval = setInterval(() => {
      fetchSystemData();
      fetchContainers();
    }, 5000);

    return () => clearInterval(interval);
  }, []);

  return (
    <div className="dashboard-container">
      <div className="dashboard-header">
        <h1 className="dashboard-title">Dashboard HomeBox</h1>
        <div className="dashboard-info">
          <span className="last-update">
            Dernière mise à jour: {lastUpdate.toLocaleTimeString()}
          </span>
          {error && <span className="error-badge">⚠️ {error}</span>}
        </div>
      </div>

      <div className="dashboard-grid">
        {/* Grande tuile serveur */}
        <ServerTile
          cpu={systemData.cpu_percent}
          ram={systemData.ram_percent}
          temp={systemData.temp}
          status={systemData.status}
        />

        {/* Tuiles des containers Docker */}
        {loading ? (
          <div className="loading-message">Chargement des containers...</div>
        ) : containers.length === 0 ? (
          <div className="no-containers">
            Aucun container détecté. Vérifiez Docker.
          </div>
        ) : (
          containers.map((container, index) => (
            <Tile
              key={index}
              title={container.name}
              port={container.port}
              status={container.status}
              uptime={container.uptime}
              image={container.image}
              onActionComplete={() => {
                fetchSystemData();
                fetchContainers();
              }}
            />
          ))
        )}
      </div>
    </div>
  );
}

export default App;
