const {
  h1, h2, h3, p, eq, bullets, figure, table, hr, runs,
  Paragraph, TextRun, AlignmentType, PageBreak,
} = require("./helpers.js");

// =======================================================================
// 7. DISTURBANCES AND FAULT INJECTION
// =======================================================================

const disturbancesAndFaults = [
  h1("7. Disturbances and Fault Injection", "sec7"),
  p("A disturbance is something that happens to the process from the outside. A fault is something wrong with a piece of equipment. Both are implemented the same way: a small object with a start time, a duration and a magnitude, whose apply_on_step method mutates the live plant or sensor objects while it is active, called once per timestep through an on_step hook in the simulation engine. This means a disturbance or fault genuinely changes the equations being integrated for as long as it is active, rather than being an annotation added to a plot afterward."),
  h2("7.1 Disturbances"),
  p("Three kinds are implemented, covering both loops:"),
  ...bullets([
    "ambient_temp_step: the ambient air temperature changes, for example a draft or a door left open near the tank",
    "inflow_temp_step: the reservoir's water temperature changes, for example a second process drawing from the same reservoir",
    "extra_outflow: an additional drain flow on top of the normal gravity outlet, for example a small leak or someone drawing water off the tank by hand",
  ]),
  h2("7.2 Faults"),
  p("Eight kinds are implemented:"),
  ...bullets([
    "sensor_bias, sensor_noise, sensor_dropout, sensor_stuck, targeting a named sensor (temperature, level or flow)",
    "pump_effectiveness and heater_effectiveness, which scale an actuator's real output below what it was commanded, standing in for a worn pump or a degraded heating element",
    "extra_heat_loss, which adds to the ambient heat loss coefficient, standing in for lost insulation",
    "extra_outflow, an uncommanded drain flow, the fault-side equivalent of the disturbance of the same name",
  ]),
  p("The fault and disturbance extra_outflow kinds share the same underlying plant attribute, so a single simulation run should schedule one or the other for that particular effect, not both at once; scheduling both would let the second one silently overwrite the first. This is a real limitation, not a hidden one, and it is listed again in section 12."),
];

// =======================================================================
// 8. SIMULATION METHODOLOGY
// =======================================================================

const methodology = [
  h1("8. Simulation Methodology", "sec8"),
  p("The simulation engine steps the closed loop forward in discrete time. At each step it reads the plant's true state, generates sensor measurements from it, applies filtering, lets the controllers compute new actuator commands, logs every quantity, and only then advances the plant physics using those commands. This ordering matters: a controller can only act on information a real controller would actually have, the filtered and delayed measurement, not the true state directly."),
  p("Both the level and thermal equations are integrated with explicit Euler steps: the next value is the current value plus the rate of change times the timestep. This is appropriate here because both loops' time constants (thousands of seconds, see section 6.3) are far larger than the timestep used (1 s), which keeps the scheme well inside its stability region while staying easy to read and explain. A few sanity checks are enforced directly in the plant code rather than left as an assumption: level is clamped to the physical range of the tank (it cannot go negative or exceed the tank height), and the thermal model's mass term is floored above zero so it cannot divide by a vanishing quantity as the tank runs low."),
  p("Sensor noise is generated from a seeded NumPy random generator (numpy.random.default_rng), so passing the same random_seed reproduces an identical run bit for bit; tests/test_engine.py checks this directly. AqualoopConfig().ideal() returns a copy of the configuration with every sensor's noise, bias, resolution, delay and dropout set to zero, the pump's dead zone and nonlinearity switched off, and the simulation mode label set accordingly, which is what section 14 identifies as the next piece to actually show side by side with the realistic mode in a dashboard."),
];

// =======================================================================
// 9. EXPERIMENTS AND RESULTS
// =======================================================================

