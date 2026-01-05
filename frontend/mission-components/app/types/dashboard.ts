export interface MissionState {
  name: string;
  phase: string;
  status: 'Nominal' | 'Degraded' | 'Critical';
  updated: string;
  anomalyCount: number;
}
