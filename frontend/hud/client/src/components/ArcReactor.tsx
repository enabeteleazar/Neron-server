import { motion } from "framer-motion";

export function ArcReactor() {
  return (
    <div className="relative w-64 h-64 md:w-96 md:h-96 flex items-center justify-center pointer-events-none">
      {/* Outer Ring - Rotating */}
      <motion.div 
        className="absolute inset-0 rounded-full border border-primary/30 border-dashed"
        animate={{ rotate: 360 }}
        transition={{ duration: 20, repeat: Infinity, ease: "linear" }}
      />
      
      {/* Middle Ring - Counter Rotating */}
      <motion.div 
        className="absolute inset-4 rounded-full border-2 border-primary/20 border-t-transparent border-b-transparent"
        animate={{ rotate: -360 }}
        transition={{ duration: 15, repeat: Infinity, ease: "linear" }}
      />
      
      {/* Inner Ring - Pulsing */}
      <motion.div 
        className="absolute inset-12 rounded-full border border-primary/60"
        animate={{ scale: [1, 1.05, 1], opacity: [0.5, 0.8, 0.5] }}
        transition={{ duration: 2, repeat: Infinity }}
      />
      
      {/* Core - Glowing */}
      <div className="absolute w-20 h-20 bg-primary/10 rounded-full blur-md flex items-center justify-center">
        <motion.div 
          className="w-16 h-16 bg-primary/20 rounded-full border border-primary text-primary flex items-center justify-center font-orbitron text-xs tracking-widest shadow-[0_0_30px_rgba(0,255,255,0.4)]"
          animate={{ boxShadow: ["0 0 20px rgba(0,255,255,0.2)", "0 0 50px rgba(0,255,255,0.6)", "0 0 20px rgba(0,255,255,0.2)"] }}
          transition={{ duration: 3, repeat: Infinity }}
        >
          AI CORE
        </motion.div>
      </div>

      {/* Decorative Marks */}
      <div className="absolute top-0 w-px h-8 bg-primary/50" />
      <div className="absolute bottom-0 w-px h-8 bg-primary/50" />
      <div className="absolute left-0 w-8 h-px bg-primary/50" />
      <div className="absolute right-0 w-8 h-px bg-primary/50" />
    </div>
  );
}
