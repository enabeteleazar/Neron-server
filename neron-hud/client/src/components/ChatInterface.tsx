import { useState, useRef, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useChatHistory, useSendMessage } from "@/hooks/use-chat";
import { Send, Mic, Volume2 } from "lucide-react";
import { format } from "date-fns";

export function ChatInterface() {
  const { data: history, isLoading } = useChatHistory();
  const { mutate: sendMessage, isPending } = useSendMessage();
  const [input, setInput] = useState("");
  const scrollRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [history]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isPending) return;
    sendMessage(input);
    setInput("");
  };

  return (
    <motion.div 
      initial={{ opacity: 0, y: 50 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay: 0.3 }}
      className="flex flex-col h-full hud-panel"
    >
      <div className="flex items-center justify-between p-3 border-b border-primary/20 bg-primary/5">
        <h3 className="font-orbitron text-primary text-sm tracking-widest flex items-center gap-2">
          <Volume2 size={16} className="animate-pulse" />
          COMMUNICATION LINK
        </h3>
        <div className="flex gap-1">
          <div className="w-2 h-2 rounded-full bg-primary animate-ping" />
          <div className="w-2 h-2 rounded-full bg-primary" />
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-4 font-mono text-sm custom-scrollbar" ref={scrollRef}>
        {isLoading ? (
          <div className="flex flex-col gap-2 opacity-50">
            <div className="h-4 bg-primary/10 w-3/4 rounded animate-pulse" />
            <div className="h-4 bg-primary/10 w-1/2 rounded animate-pulse" />
            <div className="h-4 bg-primary/10 w-5/6 rounded animate-pulse" />
          </div>
        ) : (
          <AnimatePresence initial={false}>
            {history?.map((msg) => (
              <motion.div
                key={msg.id}
                initial={{ opacity: 0, x: msg.role === "user" ? 20 : -20 }}
                animate={{ opacity: 1, x: 0 }}
                className={`flex flex-col ${msg.role === "user" ? "items-end" : "items-start"}`}
              >
                <div className="flex items-center gap-2 mb-1 opacity-50 text-[10px] font-rajdhani uppercase tracking-wider">
                  <span>{msg.role === "user" ? "OPERATOR" : "JARVIS"}</span>
                  <span>{format(new Date(msg.createdAt || Date.now()), "HH:mm:ss")}</span>
                </div>
                <div 
                  className={`
                    max-w-[85%] p-3 rounded-sm border backdrop-blur-sm
                    ${msg.role === "user" 
                      ? "bg-primary/10 border-primary/30 text-primary-foreground rounded-tr-none" 
                      : "bg-accent/10 border-accent/30 text-accent-foreground rounded-tl-none"
                    }
                  `}
                >
                  {msg.content}
                </div>
              </motion.div>
            ))}
            {isPending && (
              <motion.div 
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="flex items-start flex-col"
              >
                <div className="flex items-center gap-2 mb-1 opacity-50 text-[10px] font-rajdhani uppercase tracking-wider">
                  <span>JARVIS</span>
                  <span>PROCESSING...</span>
                </div>
                <div className="bg-accent/10 border border-accent/30 text-accent p-3 rounded-sm rounded-tl-none">
                  <div className="flex gap-1">
                    <span className="w-1 h-3 bg-accent animate-[pulse_1s_ease-in-out_infinite]" />
                    <span className="w-1 h-3 bg-accent animate-[pulse_1s_ease-in-out_0.2s_infinite]" />
                    <span className="w-1 h-3 bg-accent animate-[pulse_1s_ease-in-out_0.4s_infinite]" />
                  </div>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        )}
      </div>

      <form onSubmit={handleSubmit} className="p-3 bg-primary/5 border-t border-primary/20 flex gap-2">
        <button 
          type="button" 
          className="p-2 text-primary/60 hover:text-primary hover:bg-primary/10 rounded transition-colors"
          title="Voice Input (Simulation)"
        >
          <Mic size={20} />
        </button>
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="ENTER COMMAND..."
          className="flex-1 bg-transparent border-b border-primary/30 text-primary placeholder:text-primary/30 font-rajdhani focus:outline-none focus:border-primary transition-colors py-1 px-2"
          disabled={isPending}
        />
        <button 
          type="submit"
          disabled={!input.trim() || isPending}
          className="p-2 text-primary hover:text-white hover:bg-primary/20 rounded disabled:opacity-50 transition-all"
        >
          <Send size={20} />
        </button>
      </form>
    </motion.div>
  );
}