const experiments = [
  h1("9. Experiments and Results", "sec9"),
  p("Eleven experiments were run; each saves its own CSV of logged simulation data, a plot, and a JSON summary of the metrics computed from that run. All data produced by these experiments is simulated."),

  h2("9.1 Sensor Calibration"),
  p("Covered in section 5.2 and Table 5. All three sensors show a fitted slope within 0.4% of 1.0 and an intercept close to zero, consistent with sensor models that were configured with a scale of 1.0 and no deliberate bias; the residual error is the sensor's own modeled noise."),

  h2("9.2 Open-Loop Temperature Response"),
  p("Covered in section 6.3 and Figure 2. Stepping the heater command from 20% to 60% with the level loop holding 0.15 m identified the FOPDT model used for tuning."),

  h2("9.3 Closed-Loop Temperature Control"),
  p("Starting cold at 25 degC with a 45 degC setpoint and the level held at 0.15 m (Figure 3):"),
  ...bullets([
    "Rise time (10% to 90%): 3536 s",
    "Overshoot: 8.04%",
    "Settling time (2% band): 11559 s",
    "Steady-state error: 0.129 degC",
    "IAE: 48661, ISE: 455635",
  ]),
  ...figure("experiment_05_closed_loop_temperature_control.png", 480, "Figure 3. Closed-loop temperature control, cold start."),

  h2("9.4 Closed-Loop Level Control"),
  p("Starting at 0.08 m with a setpoint step to 0.20 m (Figure 4):"),
  ...bullets([
    "Rise time (10% to 90%): 1952 s",
    "Overshoot: 0%",
    "Settling time (2% band): 3369 s",
    "Steady-state error: 1.9 mm",
    "IAE: 107.2, ISE: 6.27",
  ]),
  ...figure("experiment_08_closed_loop_level_control.png", 480, "Figure 4. Closed-loop level control, setpoint step."),
  p("The level loop shows no overshoot, consistent with the SIMC tuning choice of lambda = tau/4 (a conservative, non-aggressive closed-loop speed) and with the process's own self-regulating behavior described in section 6.2."),

  h2("9.5 Temperature Disturbance Rejection"),
  p("With the loop holding 45 degC, the reservoir temperature was stepped 15 degC colder for 2000 s, simulating a cold-water surge (Figure 5):"),
  ...bullets([
    "Maximum dip: 5.12 degC",
    "Recovery time after the disturbance ends: 2220 s",
  ]),
  ...figure("experiment_07_temperature_disturbance_rejection.png", 520, "Figure 5. Temperature disturbance rejection, cold-water surge."),

  h2("9.6 Level Disturbance Rejection"),
  p("With the loop holding 0.15 m, an extra drain flow of 2.5e-6 m3/s was applied for 800 s, simulating a manual water draw-off (Figure 6):"),
  ...bullets([
    "Maximum dip: 45.7 mm",
    "Recovery time after the disturbance ends: 3356 s",
  ]),
  ...figure("experiment_09_level_disturbance_rejection.png", 520, "Figure 6. Level disturbance rejection, manual water draw-off."),

  h2("9.7 Coupled Full-System Operation"),
  p("This experiment is the direct demonstration of section 4.3's coupling claim. The temperature loop holds a 45 degC setpoint throughout; at t = 7000 s, only the level setpoint changes, stepping from 0.10 m to 0.20 m. Neither the temperature setpoint nor the temperature controller's gains change at any point (Figure 7):"),
  ...bullets([
    "Temperature immediately before the level setpoint change: 45.14 degC",
    "Temperature dip caused purely by the level change: 7.05 degC",
  ]),
  ...figure("experiment_10_coupled_full_system.png", 460, "Figure 7. Coupled operation: a level setpoint change alone produces a real temperature dip."),
  p("The pump saturates at 100% to move the tank to its new, higher level quickly, and that flow of reservoir-temperature water is what pulls the temperature down. The temperature PID then recovers it over the following few thousand seconds, exactly the pattern described in section 4.3 without any part of it scripted into the experiment."),

  h2("9.8 Controller Comparison: P, PI and PID"),
  p("The same plant, the same starting conditions, and the same proportional and derivative gains were used for all three controllers, varying only which terms were enabled (Figure 8, Table 7):"),
  ...figure("experiment_11_p_pi_pid_comparison.png", 500, "Figure 8. P vs PI vs PID on the temperature loop."),
  caption_placeholder(),
  table(
    ["Controller", "Rise time (s)", "Overshoot (%)", "Settling time (s)", "SSE (degC)", "IAE"],
    [
      ["P", "n/a", "0.0", "n/a", "4.541", "113872"],
      ["PI", "3536", "8.043", "11555", "0.129", "48661"],
      ["PID", "3536", "8.036", "11559", "0.129", "48661"],
    ],
    [1400, 1500, 1500, 1700, 1400, 1300],
  ),
  new Paragraph({ text: "", spacing: { after: 100 } }),
  p("Proportional-only control settles at 40.5 degC and never reaches the 45 degC setpoint or the 2% settling band around it, which is why its rise time and settling time are both undefined rather than zero or large: the response never gets far enough for either to be measured. This is the textbook proportional offset, and it is the direct, quantified reason integral action is in the loop at all. Adding integral action (PI) removes the offset entirely. Adding derivative action on top (PID) changes the response only slightly, overshoot 8.036% against 8.043% for PI alone, which is consistent with this plant having very little real dead time for a derivative term to usefully compensate, as discussed in section 6.3."),
];

