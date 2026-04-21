import React, { useState, useRef, useEffect, useCallback } from "react";
import { useChatHistory, useSendMessage } from "../hooks/use-neron";

type VoiceState = "idle" | "listening" | "processing";

export default function ChatInterface() {
  const [input, setInput] = useState("");
  const [voiceState, setVoiceState] = useState<VoiceState>("idle");
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);

  const { messages, refresh } = useChatHistory();
  const { send, pending } = useSendMessage(refresh);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSend = useCallback(() => {
    if (!input.trim()) return;
    send(input.trim());
    setInput("");
  }, [input, send]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleSend(); }
  };

  const handleVoice = async () => {
    if (voiceState === "listening") {
      mediaRecorderRef.current?.stop();
      return;
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mr = new MediaRecorder(stream);
      mediaRecorderRef.current = mr;
      chunksRef.current = [];
      mr.ondataavailable = (e) => chunksRef.current.push(e.data);
      mr.onstop = async () => {
        stream.getTracks().forEach(t => t.stop());
        setVoiceState("processing");
        try {
          const blob = new Blob(chunksRef.current, { type: "audio/webm" });
          const fd = new FormData();
          fd.append("file", blob, "audio.webm");
          const res = await fetch("/api/stt", { method: "POST", body: fd });
          if (res.ok) {
            const data = await res.json();
            if (data.text) { send(data.text); }
          }
        } catch {}
        setVoiceState("idle");
      };
      mr.start();
      setVoiceState("listening");
    } catch { setVoiceState("idle"); }
  };

  const micColor = voiceState === "listening" ? "var(--red)" : voiceState === "processing" ? "var(--orange)" : "var(--primary)";

  return (
    <div className="hud-panel" style={{ display:"flex", flexDirection:"column", height:"100%", padding:0, overflow:"hidden" }}>
      <div style={{ padding:"10px 16px", borderBottom:"1px solid var(--border)", display:"flex", alignItems:"center", gap:8 }}>
        <div className="dot dot-green" style={{ animation:"pulse 2s ease-in-out infinite" }} />
        <span style={{ fontFamily:"'Orbitron',sans-serif", fontSize:11, letterSpacing:"0.2em" }}>INTERFACE NERON</span>
      </div>

      <div style={{ flex:1, overflowY:"auto", padding:"12px 16px", display:"flex", flexDirection:"column", gap:10 }}>
        {messages.length === 0 && (
          <div style={{ color:"var(--text-muted)", fontSize:13, textAlign:"center", marginTop:24 }}>
            Canal de communication actif...
          </div>
        )}
        {messages.map((msg) => (
          <div key={msg.id} style={{ display:"flex", flexDirection:"column", alignItems: msg.role === "user" ? "flex-end" : "flex-start", animation:"fadeIn 0.2s ease" }}>
            <div style={{ fontSize:10, fontFamily:"'Orbitron',sans-serif", letterSpacing:"0.1em", color:"var(--text-muted)", marginBottom:3 }}>
              {msg.role === "user" ? "OPERATEUR" : "NERON"}
            </div>
            <div style={{
              maxWidth:"85%", padding:"8px 12px",
              background: msg.role === "user" ? "rgba(155,77,255,0.1)" : "rgba(240,45,184,0.08)",
              border: `1px solid ${msg.role === "user" ? "rgba(155,77,255,0.3)" : "rgba(240,45,184,0.2)"}`,
              fontSize:14, lineHeight:1.5,
            }}>
              {msg.content}
            </div>
          </div>
        ))}
        {pending && (
          <div style={{ color:"var(--text-muted)", fontSize:12, fontFamily:"'Fira Code',monospace" }}>
            TRAITEMENT...
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      <div style={{ padding:"10px 12px", borderTop:"1px solid var(--border)", display:"flex", gap:8, alignItems:"center" }}>
        <input
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Entrez votre commande..."
          style={{
            flex:1, background:"rgba(155,77,255,0.05)",
            border:"1px solid var(--border)", color:"var(--text)",
            padding:"8px 12px", fontSize:13,
            fontFamily:"'Rajdhani',sans-serif", outline:"none",
          }}
        />
        <button onClick={handleVoice} style={{
          width:36, height:36, border:`1px solid ${micColor}`,
          background: voiceState === "listening" ? "rgba(255,68,102,0.2)" : "transparent",
          color:micColor, cursor:"pointer", fontSize:16,
          display:"flex", alignItems:"center", justifyContent:"center",
        }}>
          {voiceState === "processing" ? "⟳" : "🎤"}
        </button>
        <button onClick={handleSend} disabled={pending || !input.trim()} style={{
          padding:"0 16px", height:36,
          background: input.trim() ? "rgba(155,77,255,0.2)" : "transparent",
          border:"1px solid var(--primary)", color:"var(--primary)",
          fontFamily:"'Orbitron',sans-serif", fontSize:10, letterSpacing:"0.1em",
          cursor: input.trim() ? "pointer" : "not-allowed",
          opacity: input.trim() ? 1 : 0.4,
        }}>
          ENVOYER
        </button>
      </div>
    </div>
  );
}
