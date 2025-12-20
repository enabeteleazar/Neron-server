import React, { useMemo } from "react";

function ServerTile({
  cpu = 0,
  ram = 0,
  temp = 0,
  status = "unknown",
}) {
  /**
   * Normalisation des valeurs numériques
   */
  const safeCpu = useMemo(() => {
    const value = Number(cpu);
    return isNaN(value) ? 0 : Math.min(Math.max(value, 0), 100);
  }, [cpu]);

  const safeRam = useMemo(() => {
    const value = Number(ram);
    return isNaN(value) ? 0 : Math.min(Math.max(value, 0), 100);
  }, [ram]);

  const safeTemp = useMemo(() => {
    const value = Number(temp);
    return isNaN(value) ? 0 : Math.min(Math.max(value, 0), 100);
  }, [temp]);

  /**
   * Normalisation du status
   */
  const safeStatus = useMemo(() => {
    if (["up", "down", "warning"].includes(status)) return status;
    return "unknown";
  }, [status]);

  /**
   * Couleurs dynamiques
   */
  const getColor = (value) => {
    if (value > 80) return "#e03131";
    if (value > 60) return "#f5a623";
    return "#30c253";
  };

  return (
    <div className="server-tile">
      {/* HEADER */}
      <div className="server-header">
        <h2>🖥️ Serveur HP – HomeBox</h2>
        <div className={`status-dot status-${safeStatus}`} />
      </div>

      {/* METRICS */}
      <div className="server-metrics">
        {/* CPU */}
        <div className="metric">
          <span className="metric-label">CPU</span>
          <span className="metric-value">{safeCpu}%</span>
          <div className="metric-bar">
            <div
              className="metric-bar-fill"
              style={{
                width: `${safeCpu}%`,
                backgroundColor: getColor(safeCpu),
              }}
            />
          </div>
        </div>

        {/* RAM */}
        <div className="metric">
          <span className="metric-label">RAM</span>
          <span className="metric-value">{safeRam}%</span>
          <div className="metric-bar">
            <div
              className="metric-bar-fill"
              style={{
                width: `${safeRam}%`,
                backgroundColor: getColor(safeRam),
              }}
            />
          </div>
        </div>

        {/* TEMP */}
        <div className="metric">
          <span className="metric-label">Température</span>
          <span className="metric-value">{safeTemp}°C</span>
          <div className="metric-bar">
            <div
              className="metric-bar-fill"
              style={{
                width: `${safeTemp}%`,
                backgroundColor: getColor(safeTemp),
              }}
            />
          </div>
        </div>
      </div>
    </div>
  );
}

export default ServerTile;
