from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import psutil
import docker
from datetime import datetime

app = FastAPI()

# Configuration CORS pour permettre les requêtes du frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["192.168.1.130"],  # En production, remplacer par l'URL du frontend
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Docker client
try:
    client = docker.DockerClient(base_url='unix://var/run/docker.sock')
except Exception as e:
    print(f"Erreur connexion Docker: {e}")
    client = None

# --- Endpoint system info ---
@app.get("/api/system")
def system_status():
    try:
        cpu = psutil.cpu_percent(interval=1)
        ram = psutil.virtual_memory().percent
        disk = psutil.disk_usage("/").percent
        
        # Température (si disponible)
        temp = None
        try:
            temps = psutil.sensors_temperatures()
            if 'coretemp' in temps:
                temp = temps['coretemp'][0].current
        except:
            temp = 0
        
        return {
            "cpu_percent": round(cpu, 1),
            "ram_percent": round(ram, 1),
            "disk_percent": round(disk, 1),
            "temp": round(temp, 1) if temp else 36,
            "status": "up"
        }
    except Exception as e:
        return {"error": str(e)}

# --- Endpoint docker containers (tous les conteneurs) ---
@app.get("/api/docker")
def docker_containers():
    if not client:
        return {"error": "Docker client non disponible"}
    
    try:
        containers = client.containers.list(all=True)
        result = []
        
        for c in containers:
            # Calculer l'uptime
            started_at = c.attrs['State'].get('StartedAt', '')
            uptime = ""
            if started_at and c.status == "running":
                try:
                    start_time = datetime.fromisoformat(started_at.replace('Z', '+00:00'))
                    uptime_delta = datetime.now(start_time.tzinfo) - start_time
                    days = uptime_delta.days
                    hours = uptime_delta.seconds // 3600
                    minutes = (uptime_delta.seconds % 3600) // 60
                    
                    if days > 0:
                        uptime = f"{days}j {hours}h"
                    elif hours > 0:
                        uptime = f"{hours}h {minutes}m"
                    else:
                        uptime = f"{minutes}m"
                except:
                    uptime = "N/A"
            
            # Récupérer les ports
            ports = []
            port_bindings = c.attrs.get('NetworkSettings', {}).get('Ports', {})
            if port_bindings:
                for container_port, host_bindings in port_bindings.items():
                    if host_bindings:
                        for binding in host_bindings:
                            ports.append(binding.get('HostPort', ''))
            
            # Déterminer le statut simplifié
            status = "up" if c.status == "running" else "down"
            if c.status == "paused":
                status = "warning"
            
            result.append({
                "name": c.name,
                "status": status,
                "raw_status": c.status,
                "uptime": uptime,
                "port": ports[0] if ports else "N/A",
                "image": c.image.tags[0] if c.image.tags else "unknown"
            })
        
        # Trier par statut (running en premier)
        result.sort(key=lambda x: (x['status'] != 'up', x['name']))
        
        return result
    except Exception as e:
        return {"error": str(e)}

# --- Health check ---
@app.get("/api/health")
def health_check():
    return {"status": "healthy", "service": "homebox-backend"}

# --- Actions sur les containers ---
@app.post("/api/docker/{container_name}/start")
def start_container(container_name: str):
    if not client:
        return {"error": "Docker client non disponible"}
    
    try:
        container = client.containers.get(container_name)
        container.start()
        return {"success": True, "message": f"Container {container_name} démarré"}
    except docker.errors.NotFound:
        return {"error": f"Container {container_name} non trouvé"}
    except Exception as e:
        return {"error": str(e)}

@app.post("/api/docker/{container_name}/stop")
def stop_container(container_name: str):
    if not client:
        return {"error": "Docker client non disponible"}
    
    try:
        container = client.containers.get(container_name)
        container.stop()
        return {"success": True, "message": f"Container {container_name} arrêté"}
    except docker.errors.NotFound:
        return {"error": f"Container {container_name} non trouvé"}
    except Exception as e:
        return {"error": str(e)}

@app.post("/api/docker/{container_name}/restart")
def restart_container(container_name: str):
    if not client:
        return {"error": "Docker client non disponible"}
    
    try:
        container = client.containers.get(container_name)
        container.restart()
        return {"success": True, "message": f"Container {container_name} redémarré"}
    except docker.errors.NotFound:
        return {"error": f"Container {container_name} non trouvé"}
    except Exception as e:
        return {"error": str(e)}
