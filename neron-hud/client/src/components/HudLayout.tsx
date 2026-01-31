import { ReactNode } from "react";
import { motion } from "framer-motion";

interface HudLayoutProps {
  children: ReactNode;
}

export function HudLayout({ children }: HudLayoutProps) {
  return (
    <div className="min-h-screen w-full relative overflow-hidden bg-[url('/images/jarvis_hud.jpeg')] bg-cover bg-center bg-no-repeat bg-blend-overlay bg-black/90">
      {/* Vignette Overlay */}
      <div className="absolute inset-0 pointer-events-none bg-[radial-gradient(circle_at_center,transparent_0%,rgba(0,0,0,0.8)_100%)] z-10" />
      
      {/* Scanline Effect */}
      <div className="absolute inset-0 pointer-events-none z-20 opacity-10 bg-[linear-gradient(transparent_50%,rgba(0,0,0,0.5)_50%)] bg-[length:100%_4px]" />
      
      {/* Content */}
      <div className="relative z-30 w-full h-full p-4 md:p-8 flex flex-col">
        {/* Top Bar - Simulated Header */}
        <header className="flex justify-between items-center mb-6 text-primary/70 text-sm tracking-[0.2em] font-orbitron">
          <motion.div 
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.5 }}
            className="flex items-center gap-4"
          >
            <span className="border-l-2 border-primary pl-3">SYSTEM ONLINE</span>
            <span className="hidden md:inline text-xs text-primary/40">SECURE CONNECTION ESTABLISHED</span>
          </motion.div>
          
          <motion.div 
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.5 }}
            className="flex items-center gap-6"
          >
            <span className="hidden md:inline">LOC: 34.0522° N, 118.2437° W</span>
            <div className="h-2 w-24 bg-primary/20 rounded-full overflow-hidden">
              <motion.div 
                className="h-full bg-primary"
                animate={{ width: ["100%", "95%", "98%", "92%", "100%"] }}
                transition={{ repeat: Infinity, duration: 2, ease: "linear" }}
              />
            </div>
            <span>PWR: 98%</span>
          </motion.div>
        </header>

        {children}

        {/* Bottom Bar - Simulated Footer */}
        <footer className="mt-auto pt-6 flex justify-between items-end text-xs text-primary/40 font-mono">
          <div className="flex flex-col gap-1">
            <span className="uppercase">Protocol V.2.0.4</span>
            <span className="uppercase">Encryption: AES-256</span>
          </div>
          <div className="w-1/3 h-px bg-gradient-to-r from-transparent via-primary/30 to-transparent" />
          <div className="uppercase">
            Status: <span className="text-primary text-glow">Active</span>
          </div>
        </footer>
      </div>
    </div>
  );
}
