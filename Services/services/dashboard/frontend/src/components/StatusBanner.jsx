import { useEffect, useState } from "react";
import { checkBackendHealth } from "../services/api";

export default function StatusBanner() {
  const [status, setStatus] = useState("checking");

  useEffect(() => {
    const check = async () => {
      const ok = await checkBackendHealth();
      setStatus(ok ? "ok" : "down");
    };

    check();
  }, []);

  if (status === "checking") {
    return (
      <div className="status-banner checking">
        Vérification des services…
      </div>
    );
  }

  if (status === "ok") return null;

  return (
    <div className="status-banner down">
      Service indisponible — mode dégradé actif
    </div>
  );
}
