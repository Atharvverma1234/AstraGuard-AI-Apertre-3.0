export interface KPI {
  id: string;           // "uptime"
  label: string;        // "Uptime"
  value: string;        // "99.87%"
  trend: number;        // +0.02 or -0.15
  progress: number;     // 99.87
  unit: string;         // "%" | "ms" | "req/s"
}

export interface BreakerState {
  from: string;         // "DB"
  to: string;           // "Telemetry" 
  state: 'Open' | 'Half' | 'Tripped';
  duration: string;     // "14m32s"
  reason: string;       // "Timeout"
}
