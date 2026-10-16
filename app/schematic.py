"""
Process schematic.

Renders the reservoir, pump, process tank, heater, drain and the three
sensor locations as an SVG, parameterized by the plant's current state.
This is a schematic, not a scale drawing: proportions are chosen for
legibility, not accuracy.
"""

from app.theme import LEVEL, TEMP, TEXT, TEXT_MUTED, BORDER, WARNING, FAULT, PANEL


def _heater_path(x0, x1, y, amplitude=7, turns=7):
    step = (x1 - x0) / turns
    pts = [f"M {x0},{y}"]
    for i in range(turns):
        cx = x0 + step * (i + 0.5)
        cy = y + (amplitude if i % 2 == 0 else -amplitude)
        ex = x0 + step * (i + 1)
        pts.append(f"Q {cx},{cy} {ex},{y}")
    return " ".join(pts)


def render_schematic(level_m: float, temp_c: float, level_setpoint_m: float,
                      temp_setpoint_c: float, tank_height_m: float,
                      heater_pct: float, pump_pct: float, flow_m3s: float,
                      interlock_active: bool = False, width: int = 560) -> str:
    tank_x, tank_y, tank_w, tank_h = 300, 34, 160, 226
    res_x, res_y, res_w, res_h = 40, 196, 110, 64

    level_frac = max(0.0, min(1.0, level_m / tank_height_m))
    fill_h = level_frac * (tank_h - 8)
    fill_y = tank_y + tank_h - 4 - fill_h

    sp_frac = max(0.0, min(1.0, level_setpoint_m / tank_height_m))
    sp_y = tank_y + tank_h - 4 - sp_frac * (tank_h - 8)

    heater_opacity = 0.22 + 0.78 * max(0.0, min(100.0, heater_pct)) / 100.0
    pump_opacity = 0.30 + 0.70 * max(0.0, min(100.0, pump_pct)) / 100.0
    flow_label = f"{flow_m3s * 6.0e7:.1f}" if flow_m3s is not None else "0.0"

    interlock_color = FAULT if interlock_active else TEXT_MUTED
    heater_color = FAULT if interlock_active else TEMP

    svg = f"""
    <svg viewBox="0 0 560 312" width="100%" xmlns="http://www.w3.org/2000/svg"
         font-family="'IBM Plex Mono', monospace">
      <defs>
        <clipPath id="tankClip">
          <rect x="{tank_x + 3}" y="{tank_y + 3}" width="{tank_w - 6}" height="{tank_h - 6}" rx="2"/>
        </clipPath>
      </defs>

      <!-- pipe: reservoir to tank inlet -->
      <path d="M {res_x + res_w - 15},{res_y} V 70 H {tank_x + tank_w/2}"
            fill="none" stroke="{BORDER}" stroke-width="10" stroke-linecap="round"/>
      <path d="M {res_x + res_w - 15},{res_y} V 70 H {tank_x + tank_w/2}"
            fill="none" stroke="{LEVEL}" stroke-width="4" stroke-linecap="round"
            opacity="{pump_opacity:.2f}"/>
      <path d="M {tank_x + tank_w/2},70 V {tank_y}"
            fill="none" stroke="{BORDER}" stroke-width="10" stroke-linecap="round"/>
      <path d="M {tank_x + tank_w/2},70 V {tank_y}"
            fill="none" stroke="{LEVEL}" stroke-width="4" stroke-linecap="round"
            opacity="{pump_opacity:.2f}"/>

      <!-- pump -->
      <circle cx="{res_x + res_w - 15}" cy="130" r="16" fill="{PANEL}" stroke="{BORDER}" stroke-width="2"/>
      <path d="M {res_x + res_w - 15 - 6},135 L {res_x + res_w - 15},121 L {res_x + res_w - 15 + 6},135 Z"
            fill="{LEVEL}" opacity="{pump_opacity:.2f}"/>
      <text x="{res_x + res_w - 15}" y="160" text-anchor="middle" font-size="10" fill="{TEXT_MUTED}">PUMP {pump_pct:.0f}%</text>

      <!-- flow sensor on inlet, positioned clear of the tank body -->
      <circle cx="230" cy="70" r="11" fill="{PANEL}" stroke="{LEVEL}" stroke-width="1.5"/>
      <text x="230" y="74" text-anchor="middle" font-size="10" fill="{LEVEL}">F</text>
      <text x="230" y="52" text-anchor="middle" font-size="9" fill="{TEXT_MUTED}">{flow_label} mL/min</text>

      <!-- reservoir -->
      <rect x="{res_x}" y="{res_y}" width="{res_w}" height="{res_h}" rx="2"
            fill="{PANEL}" stroke="{BORDER}" stroke-width="2"/>
      <rect x="{res_x + 3}" y="{res_y + res_h - 40}" width="{res_w - 6}" height="37"
            fill="{LEVEL}" opacity="0.28"/>
      <text x="{res_x + res_w/2}" y="{res_y - 10}" text-anchor="middle" font-size="10.5"
            fill="{TEXT_MUTED}">RESERVOIR</text>

      <!-- process tank -->
      <rect x="{tank_x}" y="{tank_y}" width="{tank_w}" height="{tank_h}" rx="3"
            fill="{PANEL}" stroke="{BORDER}" stroke-width="2"/>
      <rect x="{tank_x + 3}" y="{fill_y:.1f}" width="{tank_w - 6}" height="{fill_h:.1f}"
            fill="{LEVEL}" opacity="0.30" clip-path="url(#tankClip)"/>

      <!-- level setpoint marker -->
      <line x1="{tank_x - 4}" y1="{sp_y:.1f}" x2="{tank_x + tank_w + 4}" y2="{sp_y:.1f}"
            stroke="{TEXT_MUTED}" stroke-width="1.3" stroke-dasharray="5,4"/>
      <text x="{tank_x + tank_w + 8}" y="{sp_y + 3:.1f}" font-size="9.5" fill="{TEXT_MUTED}">SP {level_setpoint_m:.2f} m</text>

      <!-- heater -->
      <path d="{_heater_path(tank_x + 20, tank_x + tank_w - 20, tank_y + tank_h - 22)}"
            fill="none" stroke="{heater_color}" stroke-width="3.5" stroke-linecap="round"
            opacity="{heater_opacity:.2f}"/>
      <text x="{tank_x + tank_w/2}" y="{tank_y + tank_h - 6}" text-anchor="middle" font-size="9.5"
            fill="{TEXT_MUTED}">HEATER {heater_pct:.0f}%</text>

      <!-- temperature sensor -->
      <circle cx="{tank_x + tank_w - 26}" cy="{tank_y + 60}" r="11" fill="{PANEL}" stroke="{TEMP}" stroke-width="1.5"/>
      <text x="{tank_x + tank_w - 26}" y="{tank_y + 64}" text-anchor="middle" font-size="10" fill="{TEMP}">T</text>

      <!-- level sensor (ultrasonic, top, pointing down) -->
      <rect x="{tank_x + tank_w/2 - 12}" y="{tank_y - 14}" width="24" height="10" rx="2"
            fill="{PANEL}" stroke="{LEVEL}" stroke-width="1.5"/>
      <text x="{tank_x + tank_w/2}" y="{tank_y - 6}" text-anchor="middle" font-size="8.5" fill="{LEVEL}">L</text>

      <!-- tank label + live values -->
      <text x="{tank_x + tank_w/2}" y="{tank_y - 20}" text-anchor="middle" font-size="10.5"
            fill="{TEXT_MUTED}">PROCESS TANK</text>
      <text x="{tank_x + 14}" y="{tank_y + 24}" font-size="15" fill="{TEMP}" font-weight="600">{temp_c:.1f} C</text>
      <text x="{tank_x + 14}" y="{tank_y + 42}" font-size="15" fill="{LEVEL}" font-weight="600">{level_m:.3f} m</text>

      <!-- drain pipe back to reservoir -->
      <path d="M {tank_x + 24},{tank_y + tank_h} V 280 H {res_x + 20} V {res_y + res_h}"
            fill="none" stroke="{BORDER}" stroke-width="9" stroke-linecap="round"/>
      <path d="M {tank_x + 24},{tank_y + tank_h} V 280 H {res_x + 20} V {res_y + res_h}"
            fill="none" stroke="{LEVEL}" stroke-width="3" stroke-linecap="round" opacity="0.35"/>
      <text x="{(tank_x + 24 + res_x + 20)/2}" y="294" text-anchor="middle" font-size="9.5"
            fill="{TEXT_MUTED}">GRAVITY DRAIN</text>

      {'<text x="' + str(tank_x + tank_w/2) + '" y="' + str(tank_y + tank_h + 34) + '" text-anchor="middle" font-size="10" fill="' + FAULT + '" font-weight="600">DRY-RUN INTERLOCK ACTIVE</text>' if interlock_active else ''}
    </svg>
    """
    return svg
