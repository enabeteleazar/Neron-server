const API_URL = "http://192.168.1.56:5000"; // IP du backend

export const fetchSystem = async () => {
  try {
    const res = await fetch(`${API_URL}/api/system`);
    return await res.json();
  } catch (err) {
    console.error("Erreur System API:", err);
    return null;
  }
};

export const fetchDocker = async () => {
  try {
    const res = await fetch(`${API_URL}/api/docker`);
    return await res.json();
  } catch (err) {
    console.error("Erreur Docker API:", err);
    return [];
  }
};
