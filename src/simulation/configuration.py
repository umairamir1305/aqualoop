"""
Central configuration for the Aqualoop virtual plant.

Every physical, sensor, controller and simulation parameter lives here.
Defaults are either standard physical constants (water density, gravity),
reasonable dimensions for a table-top tank, or documented engineering
assumptions used because no physical Aqualoop hardware exists to measure
a value from. Each assumption is noted in a comment next to the parameter
it affects.

Nothing in the plant or instrumentation code should hard-code a number
that belongs here. Change a value in one of these dataclasses and it
propagates through the whole simulation.
"""

import copy
from dataclasses import dataclass, field


@dataclass
class TankConfig:
    """Process tank geometry and gravity drain."""
    area_m2: float = 0.045           # assumption: roughly 21 cm x 21 cm tank, table-top scale
    height_m: float = 0.30           # usable height before overflow
    outlet_area_m2: float = 1.2e-6   # assumption: narrow gravity drain, about 1.2 mm diameter
    discharge_coeff: float = 0.62    # sharp-edged orifice, standard textbook value
    min_safe_level_m: float = 0.03   # heater is interlocked off below this level


@dataclass
class PumpConfig:
    """Inlet pump: maps a 0-100% command to a volumetric flow rate."""
    max_flow_m3s: float = 6.0e-6      # assumption: small dosing-style pump, ~0.36 L/min at full command
    dead_zone_pct: float = 8.0        # assumption: small DC pump needs ~8% duty before it overcomes static friction
    nonlinearity_gamma: float = 1.25  # >1: flow builds slower than command near the low end


@dataclass
class ThermalConfig:
    """Energy balance parameters for the process tank."""
    water_density_kgm3: float = 997.0
    specific_heat_jkgk: float = 4186.0
    heater_power_w: float = 180.0      # assumption: small immersion heater
    heat_loss_coeff_wk: float = 0.6    # assumption: lumped convective loss to ambient air, lightly insulated tank
    ambient_temp_c: float = 25.0
    reservoir_temp_c: float = 25.0     # temperature of water arriving through the pump

    # A note on why the pump's max flow and the drain's orifice size are both
    # small: holding a steady water level means continuously replacing
    # whatever leaves through the gravity drain, and that replacement water
    # arrives at reservoir_temp_c. Even a modest continuous flow carries a
    # large thermal cost, because rho*Q*cp is large for water. A drain sized
    # like a garden-hose fitting would need a heater far bigger than a
    # student project can realistically use just to keep up with the cold
    # water passing through, before it even starts raising the temperature.
    # Sizing the drain and pump small keeps the required makeup flow (and its
    # thermal cost) in a range a 150-200 W heater can dominate, which is the
    # regime a real small-scale version of this plant would need to operate
    # in as well.


@dataclass
class SensorConfig:
    """Shared shape for one virtual sensor's imperfections."""
    scale: float = 1.0
    bias: float = 0.0
    noise_std: float = 0.0
    resolution: float = 0.0    # 0 disables quantization
    delay_steps: int = 0       # transport/response delay, in simulation steps
    dropout_prob: float = 0.0  # probability a reading is missed on a given step
    stuck: bool = False        # fault: sensor frozen at its last good value


@dataclass
class TemperatureSensorConfig(SensorConfig):
    noise_std: float = 0.05     # assumption: DS18B20-like, quiet but not silent
    resolution: float = 0.0625  # DS18B20 12-bit resolution step
    delay_steps: int = 2        # assumption: thermal probe response lag


@dataclass
class LevelSensorConfig(SensorConfig):
    noise_std: float = 2.0e-3         # metres. assumption: ultrasonic, noisier than the probe
    resolution: float = 1.0e-3        # about 1 mm
    delay_steps: int = 1
    outlier_prob: float = 0.01        # assumption: occasional ultrasonic echo glitch
    outlier_magnitude: float = 0.012  # size of a glitch, metres


@dataclass
class FlowSensorConfig(SensorConfig):
    noise_std: float = 1.0e-7                 # m3/s
    resolution: float = 0.0
    delay_steps: int = 1
    min_detectable_flow_m3s: float = 3.0e-7   # assumption: turbine stall, reads zero below this


@dataclass
class PIDConfig:
    """Temperature controller gains and limits.

    Defaults come from src/control/tuning.py applied to an open-loop step
    test of the thermal plant (see docs/tuning notes): identified process
    gain 0.325 degC per %, tau approximately 4160 s, then SIMC tuning with
    lambda = tau/4. These are the "final selected gains" after checking the
    closed-loop step response; see AqualoopConfig docstring for the
    identified-vs-final gain distinction.
    """
    kp: float = 11.2204
    ki: float = 0.0027
    kd: float = 56.102
    output_min: float = 0.0
    output_max: float = 100.0
    derivative_filter_tau: float = 2.0    # low-pass time constant on the derivative term, seconds
    derivative_on_measurement: bool = True


@dataclass
class PIConfig:
    """Level controller gains and limits.

    Defaults come from the same step-test-and-SIMC procedure as the
    temperature PID: identified process gain 0.00329 m per %, tau
    approximately 3231 s, dead time approximately 88 s.
    """
    kp: float = 1095.0378
    ki: float = 0.3389
    output_min: float = 0.0
    output_max: float = 100.0


@dataclass
class SimulationConfig:
    dt_s: float = 1.0
    duration_s: float = 9000.0   # 2.5 hours simulated; the thermal loop is slow, see ThermalConfig note
    random_seed: int = 42
    mode: str = "realistic"      # "ideal" or "realistic"


@dataclass
class AqualoopConfig:
    tank: TankConfig = field(default_factory=TankConfig)
    pump: PumpConfig = field(default_factory=PumpConfig)
    thermal: ThermalConfig = field(default_factory=ThermalConfig)
    temperature_sensor: TemperatureSensorConfig = field(default_factory=TemperatureSensorConfig)
    level_sensor: LevelSensorConfig = field(default_factory=LevelSensorConfig)
    flow_sensor: FlowSensorConfig = field(default_factory=FlowSensorConfig)
    temperature_pid: PIDConfig = field(default_factory=PIDConfig)
    level_pi: PIConfig = field(default_factory=PIConfig)
    simulation: SimulationConfig = field(default_factory=SimulationConfig)

    def ideal(self) -> "AqualoopConfig":
        """Return a copy with sensor imperfections and actuator quirks switched off.

        Used for the IDEAL MODE vs REALISTIC MODE comparison: same plant,
        same controllers, the only difference is whether the instrumentation
        and actuators behave like textbook components or like the imperfect
        hardware the physical Aqualoop concept would actually have.
        """
        cfg = copy.deepcopy(self)
        for sensor in (cfg.temperature_sensor, cfg.level_sensor, cfg.flow_sensor):
            sensor.noise_std = 0.0
            sensor.bias = 0.0
            sensor.resolution = 0.0
            sensor.delay_steps = 0
            sensor.dropout_prob = 0.0
            sensor.stuck = False
        cfg.level_sensor.outlier_prob = 0.0
        cfg.pump.dead_zone_pct = 0.0
        cfg.pump.nonlinearity_gamma = 1.0
        cfg.simulation.mode = "ideal"
        return cfg