function caption_placeholder() {
  return new Paragraph({
    children: [new TextRun({ text: "Table 7. Performance metrics, same plant and starting conditions", italics: true })],
    alignment: AlignmentType.CENTER,
    spacing: { after: 120 },
  });
}

// =======================================================================
// 10. PERFORMANCE ANALYSIS
// =======================================================================

const performanceAnalysis = [
  h1("10. Performance Analysis", "sec10"),
  p("Taken together, the eleven experiments in section 9 exercise every objective set out in section 2. The plant genuinely evolves in time (sections 4, 8), the two loops are coupled through a real, shared physical mechanism rather than by construction (sections 4.3, 9.7), the three sensors fail in different, appropriate ways (section 5.1) and were calibrated the same way real ones would be (section 5.2), both controllers were tuned from identified process data rather than guessed gains (section 6.3), and the disturbance, fault and comparison experiments show the closed loop responding to conditions it was not specifically shaped to handle."),
  p("The clearest single result is the controller comparison in section 9.8: it is not just that PID outperforms P, it is a quantified answer to the question of why PI was chosen for level control and PID for temperature, backed by numbers computed from identical starting conditions rather than asserted from control theory alone. The second clearest result is the coupled-operation experiment in section 9.7, which is the specific piece of behavior the whole plant sizing exercise in section 4.3 was aimed at producing: a level-loop event with a real, measurable consequence on the temperature loop, with no part of the temperature side of the experiment touched."),
  p("The temperature loop's settling time (about 3.2 hours of simulated time) is a genuine property of the identified model, not a simulation artifact: the water mass in a 0.15 m fill of this tank combined with a 180 W heater and the ambient and inflow heat losses in Table 3 produces a time constant over an hour, and settling to within 2% of a step that size at that time constant takes a few time constants. It highlights that thermal processes are slow compared to, for instance, an electrical control loop, and that simulated time is not the same as the wall-clock time actually spent computing it; every result in this report was generated in well under a second of real computation."),
];

// =======================================================================
// 11. VALIDATION AND TESTING
// =======================================================================

const validation = [
  h1("11. Validation and Testing", "sec11"),
  p("55 automated tests (pytest) cover:"),
  ...bullets([
    "Tank level dynamics: the pump curve's dead zone and nonlinearity, the outlet flow relationship, and the level never leaving the tank's physical range",
    "Thermal dynamics: the heater power relationship, convergence to the analytically predicted steady state with no flow, and the level-to-temperature coupling (more inflow of cooler water measurably lowers temperature)",
    "The coupled Plant object, including the dry-run heater interlock",
    "Both controllers: output saturation, anti-windup behavior, manual and automatic mode, bumpless transfer, and (for the PID controller) that acting on the measurement rather than the error avoids a derivative kick on a setpoint step",
    "All three sensors: noise statistics, bias, resolution quantization, delay, and the stuck-value fault",
    "Calibration: recovering a known linear relationship exactly when there is no noise, and that the correction step inverts the fit",
    "The EMA filter: that it reduces noise variance and that a smaller alpha lags a step change more",
    "The disturbance and fault frameworks: that a disturbance changes the plant and then reverts when its window ends, and that a fault shifts a sensor's reading only while active",
    "The closed-loop simulation engine: that both loops reach their setpoints from a cold start, that the same random seed reproduces an identical run, and that ideal mode genuinely disables sensor noise",
    "The performance metrics module, against constructed responses with known analytical answers (for example, a synthetic first-order step whose rise time should equal tau times the natural log of 9)",
  ]),
  p("All 55 pass. Two real bugs were caught and fixed during this process rather than found later: the calibration settling issue described in section 5.2, and an earlier version of the closed-loop temperature test that failed because my first choice of plant parameters (the garden-hose-sized drain described in section 4.3) made the setpoint physically unreachable within the heater's capacity. Both are left in this report as examples of what the test suite and the experiments were actually able to catch, not edited out."),
  p("What has not been validated: there is no physical Aqualoop hardware for this version, so nothing here has been checked against a real measurement. What has been checked is internal consistency (the plant obeys its own equations, sanity limits are respected, calibration recovers a known relationship) and known physics (the thermal steady state matches the analytical prediction for the configured parameters). That distinction is kept deliberately explicit throughout this report and in every generated data file, each of which is labeled SIMULATED DATA."),
];

