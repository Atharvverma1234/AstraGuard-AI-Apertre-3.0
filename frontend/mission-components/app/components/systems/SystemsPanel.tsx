import React, { useState, useEffect } from 'react';
import systemsData from '../../mocks/systems.json';
import { KPICard } from './KPICard';
import { BreakerMatrix } from './BreakerMatrix';
import { KPI, BreakerState } from '../../types/systems';

export const SystemsPanel: React.FC = () => {
    const [kpis, setKpis] = useState<KPI[]>(systemsData.kpis as KPI[]);
    const [breakers, setBreakers] = useState<BreakerState[]>(systemsData.breakers as BreakerState[]);

    // 30s drift simulation
    useEffect(() => {
        const interval = setInterval(() => {
            setKpis(prev => prev.map(kpi => ({
                ...kpi,
                value: kpi.id === 'latency'
                    ? `${Math.floor(Math.max(120, 142 + (Math.random() - 0.5) * 20))}ms`
                    : kpi.id === 'cpu'
                        ? `${Math.floor(47 + (Math.random() - 0.5) * 10)}%`
                        : kpi.value,
                trend: (Math.random() - 0.5) * (kpi.id === 'latency' ? 10 : 1),
                progress: kpi.id === 'latency' ? Math.min(100, Math.max(50, 71 + (Math.random() - 0.5) * 10)) : kpi.progress
            })));
        }, 30000);

        return () => clearInterval(interval);
    }, []);

    return (
        <div className="space-y-8 max-w-7xl mx-auto">
            {/* KPI Row */}
            <section className="glow-magenta/50">
                <h2 className="text-2xl font-bold mb-8 text-magenta-400 glow-magenta">System Health Overview</h2>
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-6">
                    {kpis.map(kpi => <KPICard key={kpi.id} {...kpi} />)}
                </div>
            </section>

            {/* Breaker Matrix */}
            <BreakerMatrix breakers={breakers} services={systemsData.services} />
        </div>
    );
};
