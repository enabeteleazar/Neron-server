import React from "react";
import ArcReactor from "./ArcReactor";
import MetricsPanel from "./MetricsPanel";
import ChatInterface from "./ChatInterface";
import { useAnomalies } from "../hooks/use-neron";

export default function Dashboard() {
  const anomalies = useAnomalies();

  return (
    <div style={{ width:"100vw", height:"100vh", position:"relative", overflow:"hidden", background:"var(--bg)" }}>
      <div style={{ position:"absolute", inset:0, backgroundImage:"url('/images/jarvis_hud.jpeg')", backgroundSize:"cover", backgroundPosition:"center", opacity:0.12, filter:"hue-rotate(200deg) saturate(0.5)" }} />
      <div style={{ position:"absolute", inset:0, background:"radial-gradient(ellipse at 50% 50%, rgba(100,20,200,0.15) 0%, transparent 70%)", pointerEvents:"none" }} />
      <div style={{ position:"absolute", inset:0, backgroundImage:"linear-gradient(rgba(140,60,255,0.025) 1px, transparent 1px), linear-gradient(90deg, rgba(140,60,255,0.025) 1px, transparent 1px)", backgroundSize:"40px 40px", pointerEvents:"none" }} />

      <div style={{ position:"relative", zIndex:1, height:"100%", display:"grid", gridTemplateColumns:"280px 1fr 340px", gridTemplateRows:"48px 1fr 40px", gap:8, padding:8 }}>

        <div style={{ gridColumn:"1 / -1", display:"flex", alignItems:"center", justifyContent:"space-between", borderBottom:"1px solid var(--border)", paddingBottom:8 }}>
          <div style={{ display:"flex", alignItems:"center", gap:12 }}>
            <div className="dot dot-green" style={{ animation:"pulse 2s ease-in-out infinite" }} />
            <h1 style={{ fontSize:16, letterSpacing:"0.3em", color:"var(--primary)", textShadow:"0 0 20px var(--primary)" }}>NERON</h1>
            <span style={{ fontSize:10, color:"var(--text-muted)", letterSpacing:"0.2em" }}>AI ASSISTANT v2.0</span>
          </div>
          <div style={{ fontSize:11, fontFamily:"'Fira Code',monospace", color:"var(--text-muted)" }}>
            {new Date().toLocaleTimeString("fr-FR")}
          </div>
        </div>

        <div style={{ gridColumn:1, gridRow:2, overflow:"hidden" }}>
          <MetricsPanel />
        </div>

        <div style={{ gridColumn:2, gridRow:2 }}>
          <div className="hud-panel" style={{ height:"100%" }}>
            <ArcReactor />
          </div>
        </div>

        <div style={{ gridColumn:3, gridRow:2, display:"flex", flexDirection:"column", gap:8, overflow:"hidden" }}>
          <div style={{ flex:1, overflow:"hidden" }}>
            <ChatInterface />
          </div>
          <div className="hud-panel" style={{ padding:"12px 16px", maxHeight:160, overflow:"auto" }}>
            <div style={{ fontFamily:"'Orbitron',sans-serif", fontSize:10, color:"var(--text-muted)", letterSpacing:"0.2em", marginBottom:8 }}>ANOMALIES</div>
            {anomalies.length === 0 ? (
              <div style={{ display:"flex", alignItems:"center", gap:8, color:"var(--green)", fontSize:12 }}>
                <span>✓</span> Aucune anomalie
              </div>
            ) : (
              <div style={{ display:"flex", flexDirection:"column", gap:6 }}>
                {anomalies.slice(0,5).map((a) => (
                  <div key={a.id} style={{ display:"flex", alignItems:"flex-start", gap:8, fontSize:12 }}>
                    <div className={`dot ${a.severity === "high" ? "dot-red" : a.severity === "medium" ? "dot-orange" : "dot-dim"}`} style={{ marginTop:3 }} />
                    <div><span style={{ color:"var(--text-muted)", fontFamily:"'Orbitron',sans-serif", fontSize:9 }}>{a.service} </span>{a.message}</div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        <div style={{ gridColumn:"1 / -1", display:"flex", alignItems:"center", justifyContent:"space-between", borderTop:"1px solid var(--border)", paddingTop:8, fontSize:10, fontFamily:"'Orbitron',sans-serif", color:"var(--text-muted)", letterSpacing:"0.15em" }}>
          <span>NERON AI — v2.0.0</span>
          <span>SYSTEME OPERATIONNEL</span>
          <span>HOMEBOX</span>
        </div>
      </div>
    </div>
  );
}
