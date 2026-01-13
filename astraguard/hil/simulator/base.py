"""
Abstract base class and utilities for satellite HIL simulation.

This module provides the foundational SatelliteSimulator abstract base class
that powers all HIL testing for AstraGuard swarm behaviors.
"""

from abc import ABC, abstractmethod
from typing import List, Optional
from datetime import datetime
from ..schemas.telemetry import (
    TelemetryPacket,
    AttitudeData,
    PowerData,
    ThermalData,
    OrbitData,
)


class SatelliteSimulator(ABC):
    """
    Abstract base class for all CubeSat HIL simulation.
    
    Defines the core interface that all satellite simulator implementations must follow,
    including telemetry generation, fault injection, and lifecycle management.
    """
    
    def __init__(self, sat_id: str):
        """
        Initialize a satellite simulator.
        
        Args:
            sat_id: Unique identifier for this satellite
        """
        self.sat_id = sat_id
        self._running = False
        self._telemetry_history: List[TelemetryPacket] = []
    
    @abstractmethod
    async def generate_telemetry(self) -> TelemetryPacket:
        """
        Generate one telemetry packet for this satellite.
        
        Returns:
            TelemetryPacket with current satellite state
        """
        pass
    
    @abstractmethod
    async def inject_fault(
        self, 
        fault_type: str, 
        severity: float = 1.0, 
        duration: float = 60.0
    ) -> None:
        """
        Inject configurable fault into satellite simulation.
        
        Args:
            fault_type: Type of fault to inject (e.g., 'power_brownout', 'thermal_spike')
            severity: Fault severity on scale 0.0-1.0
            duration: Fault duration in seconds
        """
        pass
    
    def start(self) -> None:
        """Mark simulator as running (for orchestration)."""
        self._running = True
    
    def stop(self) -> None:
        """Mark simulator as stopped."""
        self._running = False
    
    def get_telemetry_history(self) -> List[TelemetryPacket]:
        """
        Get copy of telemetry history.
        
        Returns:
            List of all recorded TelemetryPackets
        """
        return self._telemetry_history.copy()
    
    def record_telemetry(self, packet: TelemetryPacket) -> None:
        """
        Internal method: append telemetry packet to history.
        
        Args:
            packet: TelemetryPacket to record
        """
        self._telemetry_history.append(packet)


class StubSatelliteSimulator(SatelliteSimulator):
    """
    Temporary concrete implementation of SatelliteSimulator for testing.
    
    Generates realistic LEO telemetry values and simulates fault states.
    This stub will be replaced by specialized implementations in subsequent PRs.
    """
    
    def __init__(self, sat_id: str):
        """Initialize stub simulator."""
        super().__init__(sat_id)
        self._fault_active = False
        self._fault_type: Optional[str] = None
    
    async def generate_telemetry(self) -> TelemetryPacket:
        """
        Generate LEO satellite telemetry with production schemas.
        
        Returns telemetry with voltage/SOC drop and thermal warning when fault is active.
        """
        import random
        
        timestamp = datetime.now()
        
        # Simulate fault effects across multiple subsystems
        if self._fault_active and self._fault_type == "power_brownout":
            battery_voltage = 6.2
            battery_soc = 0.45
            thermal_status = "warning"
            battery_temp = 25.2  # Raised during fault
        else:
            battery_voltage = 8.4  # Nominal LiIon voltage
            battery_soc = 0.87
            thermal_status = "nominal"
            battery_temp = 15.2
        
        # Attitude: near nadir pointing
        attitude = AttitudeData(
            quaternion=[0.707, 0.01, 0.02, 0.03],
            angular_velocity=[0.001, 0.002, 0.001],
            nadir_pointing_error_deg=random.uniform(0.1, 2.0)
        )
        
        # Power: battery + solar
        power = PowerData(
            battery_voltage=battery_voltage,
            battery_soc=battery_soc,
            solar_current=0.8,
            load_current=0.3
        )
        
        # Thermal: battery + EPS temps
        thermal = ThermalData(
            battery_temp=battery_temp,
            eps_temp=22.1,
            status=thermal_status
        )
        
        # Orbit: LEO parameters
        orbit = OrbitData(
            altitude_m=520000 + random.uniform(-1000, 1000),
            ground_speed_ms=7660,
            true_anomaly_deg=random.uniform(0, 360)
        )
        
        # Build packet
        packet = TelemetryPacket(
            timestamp=timestamp,
            satellite_id=self.sat_id,
            attitude=attitude,
            power=power,
            thermal=thermal,
            orbit=orbit,
            mission_mode="nominal",
            ground_contact=random.choice([True, False])
        )
        
        self.record_telemetry(packet)
        return packet
    
    async def inject_fault(
        self, 
        fault_type: str, 
        severity: float = 1.0, 
        duration: float = 60.0
    ) -> None:
        """
        Inject fault into stub simulator.
        
        Args:
            fault_type: Type of fault
            severity: Fault severity (0.0-1.0)
            duration: Fault duration in seconds
        """
        self._fault_active = True
        self._fault_type = fault_type
        print(
            f"Sat {self.sat_id}: Injected {fault_type} fault "
            f"(severity={severity}, duration={duration}s)"
        )
