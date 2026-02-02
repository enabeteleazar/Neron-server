import { motion } from "framer-motion";
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, AreaChart, Area } from "recharts";
import { type MetricsResponse } from "@shared/routes";
import { Cpu, Thermometer, Wifi, Activity } from "lucide-react";

interface MetricsPanelProps {
  metrics?: MetricsResponse;
}

// Dummy data generator for charts since we only get point-in-time metrics
const generateChartData = () => {
  return Array.from({ length: 20 }).map((_, i) => ({
    time: i,
    value: Math.floor(Math.random() * 40) + 30,
    value2: Math.floor(Math.random() * 30) + 20,
  }));
};

const data = generateChartData();

export function MetricsPanel({ metrics }: MetricsPanelProps) {
  if (!metrics) return null;

  return (
    <motion.div 
      initial={{ opacity: 0, x: -50 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ duration: 0.5, delay: 0.2 }}
      className="flex flex-col gap-4 h-full"
    >
      <div className="font-orbitron text-primary text-lg tracking-wider border-b border-primary/30 pb-2 mb-2">
        SYSTEM DIAGNOSTICS
      </div>

      {/* CPU Widget */}
      <div className="hud-panel p-4 flex flex-col gap-2">
        <div className="flex justify-between items-center text-primary/80 font-rajdhani font-bold">
          <span className="flex items-center gap-2"><Cpu size={16} /> PROCESSOR</span>
          <span className="text-xl">{metrics.cpu}%</span>
        </div>
        <div className="w-full bg-primary/10 h-2 rounded-full overflow-hidden">
          <motion.div 
            className="h-full bg-primary shadow-[0_0_10px_rgba(0,255,255,0.5)]"
            animate={{ width: `${metrics.cpu}%` }}
            transition={{ type: "spring", stiffness: 50 }}
          />
        </div>
        <div className="h-24 w-full mt-2">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={data}>
              <defs>
                <linearGradient id="colorCpu" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="var(--primary)" stopOpacity={0.3}/>
                  <stop offset="95%" stopColor="var(--primary)" stopOpacity={0}/>
                </linearGradient>
              </defs>
              <Area type="monotone" dataKey="value" stroke="var(--primary)" fillOpacity={1} fill="url(#colorCpu)" strokeWidth={2} />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Temperature Widget */}
      <div className="hud-panel p-4 flex flex-col gap-2">
        <div className="flex justify-between items-center text-accent font-rajdhani font-bold">
          <span className="flex items-center gap-2"><Thermometer size={16} /> THERMAL</span>
          <span className="text-xl">{metrics.temperature}°C</span>
        </div>
        <div className="w-full bg-accent/10 h-2 rounded-full overflow-hidden">
          <motion.div 
            className="h-full bg-accent shadow-[0_0_10px_rgba(255,128,0,0.5)]"
            animate={{ width: `${(metrics.temperature / 100) * 100}%` }}
            transition={{ type: "spring", stiffness: 50 }}
          />
        </div>
      </div>

      {/* Network Widget */}
      <div className="hud-panel p-4 flex-1 min-h-[150px] flex flex-col">
        <div className="flex justify-between items-center text-primary/80 font-rajdhani font-bold mb-4">
          <span className="flex items-center gap-2"><Wifi size={16} /> NETWORK</span>
          <div className="flex gap-4 text-xs font-mono text-primary/60">
            <span>UP: {metrics.networkUp} MB/s</span>
            <span>DN: {metrics.networkDown} MB/s</span>
          </div>
        </div>
        <div className="flex-1 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={data}>
              <Line type="step" dataKey="value" stroke="var(--primary)" strokeWidth={2} dot={false} />
              <Line type="step" dataKey="value2" stroke="var(--accent)" strokeWidth={1} dot={false} strokeDasharray="3 3" />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>
    </motion.div>
  );
}
