"""
Thermal / energy-balance model for the Aqualoop process tank.

The tank is treated as a single well-mixed thermal mass. Starting from an
energy balance on a control volume whose mass changes as water flows in
and out (m = rho * A * h):

    d(m cp T)/dt = rho*Qin*cp*T_in - rho*Qout*cp*T + Q_heater - Q_loss

Expanding the left side as m*cp*dT/dt + cp*T*dm/dt and substituting the
continuity relation dm/dt = rho*(Qin - Qout), the rho*Qout*cp*T terms
cancel and the balance reduces to

    m * cp * dT/dt = rho * Qin * cp * (T_in - T) + Q_heater - Q_loss

which is what step_temperature integrates below. This is also the
mechanism that couples the level loop to the temperature loop: when the
pump runs harder to hold the level setpoint, more reservoir-temperature
water enters the tank, and that shows up directly as the
rho*Qin*cp*(T_in - T) term, a thermal disturbance the PID has to reject.
In practice this inflow term is usually a bigger source of heat loss than
Q_loss to ambient air, since even a modest pump flow moves more thermal
energy than passive convection off the water surface.
"""

from src.simulation.configuration import ThermalConfig, TankConfig

MIN_MASS_KG = 0.05  # floor so dT/dt does not blow up as the tank runs low


def heater_power_w(command_pct: float, cfg: ThermalConfig) -> float:
    command_pct = max(0.0, min(100.0, command_pct))
    return cfg.heater_power_w * command_pct / 100.0


def temperature_derivative(temp_c: float, height_m: float, qin_m3s: float,
                            heater_cmd_pct: float,
                            thermal_cfg: ThermalConfig, tank_cfg: TankConfig) -> float:
    """dT/dt for the process tank at the current state."""
    mass_kg = thermal_cfg.water_density_kgm3 * tank_cfg.area_m2 * max(height_m, 0.0)
    mass_kg = max(mass_kg, MIN_MASS_KG)

    q_heater = heater_power_w(heater_cmd_pct, thermal_cfg)
    q_loss = thermal_cfg.heat_loss_coeff_wk * (temp_c - thermal_cfg.ambient_temp_c)
    q_inflow = (thermal_cfg.water_density_kgm3 * qin_m3s * thermal_cfg.specific_heat_jkgk
                * (thermal_cfg.reservoir_temp_c - temp_c))

    return (q_inflow + q_heater - q_loss) / (mass_kg * thermal_cfg.specific_heat_jkgk)


def step_temperature(temp_c: float, height_m: float, qin_m3s: float,
                      heater_cmd_pct: float, dt_s: float,
                      thermal_cfg: ThermalConfig, tank_cfg: TankConfig) -> float:
    """Advance the water temperature by one explicit Euler step."""
    dTdt = temperature_derivative(temp_c, height_m, qin_m3s, heater_cmd_pct,
                                   thermal_cfg, tank_cfg)
    return temp_c + dTdt * dt_s
