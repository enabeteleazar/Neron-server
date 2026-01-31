import { HudLayout } from "@/components/HudLayout";
import { MetricsPanel } from "@/components/MetricsPanel";
import { ChatInterface } from "@/components/ChatInterface";
import { ArcReactor } from "@/components/ArcReactor";
import { useSystemMetrics } from "@/hooks/use-chat";
import { motion } from "framer-motion";
import { Activity, ShieldCheck, Database, Globe } from "lucide-react";

export default function Dashboard() {
  const { data: metrics } = useSystemMetrics();

  return (
    <HudLayout>
      <main className="flex-1 grid grid-cols-1 md:grid-cols-12 gap-6 relative z-10 overflow-hidden">
        
        {/* Left Column: Metrics */}
        <div className="md:col-span-3 flex flex-col gap-6 h-full overflow-hidden">
          <MetricsPanel metrics={metrics} />
          
          {/* Decorative Status Block */}
          <motion.div 
            initial={{ opacity: 0, x: -50 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.4 }}
            className="hud-panel p-4 mt-auto"
          >
            <h4 className="font-orbitron text-xs text-primary mb-3">SYSTEM STATUS</h4>
            <div className="grid grid-cols-2 gap-2 text-xs font-mono text-primary/70">
              <div className="flex items-center gap-2">
                <ShieldCheck size={14} className="text-primary" />
                <span>FIREWALL: ON</span>
              </div>
              <div className="flex items-center gap-2">
                <Database size={14} className="text-primary" />
                <span>DB: CONNECTED</span>
              </div>
              <div className="flex items-center gap-2">
                <Globe size={14} className="text-primary" />
                <span>SAT: LINKED</span>
              </div>
              <div className="flex items-center gap-2">
                <Activity size={14} className="text-primary" />
                <span>CORE: STABLE</span>
              </div>
            </div>
          </motion.div>
        </div>

        {/* Center Column: Visualizer */}
        <div className="md:col-span-6 flex flex-col items-center justify-center relative min-h-[400px]">
          {/* Central Reactor */}
          <ArcReactor />
          
          {/* Floating Data Points around Reactor */}
          <motion.div 
            className="absolute top-1/4 left-10 text-[10px] font-mono text-primary/40 hidden md:block"
            animate={{ opacity: [0.3, 0.8, 0.3] }}
            transition={{ duration: 4, repeat: Infinity }}
          >
            TARGET_LOCK: NULL<br/>
            SECTOR: 7G<br/>
            SCANNING...
          </motion.div>

           <motion.div 
            className="absolute bottom-1/4 right-10 text-[10px] font-mono text-primary/40 text-right hidden md:block"
            animate={{ opacity: [0.3, 0.8, 0.3] }}
            transition={{ duration: 3, repeat: Infinity, delay: 1 }}
          >
            MEMORY_DUMP: 0x4F2A<br/>
            CACHE: CLEARED<br/>
            LATENCY: 12ms
          </motion.div>
        </div>

        {/* Right Column: Chat & Tasks */}
        <div className="md:col-span-3 flex flex-col h-full overflow-hidden">
          <ChatInterface />
          
          {/* Quick Tasks / Alerts */}
          <motion.div 
            initial={{ opacity: 0, x: 50 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.6 }}
            className="mt-6 hud-panel p-4 border-accent/30 bg-accent/5"
          >
             <h4 className="font-orbitron text-xs text-accent mb-2 flex justify-between">
               <span>ACTIVE ALERTS</span>
               <span className="animate-pulse">●</span>
             </h4>
             <div className="text-xs font-mono text-accent/80 space-y-2">
               <div className="flex justify-between border-b border-accent/20 pb-1">
                 <span>ERR_09: PROXY TIMEOUT</span>
                 <span>08:42</span>
               </div>
               <div className="flex justify-between border-b border-accent/20 pb-1">
                 <span>WARN: CPU TEMP SPIKE</span>
                 <span>09:15</span>
               </div>
             </div>
          </motion.div>
        </div>

      </main>
    </HudLayout>
  );
}
