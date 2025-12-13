import React from "react";

const statusColor = (status) => {
  switch (status) {
    case "active": return "green";
    case "inactive": return "red";
    case "pending": return "orange";
    default: return "gray";
  }
};

const ServiceTile = ({ name, port, status }) => {
  return (
    <div className="tile service-tile">
      <h3>{name}</h3>
      <p>Port: {port}</p>
      <div className="status-dot" style={{ backgroundColor: statusColor(status) }}></div>
    </div>
  );
};

export default ServiceTile;