// =======================================================================
// 12. LIMITATIONS
// =======================================================================

const limitations = [
  h1("12. Limitations", "sec12"),
  ...bullets([
    "No physical hardware exists for this version. Every number in this report is a simulation output, checked against the model's own physics and internal consistency, not against a real measurement.",
    "The FOPDT identification in section 6.3 is a linear approximation of a plant that is genuinely nonlinear (the sqrt(h) outflow relationship, the pump's dead zone and gamma curve). Gains are tuned around one operating point, 0.15 m and 45 degC, and would likely need re-identifying far from it.",
    "The identified dead time (theta) for both loops is small and dominated by instrumentation lag rather than a true transport delay, so it is not a precise physical quantity, only good enough for SIMC tuning to stay numerically well behaved, as discussed in section 6.3.",
    "The exponential moving average filter is a simple first-order filter. A Kalman filter or another model-based observer would likely handle the level sensor's outlier glitches more gracefully than a fixed-alpha average, at the cost of real implementation complexity this project did not take on.",
    "A disturbance and a fault of the extra_outflow kind cannot be scheduled in the same run without one overwriting the other's effect on the plant, since both act on the same underlying attribute (section 7.2).",
    "The heater is modeled as responding to a command instantly; a real immersion heating element has some thermal inertia of its own, which is not modeled separately from the water's thermal mass.",
    "Running the FOPDT identification a second time gives similar but not identical parameters to Table 6, because the level loop's pump command during the step test depends on noisy sensor readings, which feed back into the exact trajectory of the temperature response being identified.",
  ]),
];

// =======================================================================
// 13. INDUSTRIAL RELEVANCE
// =======================================================================

const industrialRelevance = [
  h1("13. Industrial Relevance", "sec13"),
  p("This is a small, single-person student project, not an industrial control system, but the concepts it uses are the same ones a real process plant runs on, just at a much smaller scale. The temperature and level are process variables; the heater and pump commands are manipulated variables; the setpoints are what an operator would enter on an HMI. The virtual sensors stand in for transmitters, the calibration routine for the bench work an instrumentation technician actually does before a transmitter goes into service, and the dry-run heater interlock for the kind of safety interlock a real plant would wire directly into hardware rather than trust to software alone. A PID and a PI loop are still the most common control elements in industrial plants by a wide margin, and the reasoning in section 6 for why level control uses PI while temperature control uses PID reflects a real, common industrial default, not something specific to this project. The disturbance and fault framework in section 7 is a small version of what a plant would use to test alarm and interlock logic before commissioning, and the dashboard planned in section 14 is a small analogue of an HMI or SCADA screen. None of this makes the project industrial-grade; it is a way of connecting a student project to the vocabulary and structure of the field it is drawn from."),
];

// =======================================================================
// 14. FUTURE IMPROVEMENTS
// =======================================================================

const futureImprovements = [
  h1("14. Future Improvements", "sec14"),
  ...bullets([
    "A Streamlit dashboard with a process schematic, live charts, and pages for control engineering, instrumentation, experiments, and fault and disturbance testing",
    "Showing ideal mode and realistic mode side by side, since the configuration already supports it (AqualoopConfig().ideal()) but nothing currently displays the comparison",
    "Relay-feedback auto-tuning (the Astrom-Hagglund method) as a second tuning route, which identifies an ultimate gain and period directly from a limit cycle rather than from a step test, and would make an interesting comparison against the SIMC gains in Table 6",
    "A Kalman filter or similar observer for the level signal, to handle the ultrasonic sensor's outlier glitches without trading off as much lag as a larger EMA alpha currently does",
    "If physical hardware is ever built, comparing real sensor and control data against this model would be the first genuine experimental validation, as opposed to the internal validation described in section 11",
  ]),
];

