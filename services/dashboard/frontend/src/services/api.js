// IP du backend
const API_URL = "http://192.168.1.130:5000"; 

/* =========================
   FETCH SYSTEM
========================= */
export const fetchSystem = async () => {
  try {
    const res = await fetch(`${API_URL}/api/system`);
    if (!res.ok) throw new Error(`Erreur System API : ${res.status}`);
    const data = await res.json();
    return data;
  } catch (err) {
    console.error("Erreur System API:", err);
    return null; // Retour safe pour éviter crash frontend
  }
};

/* =========================
   FETCH DOCKER
========================= */
export const fetchDocker = async () => {
  try {
    const res = await fetch(`${API_URL}/api/docker`);
    if (!res.ok) throw new Error(`Erreur Docker API : ${res.status}`);
    const data = await res.json();
    return data; // Note: data.containers sera traité côté frontend
  } catch (err) {
    console.error("Erreur Docker API:", err);
    return { containers: [] }; // Retour safe
  }
};

/* =========================
   FETCH HEALTH
========================= */
export const fetchHealth = async () => {
  try {
    const res = await fetch(`${API_URL}/api/health`);
    if (!res.ok) throw new Error(`Erreur Health API : ${res.status}`);
    const data = await res.json();
    return data; // objet { service1: "ok", service2: "ko", ... }
  } catch (err) {
    console.error("Erreur Health API:", err);
    return null; // Retour safe
  }
};
