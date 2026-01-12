import React, { useMemo } from "react";
import Tile from "./Tile";

function TileGrid({ containers = [], onActionComplete }) {
  /**
   * Normalisation de la liste des containers
   */
  const safeContainers = useMemo(() => {
    if (!Array.isArray(containers)) return [];
    return containers.filter((c) => c && typeof c === "object");
  }, [containers]);

  /**
   * Cas : aucun container
   */
  if (safeContainers.length === 0) {
    return (
      <div className="no-containers">
        Aucun service Docker détecté.
      </div>
    );
  }

  return (
    <>
      {safeContainers.map((container, index) => {
        const {
          name = "Service inconnu",
          port = "N/A",
          status = "unknown",
          uptime = "—",
          image = "—",
        } = container;

        return (
          <Tile
            key={`${name}-${index}`}
            title={name}
            port={port}
            status={status}
            uptime={uptime}
            image={image}
            onActionComplete={onActionComplete}
          />
        );
      })}
    </>
  );
}

export default TileGrid;
