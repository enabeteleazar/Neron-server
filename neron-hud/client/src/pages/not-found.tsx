import { Link } from "wouter";
import { HudLayout } from "@/components/HudLayout";
import { AlertTriangle } from "lucide-react";

export default function NotFound() {
  return (
    <HudLayout>
      <div className="flex flex-col items-center justify-center h-full text-center">
        <div className="relative">
          <AlertTriangle size={120} className="text-destructive opacity-80" strokeWidth={1} />
          <AlertTriangle size={120} className="text-destructive absolute top-0 left-0 blur-md opacity-40 animate-pulse" strokeWidth={1} />
        </div>
        
        <h1 className="text-6xl font-orbitron text-destructive mt-8 mb-4 tracking-widest text-glow">
          404
        </h1>
        
        <h2 className="text-2xl font-rajdhani text-destructive/80 uppercase tracking-widest mb-8">
          Signal Lost // Coordinate Not Found
        </h2>
        
        <p className="text-destructive/60 font-mono mb-8 max-w-md">
          The requested sector is outside of the operational grid. Please return to the main dashboard immediately.
        </p>

        <Link href="/" className="px-8 py-3 border border-destructive text-destructive font-orbitron uppercase tracking-widest hover:bg-destructive hover:text-black transition-all duration-300">
          Return to Base
        </Link>
      </div>
    </HudLayout>
  );
}