// =======================================================================
// 15. CONCLUSION
// =======================================================================

const conclusion = [
  h1("15. Conclusion", "sec15"),
  p("Aqualoop, in this virtual form, is a coupled level and temperature process with a real dynamic plant model, three virtual sensors with distinct, documented failure modes, calibration and filtering routines, two controllers tuned from identified process data rather than guessed gains, and a disturbance and fault injection framework that changes the plant's actual equations while a simulation runs. Eleven experiments exercise all of it and produce performance numbers computed directly from simulation output, including a controller comparison that quantifies why PI and PID were chosen where they were, and a coupled-operation experiment that demonstrates the project's central engineering claim, that the level and temperature loops are physically connected, as a measured result rather than an assertion."),
  p("The plant sizing problem in section 4.3, the tuning-method problem in section 6.3, and the calibration and filtering bugs described in sections 5.2 and 5.3 were all real problems that came up during development and were resolved by going back to the physics and the data rather than by adjusting numbers until a plot looked right. What remains, listed in section 14, is mostly interface work: a dashboard to make the existing simulation interactive, not new physics or control theory the project still needs."),
];

// =======================================================================
// APPENDIX A: ENGINEERING ASSUMPTIONS
// =======================================================================

const appendixA = [
  h1("Appendix A: Engineering Assumptions", "secA"),
  p("Every parameter below could not be taken from physical hardware, since none exists for this version, and was instead set to a documented, reasonable value. All are defined in src/simulation/configuration.py."),
  table(
    ["Parameter", "Value", "Reasoning"],
    [
      ["Tank cross-sectional area", "0.045 m2", "Table-top scale, roughly 21 cm x 21 cm"],
      ["Outlet orifice diameter", "about 1.2 mm", "Sized so makeup flow stays within the heater's thermal capacity (section 4.3)"],
      ["Pump maximum flow", "6.0e-6 m3/s (0.36 L/min)", "Small dosing-style pump, sized with the outlet (section 4.3)"],
      ["Pump dead zone", "8% of command", "Static friction in a small DC pump"],
      ["Heater power", "180 W", "Small immersion heater, sized against the sink terms in Table 3"],
      ["Heat loss coefficient", "0.6 W/K", "Lumped convective loss, lightly insulated tank"],
      ["Temperature sensor noise", "0.05 degC std dev", "DS18B20-style reference"],
      ["Level sensor noise", "2.0 mm std dev, 1% outlier chance", "Ultrasonic rangefinder-style reference"],
      ["Flow sensor minimum detectable flow", "3.0e-7 m3/s", "Turbine stall at low flow"],
      ["Derivative filter time constant", "2 s", "Damps noise amplification from differentiating a noisy signal"],
      ["SIMC lambda (both loops)", "tau / 4", "Reasonably brisk, non-aggressive closed-loop speed"],
    ],
    [3000, 2600, 3000],
  ),
];

// =======================================================================
// APPENDIX B: REPOSITORY AND REPRODUCING RESULTS
// =======================================================================

const appendixB = [
  h1("Appendix B: Reproducing These Results", "secB"),
  p("From the project root:"),
  new Paragraph({ children: [new TextRun({ text: "pip install -r requirements.txt", font: "Consolas", size: 19 })] }),
  new Paragraph({ children: [new TextRun({ text: "python3 -m pytest tests/ -q", font: "Consolas", size: 19 })] }),
  new Paragraph({ children: [new TextRun({ text: "python3 -m src.experiments.runner", font: "Consolas", size: 19 })], spacing: { after: 200 } }),
  p("This regenerates every CSV, plot and JSON summary referenced in this report under data/generated/, results/figures/ and results/reports/. Every random draw is seeded (random_seed = 42 by default, in SimulationConfig), so a fresh run reproduces the same numbers for any experiment that does not depend on a second, independent step test's own noisy trajectory (the caveat noted at the end of section 6.3 and in section 12)."),
];

module.exports = {
  disturbancesAndFaults, methodology, experiments, performanceAnalysis,
  validation, limitations, industrialRelevance, futureImprovements,
  conclusion, appendixA, appendixB,
};
