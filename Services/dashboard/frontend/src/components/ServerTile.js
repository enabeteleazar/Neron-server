import React from "react";

const ServerTile = ({ cpu, ram, storage }) => {
  return (
    <div className="tile server-tile">
      <h2>Serveur</h2>
      <p>CPU: {cpu}%</p>
      <p>RAM: {ram}%</p>
      <p>Stockage: {storage}%</p>
    </div>
  );
};

export default ServerTile;
