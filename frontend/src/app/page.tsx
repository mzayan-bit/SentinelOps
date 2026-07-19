import type { Metadata } from "next";
import {
  Activity,
  AlertTriangle,
  Camera,
  Cpu,
  BarChart,
  ShieldCheck,
  Video,
  Clock,
  Eye
} from "lucide-react";
import Link from "next/link";

export const metadata: Metadata = {
  title: "Commander Dashboard | SentinelOps",
};

// Mock data based on the generated SentinelOps Narrative design
const telemetryStats = [
  { label: "ACTIVE STREAMS", value: "12", icon: Camera, color: "text-accent" },
  { label: "INFERENCE LATENCY", value: "42ms", icon: Cpu, color: "text-success" },
  { label: "PPE COMPLIANCE", value: "98.2%", icon: ShieldCheck, color: "text-accent" },
  { label: "CRITICAL ALERTS", value: "3", icon: AlertTriangle, color: "text-danger", isCritical: true },
];

const liveFeeds = [
  { id: "CAM-01", location: "Main Gate", helmet: 99, vest: 95, status: "safe" },
  { id: "CAM-02", location: "Sector 4", helmet: 92, vest: 88, status: "safe" },
  { id: "CAM-03", location: "Loading Bay", helmet: 45, vest: 90, status: "warning" },
  { id: "CAM-04", location: "Catwalk B", helmet: 98, vest: 97, status: "safe" },
];

const liveAlerts = [
  { id: "ALT-1042", time: "14:22:05", cam: "CAM-03", issue: "Missing Helmet", type: "warning" },
  { id: "ALT-1043", time: "14:15:30", cam: "CAM-07", issue: "Missing Vest", type: "warning" },
  { id: "ALT-1044", time: "13:58:12", cam: "CAM-01", issue: "Unauthorized Area", type: "danger" },
  { id: "ALT-1045", time: "13:42:55", cam: "CAM-05", issue: "Missing Helmet", type: "warning" },
  { id: "ALT-1046", time: "13:30:10", cam: "CAM-02", issue: "Missing Vest", type: "warning" },
];

