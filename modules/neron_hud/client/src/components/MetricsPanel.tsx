import React from "react";
import { useSystemMetrics } from "../hooks/use-neron";

export default function MetricsPanel() {
  const metrics = useSystemMetrics();
  const score = metrics.score ?? 0;
  const services = metrics.services ?? [];
  const scoreColor = score > 80 ? "var(--green)" : score > 50 ? "var(--orange)" : "var(--red)";

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 12, height: "100%" }}>
      <div className="hud-panel" style={{ padding: "16px" }}>
        <div style={{ fontFamily:"'Orbitron',sans-serif", fontSize:10, color:"var(--text-muted)", letterSpacing:"0.2em", marginBottom:8 }}>
          SCORE SYSTEME
        </div>
        <div style={{ fontSize:36, fontWeight:700, color:scoreColor, textShadow:`0 0 20px ${scoreColor}`, fontFamily:"'Orbitron',sans-serif" }}>
          {score}<span style={{ fontSize:16 }}>%</span>
        </div>
        <div style={{ marginTop:8, height:4, background:"rgba(255,255,255,0.1)", borderRadius:2 }}>
          <div style={{
            height:"100%", width:`${score}%`,
            background: `linear-gradient(90deg, ${scoreColor}, ${scoreColor}99)`,
            borderRadius:2, transition:"width 0.5s ease",
            boxShadow:`0 0 8px ${scoreColor}`,
          }} />
        </div>
      </div>

      <div className="hud-panel" style={{ padding:"16px", flex:1, overflow:"auto" }}>
        <div style={{ fontFamily:"'Orbitron',sans-serif", fontSize:10, color:"var(--text-muted)", letterSpacing:"0.2em", marginBottom:12 }}>
          SERVICES
        </div>
        {services.length === 0 ? (
          <div style={{ color:"var(--text-muted)", fontSize:12 }}>Connexion...</div>
        ) : (
          <div style={{ display:"flex", flexDirection:"column", gap:8 }}>
            {services.map((svc) => {
              const dotClass = svc.status === "up" ? "dot-green" : svc.status === "down" ? "dot-red" : "dot-orange";
              return (
                <div key={svc.name} style={{ display:"flex", alignItems:"center", gap:8, justifyContent:"space-between" }}>
                  <div style={{ display:"flex", alignItems:"center", gap:8 }}>
                    <div className={`dot ${dotClass}`} />
                    <span style={{ fontSize:13, textTransform:"uppercase", letterSpacing:"0.05em" }}>{svc.name}</span>
                  </div>
                  <span style={{ fontSize:11, color:"var(--text-muted)", fontFamily:"'Fira Code',monospace" }}>
                    {svc.latency_ms != null ? `${svc.latency_ms}ms` : "--"}
                  </span>
                </div>
              );
            })}
          </div>
        )}
      </div>

      <div className="hud-panel" style={{ padding:"12px 16px" }}>
        <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:8 }}>
          {["CORE","STT","LLM","MEM"].map((s) => {
            const svc = services.find(x => x.name.toLowerCase().includes(s.toLowerCase()));
            const up = svc?.status === "up";
            return (
              <div key={s} style={{ display:"flex", alignItems:"center", gap:6 }}>
                <div className={`dot ${up ? "dot-green" : "dot-dim"}`} />
                <span style={{ fontSize:11, fontFamily:"'Orbitron',sans-serif", color: up ? "var(--text)" : "var(--text-muted)" }}>{s}</span>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
