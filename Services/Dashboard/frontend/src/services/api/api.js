// src/services/api/index.js

export const API_URL = "http://192.168.1.130:5000/api";

export const fetchSystem = async () => {
  try {
    const res = await fetch(`${API_URL}/system/`);
    if (!res.ok) throw new Error(`Erreur System API : ${res.status}`);
    const json = await res.json();
    
    return {
      status: json.status,
      cpu: json.data?.cpu || { percent: 0, temperature: null, count: 0, freq_mhz: null },
      ram: json.data?.memory?.ram || { percent: 0, used_mb: 0, total_mb: 0, available_mb: 0 },
      swap: json.data?.memory?.swap || { percent: 0, used_mb: 0, total_mb: 0 },
      disk: json.data?.disk || { percent: 0, used_gb: 0, total_gb: 0, free_gb: 0 },
      uptime_seconds: json.data?.uptime_seconds || 0,
      process_count: json.data?.process_count || 0
    };
  } catch (err) {
    console.error("Erreur System API:", err);
    return null;
  }
};

export const fetchDocker = async () => {
  try {
    const res = await fetch(`${API_URL}/docker/list`);
    if (!res.ok) throw new Error(`Erreur Docker API : ${res.status}`);
    const json = await res.json();
    
    return {
      status: json.status,
      containers: json.data?.containers || [],
      summary: json.data?.summary || { total: 0, running: 0, stopped: 0, paused: 0 }
    };
  } catch (err) {
    console.error("Erreur Docker API:", err);
    return {
      status: "error",
      containers: [],
      summary: { total: 0, running: 0, stopped: 0, paused: 0 }
    };
  }
};

export const toggleContainer = async (containerId, action) => {
  try {
    const res = await fetch(`${API_URL}/docker/${containerId}/${action}`, {
      method: "POST"
    });
    
    if (!res.ok) {
      const error = await res.json();
      throw new Error(error.data?.detail || `Erreur ${action}`);
    }
    
    return await res.json();
  } catch (err) {
    console.error(`Erreur Docker ${action}:`, err);
    throw err;
  }
};

export const fetchHealth = async () => {
  try {
    const res = await fetch(`${API_URL}/health/`);
    if (!res.ok) throw new Error(`Erreur Health API : ${res.status}`);
    const json = await res.json();
    
    return {
      status: json.status,
      system: json.system || {},
      docker: json.docker || {},
      services: json.services || { ok: [], down: [] }
    };
  } catch (err) {
    console.error("Erreur Health API:", err);
    return {
      status: "error",
      system: {},
      docker: {},
      services: { ok: [], down: [] }
    };
  }
};
