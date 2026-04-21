import React from "react";

export default function ArcReactor() {
  return (
    <div style={{
      display: "flex",
      flexDirection: "column",
      alignItems: "center",
      justifyContent: "center",
      height: "100%",
      gap: "16px",
    }}>
      {/* Reactor */}
      <div style={{ position: "relative", width: 220, height: 220 }}>
        {/* Outer ring */}
        <div style={{
          position: "absolute", inset: 0,
          borderRadius: "50%",
          border: "1px solid rgba(155,77,255,0.2)",
          animation: "spin-slow 25s linear infinite",
        }}>
          {[0,90,180,270].map(deg => (
            <div key={deg} style={{
              position: "absolute",
              width: 6, height: 6,
              borderRadius: "50%",
              background: "var(--primary)",
              boxShadow: "0 0 8px var(--primary)",
              top: "50%", left: "50%",
              transform: `rotate(${deg}deg) translateY(-110px) translate(-50%,-50%)`,
            }} />
          ))}
        </div>

        {/* Middle ring */}
        <div style={{
          position: "absolute", inset: 20,
          borderRadius: "50%",
          border: "2px solid transparent",
          background: "linear-gradient(#080510,#080510) padding-box, linear-gradient(135deg,#9B4DFF,#F02DB8,#9B4DFF) border-box",
          animation: "spin-reverse 18s linear infinite",
        }}>
          {[45,135,225,315].map(deg => (
            <div key={deg} style={{
              position: "absolute",
              width: 4, height: 12,
              background: "var(--accent)",
              top: "50%", left: "50%",
              transform: `rotate(${deg}deg) translateY(-80px) translate(-50%,-50%)`,
              opacity: 0.8,
            }} />
          ))}
        </div>

        {/* Inner ring */}
        <div style={{
          position: "absolute", inset: 44,
          borderRadius: "50%",
          border: "1px solid rgba(155,77,255,0.4)",
          animation: "spin-slow 12s linear infinite",
        }} />

        {/* Core */}
        <div style={{
          position: "absolute", inset: 64,
          borderRadius: "50%",
          background: "radial-gradient(circle, rgba(155,77,255,0.3) 0%, rgba(120,40,200,0.15) 50%, transparent 70%)",
          border: "1px solid rgba(155,77,255,0.5)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          animation: "glow-pulse 3s ease-in-out infinite",
        }}>
          <span style={{
            fontFamily: "'Orbitron', sans-serif",
            fontSize: 14,
            fontWeight: 700,
            color: "var(--primary)",
            textShadow: "0 0 12px var(--primary)",
            letterSpacing: "0.15em",
          }}>NERON</span>
        </div>

        {/* Cardinal marks */}
        {["N","E","S","O"].map((label, i) => {
          const positions = [
            { top: -20, left: "50%", transform: "translateX(-50%)" },
            { top: "50%", right: -20, transform: "translateY(-50%)" },
            { bottom: -20, left: "50%", transform: "translateX(-50%)" },
            { top: "50%", left: -20, transform: "translateY(-50%)" },
          ];
          return (
            <div key={label} style={{
              position: "absolute",
              fontFamily: "'Orbitron',sans-serif",
              fontSize: 10,
              color: "rgba(155,77,255,0.5)",
              ...positions[i],
            }}>{label}</div>
          );
        })}
      </div>

      {/* Status text */}
      <div style={{ textAlign: "center" }}>
        <div style={{
          fontFamily: "'Orbitron',sans-serif",
          fontSize: 11,
          color: "var(--text-muted)",
          letterSpacing: "0.2em",
          animation: "pulse 2s ease-in-out infinite",
        }}>SYSTEME ACTIF</div>
      </div>
    </div>
  );
}