export default function CommanderDashboard() {
  return (
    <div className="mx-auto max-w-[1440px] space-y-6 animate-fade-in relative">
      
      {/* Background ambient glow */}
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-accent/5 rounded-full blur-[100px] pointer-events-none -z-10" />

      {/* Top Section: Telemetry Cards */}
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4 stagger-1">
        {telemetryStats.map((stat, i) => {
          const Icon = stat.icon;
          return (
            <div key={i} className={`glass-1 p-5 relative overflow-hidden group ${stat.isCritical ? 'border-danger/40 shadow-[0_0_15px_rgba(248,81,73,0.1)]' : ''}`}>
              <div className="flex items-start justify-between">
                <div>
                  <h3 className="text-muted text-[11px] font-bold tracking-widest uppercase font-mono mb-2">
                    {stat.label}
                  </h3>
                  <div className="text-foreground font-mono text-3xl font-bold flex items-baseline gap-1">
                    {stat.value}
                    {stat.isCritical && (
                      <span className="w-2 h-2 rounded-full bg-danger animate-pulse-glow" />
                    )}
                  </div>
                </div>
                <div className={`p-2 rounded bg-surface ${stat.color} border border-border-subtle group-hover:scale-110 transition-transform`}>
                  <Icon className="h-5 w-5" />
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Main Area: Grid Layout */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        
        {/* Left 2/3: Live Sentinel View */}
        <div className="lg:col-span-2 glass-2 p-1 stagger-2 relative">
          {/* Header */}
          <div className="px-5 py-4 border-b border-border-subtle flex items-center justify-between bg-surface-elevated/50 backdrop-blur-md rounded-t">
            <h2 className="text-sm font-bold tracking-widest uppercase flex items-center gap-2">
              <Video className="h-4 w-4 text-accent" />
              Live Sentinel View
            </h2>
            <div className="flex items-center gap-2">
              <span className="flex h-2 w-2 rounded-full bg-accent animate-pulse-glow"></span>
              <span className="text-[10px] font-mono text-accent tracking-widest uppercase">Recording</span>
            </div>
          </div>
          
          {/* Video Grid */}
          <div className="grid grid-cols-2 gap-1 p-1 bg-background/50">
            {liveFeeds.map((feed) => (
              <div key={feed.id} className="relative aspect-video bg-[#0a0c10] border border-border-subtle rounded overflow-hidden group">
                {/* Mock Video Placeholder */}
                <div className="absolute inset-0 bg-gradient-to-br from-surface to-background opacity-80" />
                
                {/* YOLO Bounding Box Overlay Mock */}
                <div className="absolute top-1/4 left-1/4 right-1/3 bottom-1/4 border-2 border-accent/60 shadow-[0_0_10px_rgba(0,240,255,0.4)] rounded-sm group-hover:border-accent transition-colors">
                  <div className="absolute -top-6 left-[-2px] bg-accent/20 border border-accent/50 text-accent font-mono text-[9px] px-1 py-0.5 rounded-sm backdrop-blur-sm whitespace-nowrap">
                    Helmet: {feed.helmet}% | Vest: {feed.vest}%
                  </div>
                </div>

                <div className="absolute bottom-2 left-2 flex flex-col gap-1">
                  <span className="bg-surface/80 border border-border text-foreground font-mono text-[10px] px-2 py-0.5 rounded backdrop-blur-md">
                    {feed.id} • {feed.location}
                  </span>
                </div>
                
                {feed.status === 'warning' && (
                  <div className="absolute top-2 right-2 flex h-3 w-3">
                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-warning opacity-75"></span>
                    <span className="relative inline-flex rounded-full h-3 w-3 bg-warning"></span>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>

        {/* Right 1/3: Real-time Safety Stream */}
        <div className="glass-2 flex flex-col stagger-3">
          <div className="px-5 py-4 border-b border-border-subtle bg-surface-elevated/50 backdrop-blur-md rounded-t">
            <h2 className="text-sm font-bold tracking-widest uppercase flex items-center gap-2">
              <Activity className="h-4 w-4 text-warning" />
              Safety Stream
            </h2>
          </div>
          <div className="flex-1 overflow-y-auto p-2 space-y-1">
            {liveAlerts.map((alert) => (
              <div key={alert.id} className="p-3 bg-surface hover:bg-surface-elevated border border-transparent hover:border-border-subtle rounded transition-colors group">
                <div className="flex justify-between items-start mb-2">
                  <div className="flex items-center gap-2">
                    <span className={`h-1.5 w-1.5 rounded-full ${alert.type === 'danger' ? 'bg-danger shadow-[0_0_5px_rgba(248,81,73,0.8)]' : 'bg-warning shadow-[0_0_5px_rgba(255,107,0,0.8)]'}`} />
                    <span className="text-foreground text-sm font-medium">{alert.issue}</span>
                  </div>
                  <span className="text-muted font-mono text-[10px] flex items-center gap-1">
                    <Clock className="h-3 w-3" />
                    {alert.time}
                  </span>
                </div>
                <div className="flex justify-between items-end">
                  <span className="text-muted font-mono text-[11px] bg-background/50 px-1.5 py-0.5 rounded">
                    {alert.cam}
                  </span>
                  <button className="text-[10px] font-mono tracking-wider uppercase text-accent opacity-0 group-hover:opacity-100 transition-opacity flex items-center gap-1 hover:underline">
                    <Eye className="h-3 w-3" /> Snapshot
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Bottom Section: Charts */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2 stagger-4 pb-10">
        
        {/* Left Chart */}
        <div className="glass-1 p-5">
          <div className="flex items-center justify-between mb-6">
            <h3 className="text-sm font-bold tracking-widest uppercase flex items-center gap-2">
              <BarChart className="h-4 w-4 text-accent" />
              Model Accuracy (24h)
            </h3>
            <span className="text-[10px] font-mono text-accent bg-accent/10 border border-accent/20 px-2 py-0.5 rounded">LIVE</span>
          </div>
          {/* Mock Line Chart */}
          <div className="h-40 w-full relative flex items-end justify-between px-2">
            {/* Grid lines */}
            <div className="absolute inset-0 flex flex-col justify-between border-l border-b border-border-subtle pb-6 pl-2">
              <div className="w-full h-[1px] bg-border-subtle/50" />
              <div className="w-full h-[1px] bg-border-subtle/50" />
              <div className="w-full h-[1px] bg-border-subtle/50" />
              <div className="w-full h-[1px] bg-border-subtle/50" />
            </div>
            {/* SVG Line mock */}
            <svg className="absolute inset-0 h-full w-full overflow-visible preserve-3d pb-6 pl-2 z-10" viewBox="0 0 100 100" preserveAspectRatio="none">
              <path d="M0,80 Q20,70 40,85 T70,50 T100,10" fill="none" stroke="var(--accent)" strokeWidth="2" className="drop-shadow-[0_0_8px_rgba(0,240,255,0.6)]" />
              <path d="M0,80 Q20,70 40,85 T70,50 T100,10 L100,100 L0,100 Z" fill="url(#neon-gradient)" stroke="none" opacity="0.1" />
              <defs>
                <linearGradient id="neon-gradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="var(--accent)" />
                  <stop offset="100%" stopColor="transparent" />
                </linearGradient>
              </defs>
            </svg>
            <div className="absolute bottom-0 left-2 right-0 flex justify-between text-[10px] font-mono text-muted">
              <span>00:00</span>
              <span>06:00</span>
              <span>12:00</span>
              <span>18:00</span>
              <span>24:00</span>
            </div>
          </div>
        </div>

        {/* Right Chart */}
        <div className="glass-1 p-5">
          <div className="flex items-center justify-between mb-6">
            <h3 className="text-sm font-bold tracking-widest uppercase flex items-center gap-2">
              <AlertTriangle className="h-4 w-4 text-warning" />
              Violations by Type
            </h3>
            <span className="text-[10px] font-mono text-muted bg-surface border border-border px-2 py-0.5 rounded">TODAY</span>
          </div>
          {/* Mock Bar Chart */}
          <div className="h-40 w-full relative flex items-end justify-around pb-6 px-4">
            <div className="absolute inset-0 border-l border-b border-border-subtle pb-6 pl-2" />
            
            <div className="relative h-[80%] w-12 bg-warning/20 border border-warning/50 rounded-t-sm group hover:bg-warning/30 transition-colors">
              <div className="absolute -top-6 left-1/2 -translate-x-1/2 text-warning font-mono text-[10px] opacity-0 group-hover:opacity-100 transition-opacity">142</div>
            </div>
            <div className="relative h-[65%] w-12 bg-warning/20 border border-warning/50 rounded-t-sm group hover:bg-warning/30 transition-colors">
              <div className="absolute -top-6 left-1/2 -translate-x-1/2 text-warning font-mono text-[10px] opacity-0 group-hover:opacity-100 transition-opacity">98</div>
            </div>
            <div className="relative h-[30%] w-12 bg-danger/20 border border-danger/50 rounded-t-sm group hover:bg-danger/30 transition-colors">
              <div className="absolute -top-6 left-1/2 -translate-x-1/2 text-danger font-mono text-[10px] opacity-0 group-hover:opacity-100 transition-opacity">45</div>
            </div>

            <div className="absolute bottom-0 left-2 right-0 flex justify-around text-[10px] font-mono text-muted">
              <span>No Helmet</span>
              <span>No Vest</span>
              <span>Zone Breach</span>
            </div>
          </div>
        </div>

      </div>
    </div>
  );
}
