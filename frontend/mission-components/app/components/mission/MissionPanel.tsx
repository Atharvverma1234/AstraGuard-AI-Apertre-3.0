'use client';

import { useState, useEffect, useRef } from 'react';
import { Satellite, MissionPhase } from '../../types/mission';
import missionData from '../../mocks/mission.json';
import { SatelliteCard } from './SatelliteCard';
import { PhaseTimeline } from './PhaseTimeline';

const cycleTasks: Record<string, string[]> = {
  'sat-001': ['Data Dump', 'Status Check', 'Calibration'],
  'sat-002': ['Orbit Adjust', 'Drift Correction', 'Standby'],
  'sat-003': ['Imaging', 'Data Capture', 'Processing'],
  'sat-004': ['Standby', 'Monitoring', 'Idle'],
  'sat-005': ['Offline', 'Offline', 'Offline'],
  'sat-006': ['Telemetry', 'Signal Boost', 'Transmission'],
};

export const MissionPanel: React.FC<{ onSelectSatellite?: (satId: string) => void }> = ({ onSelectSatellite }) => {
  const [satellites, setSatellites] = useState<Satellite[]>(missionData.satellites as Satellite[]);
  const [phases, setPhases] = useState<MissionPhase[]>(missionData.phases as MissionPhase[]);
  const [selectedSatId, setSelectedSatId] = useState<string | null>(null);
  const taskIndicesRef = useRef<Record<string, number>>({});

  const selectedSat = satellites.find((s) => s.id === selectedSatId) || null;

  useEffect(() => {
    missionData.satellites.forEach((sat) => {
      taskIndicesRef.current[sat.id] = 0;
    });
  }, []);

  useEffect(() => {
    const interval = setInterval(() => {
      setSatellites((prev) =>
        prev.map((sat) => {
          const tasks = cycleTasks[sat.id] || ['Data Dump'];
          taskIndicesRef.current[sat.id] = ((taskIndicesRef.current[sat.id] || 0) + 1) % tasks.length;
          return {
            ...sat,
            task: tasks[taskIndicesRef.current[sat.id]],
            latency:
              sat.latency === 0 ? 0 : Math.max(20, sat.latency + (Math.random() - 0.5) * 20),
          };
        })
      );

      setPhases((prev) => {
        const activeIdx = prev.findIndex((p) => p.isActive);
        const nextIdx = (activeIdx + 1) % prev.length;
        return prev.map((phase, i) => ({
          ...phase,
          isActive: i === nextIdx,
          progress:
            i === nextIdx && phase.progress < 100 ? Math.min(100, phase.progress + 2) : phase.progress,
        }));
      });
    }, 10000);

    return () => clearInterval(interval);
  }, []);

  return (
    <div className="space-y-8 max-w-7xl mx-auto">
      <section className="glow-teal/50">
        <h2 className="text-2xl font-bold mb-6 text-teal-400 glow-teal flex items-center">
          Satellite Status{' '}
          <span className="ml-2 text-sm bg-teal-500/20 px-3 py-1 rounded-full">
            {satellites.filter((s) => s.status === 'Nominal').length}/6 Nominal
          </span>
        </h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-4">
          {satellites.map((sat) => (
            <SatelliteCard
              key={sat.id}
              {...sat}
              isSelected={selectedSatId === sat.id}
              onClick={() => {
                setSelectedSatId(sat.id);
                onSelectSatellite?.(sat.orbitSlot);
              }}
            />
          ))}
        </div>
      </section>

      {selectedSat && (
        <div className="p-6 bg-black/50 backdrop-blur-xl rounded-2xl border border-teal-500/30 glow-teal">
          <h3 className="text-xl font-bold text-teal-400 mb-4">Selected: {selectedSat.orbitSlot}</h3>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
            <div>
              <span className="opacity-75">Status:</span>
              <div className="font-mono text-teal-400">{selectedSat.status}</div>
            </div>
            <div>
              <span className="opacity-75">Latency:</span>
              <div className="font-mono text-teal-400">{Math.round(selectedSat.latency)}ms</div>
            </div>
            <div>
              <span className="opacity-75">Task:</span>
              <div className="font-mono text-teal-400">{selectedSat.task}</div>
            </div>
            <div>
              <span className="opacity-75">Signal:</span>
              <div className="font-mono text-teal-400">{selectedSat.signal}%</div>
            </div>
          </div>
        </div>
      )}

      <PhaseTimeline phases={phases} />
    </div>
  );
};
