import React, { useState } from "react";

function Tile({ title, port, status, uptime, image, onActionComplete }) {
  const [loading, setLoading] = useState(false);
  const [actionMessage, setActionMessage] = useState(null);

  const handleAction = async (action) => {
    setLoading(true);
    setActionMessage(null);

    try {
      const API_URL = window.location.hostname === "localhost" 
        ? "http://localhost:5000/api"
        : `http://${window.location.hostname}:5000/api`;

      const response = await fetch(`${API_URL}/docker/${title}/${action}`, {
        method: "POST",
      });

      const data = await response.json();

      if (data.success) {
        setActionMessage({ type: "success", text: data.message });
        // Rafraîchir les données après 1 seconde
        setTimeout(() => {
          if (onActionComplete) onActionComplete();
          setActionMessage(null);
        }, 1500);
      } else {
        setActionMessage({ type: "error", text: data.error });
        setTimeout(() => setActionMessage(null), 3000);
      }
    } catch (error) {
      setActionMessage({ type: "error", text: "Erreur de connexion" });
      setTimeout(() => setActionMessage(null), 3000);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="tile">
      <div className="tile-header">
        <h3 className="tile-title">{title}</h3>
        <div className={`status-dot status-${status}`}></div>
      </div>
      
      <div className="tile-info">
        {port && port !== "N/A" && (
          <div className="tile-detail">
            <span className="detail-label">Port:</span>
            <span className="detail-value">{port}</span>
          </div>
        )}
        
        {uptime && (
          <div className="tile-detail">
            <span className="detail-label">Uptime:</span>
            <span className="detail-value">{uptime}</span>
          </div>
        )}
        
        {image && (
          <div className="tile-detail tile-image">
            <span className="detail-label">Image:</span>
            <span className="detail-value">{image}</span>
          </div>
        )}
      </div>

      {/* Message d'action */}
      {actionMessage && (
        <div className={`action-message action-message-${actionMessage.type}`}>
          {actionMessage.text}
        </div>
      )}
      
      {/* Boutons d'action */}
      <div className="tile-actions">
        {status === "down" ? (
          <button 
            className="action-btn action-btn-start"
            onClick={() => handleAction("start")}
            disabled={loading}
          >
            {loading ? "⏳" : "▶️"} Start
          </button>
        ) : (
          <>
            <button 
              className="action-btn action-btn-stop"
              onClick={() => handleAction("stop")}
              disabled={loading}
            >
              {loading ? "⏳" : "⏹️"} Stop
            </button>
            <button 
              className="action-btn action-btn-restart"
              onClick={() => handleAction("restart")}
              disabled={loading}
            >
              {loading ? "⏳" : "🔄"} Restart
            </button>
          </>
        )}
      </div>
      
      <div className="tile-status-text">
        {status === "up" && "🟢 En ligne"}
        {status === "down" && "🔴 Arrêté"}
        {status === "warning" && "🟡 Pause"}
      </div>
    </div>
  );
}

export default Tile;
