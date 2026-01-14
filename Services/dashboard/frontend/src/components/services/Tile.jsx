import React, { useState, useMemo } from "react";

function Tile({
  title = "Service inconnu",
  port = null,
  status = "unknown",
  uptime = null,
  image = null,
  onActionComplete = null,
}) {
  const [loading, setLoading] = useState(false);
  const [actionMessage, setActionMessage] = useState(null);

  /**
   * Normalisation du status
   */
  const safeStatus = useMemo(() => {
    if (["up", "down", "warning"].includes(status)) return status;
    return "unknown";
  }, [status]);

  /**
   * Sécurité API URL
   */
  const API_URL = useMemo(() => {
    return window.location.hostname === "localhost"
      ? "http://localhost:5000/api"
      : `http://${window.location.hostname}:5000/api`;
  }, []);

  /**
   * Action Docker sécurisée
   */
  const handleAction = async (action) => {
    if (!title || loading) return;

    setLoading(true);
    setActionMessage(null);

    try {
      const response = await fetch(
        `${API_URL}/docker/${encodeURIComponent(title)}/${action}`,
        { method: "POST" }
      );

      const data = await response.json().catch(() => ({}));

      if (response.ok && data?.success) {
        setActionMessage({
          type: "success",
          text: data.message || "Action effectuée",
        });

        setTimeout(() => {
          onActionComplete?.();
          setActionMessage(null);
        }, 1500);
      } else {
        setActionMessage({
          type: "error",
          text: data?.error || "Action impossible",
        });

        setTimeout(() => setActionMessage(null), 3000);
      }
    } catch (err) {
      console.error("Tile action error:", err);
      setActionMessage({
        type: "error",
        text: "Erreur de connexion à l’API",
      });

      setTimeout(() => setActionMessage(null), 3000);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="tile">
      {/* HEADER */}
      <div className="tile-header">
        <h3 className="tile-title">{title}</h3>
        <div className={`status-dot status-${safeStatus}`} />
      </div>

      {/* INFOS */}
      <div className="tile-info">
        {port && port !== "N/A" && (
          <div className="tile-detail">
            <span className="detail-label">Port</span>
            <span className="detail-value">{port}</span>
          </div>
        )}

        {uptime && (
          <div className="tile-detail">
            <span className="detail-label">Uptime</span>
            <span className="detail-value">{uptime}</span>
          </div>
        )}

        {image && (
          <div className="tile-detail tile-image">
            <span className="detail-label">Image</span>
            <span className="detail-value">{image}</span>
          </div>
        )}
      </div>

      {/* MESSAGE */}
      {actionMessage && (
        <div className={`action-message action-message-${actionMessage.type}`}>
          {actionMessage.text}
        </div>
      )}

      {/* ACTIONS */}
      <div className="tile-actions">
        {safeStatus === "down" && (
          <button
            className="action-btn action-btn-start"
            onClick={() => handleAction("start")}
            disabled={loading}
          >
            {loading ? "⏳" : "▶️"} Start
          </button>
        )}

        {safeStatus === "up" && (
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

        {safeStatus === "unknown" && (
          <button className="action-btn" disabled>
            ❓ Indisponible
          </button>
        )}
      </div>

      {/* STATUS TEXT */}
      <div className="tile-status-text">
        {safeStatus === "up" && "🟢 En ligne"}
        {safeStatus === "down" && "🔴 Arrêté"}
        {safeStatus === "warning" && "🟡 Attention"}
        {safeStatus === "unknown" && "⚪ État inconnu"}
      </div>
    </div>
  );
}

export default Tile;
