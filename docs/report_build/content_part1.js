const fs = require("fs");
const path = require("path");
const {
  h1, h2, h3, p, eq, bullets, figure, table, hr, runs, caption,
  Document, Packer, Paragraph, TextRun, HeadingLevel, AlignmentType,
  Header, Footer, PageNumber, TableOfContents, PageBreak, LevelFormat,
  convertInchesToTwip,
} = require("./helpers.js");

const mono = (text) => new TextRun({ text, font: "Consolas", size: 19 });
const monoLine = (text) => new Paragraph({ children: [mono(text)], spacing: { after: 0 } });

// =======================================================================
// TITLE PAGE
// =======================================================================

const titlePage = [
  new Paragraph({ text: "", spacing: { before: 2400 } }),
  new Paragraph({
    children: [new TextRun({ text: "AQUALOOP", bold: true, size: 64 })],
    alignment: AlignmentType.CENTER,
    spacing: { after: 240 },
  }),
  new Paragraph({
    children: [new TextRun({ text: "Virtual Multi-Loop Process Control and Instrumentation System", size: 30 })],
    alignment: AlignmentType.CENTER,
    spacing: { after: 480 },
  }),
  new Paragraph({
    children: [new TextRun({ text: "Technical Report", size: 26, italics: true })],
    alignment: AlignmentType.CENTER,
    spacing: { after: 1200 },
  }),
  new Paragraph({
    children: [new TextRun({ text: "Sam", size: 24 })],
    alignment: AlignmentType.CENTER,
    spacing: { after: 80 },
  }),
  new Paragraph({
    children: [new TextRun({ text: "Mechanical Engineering", size: 22 })],
    alignment: AlignmentType.CENTER,
    spacing: { after: 80 },
  }),
  new Paragraph({
    children: [new TextRun({ text: "September 2026", size: 22 })],
    alignment: AlignmentType.CENTER,
    spacing: { after: 1600 },
  }),
  new Paragraph({
    children: [new TextRun({
      text: "Personal project. This is a software-only, simulated implementation. No physical hardware was built or tested for this version.",
      italics: true, size: 20,
    })],
    alignment: AlignmentType.CENTER,
  }),
];

// =======================================================================
// 1. INTRODUCTION
// =======================================================================

const introduction = [
  h1("1. Introduction", "sec1"),
  p("This report documents Aqualoop, a software-based process control and instrumentation project built around a simulated water tank with two coupled feedback loops: water level and water temperature. The project started as a physical table-top plant design for a Measurement and Instrumentation and Control Engineering course, built around an ESP32 microcontroller, a DS18B20 temperature probe, a JSN-SR04T ultrasonic level sensor, a YF-S201 flow sensor, and a PWM-driven pump and heater."),
  p("I decided not to build that hardware version. Instead I built a virtual implementation of the same process architecture: a plant model that evolves according to real differential equations rather than a predetermined curve, virtual sensors with the kind of imperfections real sensors have, calibration and filtering routines, two feedback controllers tuned from an identified process model, a disturbance and fault injection framework, and an experiment suite that exercises all of it and computes performance metrics from the results."),
  p("Nothing physical was built or tested for this version, and nothing in this report claims otherwise. Every number that came out of a simulation run is labeled as simulated data. Where a parameter could not be taken from real hardware, I made an engineering assumption and documented it; the full list is in Appendix A."),
];

// =======================================================================
// 2. PROBLEM DEFINITION AND OBJECTIVES
// =======================================================================

const objectives = [
  h1("2. Problem Definition and Objectives", "sec2"),
  p("The original Aqualoop concept called for a physical table-top plant: a reservoir, a pump, a process tank, a gravity drain, a heater, and enough instrumentation to run a temperature control loop and a level control loop at the same time. Building that plant well means working through a set of problems that show up in real process plants at a much larger scale: how to model a nonlinear process, how to deal with sensors that are noisy, biased, delayed or occasionally wrong, how to tune a controller from data instead of guessing at gains, how a fault in one part of a system shows up somewhere else, and how two loops that look independent on paper end up affecting each other through a shared piece of equipment."),
  p("For the virtual version I set the following objectives:"),
  ...bullets([
    "Build a plant model whose temperature and level actually evolve according to differential equations, not a scripted curve",
    "Give the level and temperature loops a real physical connection to each other, not two independent simulations running side by side",
    "Model three different virtual sensors with different, appropriate failure characteristics",
    "Calibrate those sensors and filter their signals the same way I would for real instrumentation",
    "Implement a PID controller and a PI controller from first principles, including anti-windup and bumpless manual and automatic transfer",
    "Tune both controllers from an identified process model instead of picking gains by feel",
    "Build a disturbance and fault injection framework that changes the plant equations while a simulation is running, not one that overlays an annotation on a plot afterward",
    "Automate the experiments that demonstrate all of the above, and compute performance metrics from the resulting data",
    "Keep the scope realistic for one person to build and understand completely, without machine learning, model predictive control, an industrial protocol stack, or container orchestration the project does not need",
  ]),
];

// =======================================================================
// 3. SYSTEM ARCHITECTURE
// =======================================================================

const architectureTree = [
  "Aqualoop/",
  "  src/",
  "    plant/            tank.py, thermal.py, process.py",
  "    instrumentation/  temperature_sensor.py, level_sensor.py,",
  "                      flow_sensor.py, calibration.py, filtering.py",
  "    control/          pid.py, pi.py, tuning.py",
  "    simulation/       configuration.py, engine.py,",
  "                      disturbances.py, faults.py",
  "    experiments/      experiments.py, runner.py, saving.py",
  "    analysis/         metrics.py",
  "  tests/              55 automated tests",
  "  scripts/            run_demo.py",
  "  data/generated/      experiment CSV output, simulated data",
  "  results/figures/     experiment plots",
  "  results/reports/     experiment JSON summaries",
  "  docs/                this report",
];

const architecture = [
  h1("3. System Architecture", "sec3"),
  p("The project is organized into six layers, each with a single job. Nothing is in one giant script; a change to the pump curve, for example, only touches tank.py and the tests that cover it."),
  ...architectureTree.map(monoLine),
  new Paragraph({ text: "", spacing: { after: 200 } }),
  p([{ t: "plant", b: true }, { t: ": the physical model. " }, { t: "tank.py", i: true }, { t: " holds the level dynamics and the pump curve, " }, { t: "thermal.py", i: true }, { t: " holds the energy balance, " }, { t: "process.py", i: true }, { t: " combines the two into one Plant object and applies the dry-run heater interlock." }]),
  p([{ t: "instrumentation", b: true }, { t: ": the three virtual sensors, the calibration routine, and the exponential moving average filter." }]),
  p([{ t: "control", b: true }, { t: ": the PID and PI controllers, and the tuning module that identifies a process model from a step test and computes gains from it." }]),
  p([{ t: "simulation", b: true }, { t: ": " }, { t: "configuration.py", i: true }, { t: " holds every tunable parameter in one place, " }, { t: "engine.py", i: true }, { t: " runs the closed-loop, time-stepping simulation, and " }, { t: "disturbances.py", i: true }, { t: " and " }, { t: "faults.py", i: true }, { t: " apply changes to the running plant." }]),
  p([{ t: "experiments", b: true }, { t: ": the eleven experiment functions and the shared code that saves their CSV, plot and JSON output." }]),
  p([{ t: "analysis", b: true }, { t: ": the performance metrics module, computed from simulation arrays rather than estimated by eye." }]),
  p("Every layer has automated tests. 55 tests cover the plant physics, the three sensors, the calibration routine, both controllers, the disturbance and fault frameworks, and the closed-loop simulation engine, and all 55 pass."),
];

// =======================================================================
// 4. MATHEMATICAL MODEL
// =======================================================================

const paramTableWidths = [2600, 1800, 4400];

const tankParams = table(
  ["Parameter", "Value", "Basis"],
  [
    ["Tank cross-sectional area, A", "0.045 m2", "Assumption: roughly 21 cm x 21 cm tank"],
    ["Usable tank height", "0.30 m", "Assumption: table-top scale"],
    ["Outlet orifice area, Ao", "1.2e-6 m2", "Assumption: narrow gravity drain, about 1.2 mm diameter (see section 4.3)"],
    ["Discharge coefficient, Cd", "0.62", "Standard textbook value for a sharp-edged orifice"],
    ["Minimum safe level", "0.03 m", "Heater interlock threshold"],
  ],
  paramTableWidths,
);

const pumpParams = table(
  ["Parameter", "Value", "Basis"],
  [
    ["Maximum pump flow", "6.0e-6 m3/s (about 0.36 L/min)", "Assumption: small dosing-style pump (see section 4.3)"],
    ["Dead zone", "8% of command", "Assumption: static friction in a small DC pump"],
    ["Nonlinearity exponent, gamma", "1.25", "Assumption: flow builds slower than command near the low end"],
  ],
  paramTableWidths,
);

const thermalParams = table(
  ["Parameter", "Value", "Basis"],
  [
    ["Water density", "997 kg/m3", "Standard property of water"],
    ["Specific heat", "4186 J/(kg K)", "Standard property of water"],
    ["Heater power", "180 W", "Assumption: small immersion heater"],
    ["Heat loss coefficient, UA", "0.6 W/K", "Assumption: lumped convective loss, lightly insulated tank"],
    ["Ambient temperature", "25 degC", "Assumption"],
    ["Reservoir temperature", "25 degC", "Assumption: same as ambient"],
  ],
  paramTableWidths,
);

const mathModel = [
  h1("4. Mathematical Model of the Virtual Plant", "sec4"),
  p("Both loops are driven by real differential equations, integrated forward in time with explicit Euler steps (see section 8). Nothing here is a plotted curve fitted to look like a control response; the numbers in section 9 come directly from stepping these equations forward."),

  h2("4.1 Level Dynamics"),
  p("The process tank is modeled as a single well-mixed control volume with a gravity drain. The mass balance in terms of height h is:"),
  eq([{ t: "A" }, " ", { t: "dh/dt = Qin - Qout" }], "1"),
  p("with a physically meaningful outflow relationship for a submerged, sharp-edged orifice draining under gravity:"),
  eq([{ t: "Qout = Cd . Ao . sqrt(2 g h)" }], "2"),
  p("Qin comes from the inlet pump through a nonlinear command-to-flow curve. I did not assume that a 50% pump command gives 50% of the pump's rated flow. Below a dead zone the pump does not move enough water to matter, which is what a small DC pump with static friction actually does; above the dead zone, flow rises with the command raised to an exponent greater than one, so the pump has to spin up before flow tracks the command closely:"),
  eq([{ t: "Qin = Qmax . ((u - udead) / (100 - udead))" }, { t: "gamma", sup: true }], "3"),
  p("for command u above udead, and zero otherwise. Table 1 and Table 2 list the tank and pump parameters used."),
  caption("Table 1. Tank geometry parameters"),
  tankParams,
  new Paragraph({ text: "", spacing: { after: 200 } }),
  caption("Table 2. Pump parameters"),
  pumpParams,
  new Paragraph({ text: "", spacing: { after: 100 } }),

  h2("4.2 Thermal Dynamics"),
  p("The tank is also treated as a single well-mixed thermal mass. Starting from an energy balance on a control volume whose mass changes as water flows in and out:"),
  eq([{ t: "d(m cp T)/dt = " }, { t: "rho" }, { t: " Qin cp Tin - " }, { t: "rho" }, { t: " Qout cp T + Qheater - Qloss" }], "4"),
  p("and expanding the left side as m cp dT/dt + cp T dm/dt, then substituting the continuity relation dm/dt = rho (Qin - Qout), the rho Qout cp T terms cancel and the balance reduces to:"),
  eq([{ t: "m cp " }, { t: "dT/dt = " }, { t: "rho" }, { t: " Qin cp (Tin - T) + Qheater - Qloss" }], "5"),
  p("which is what the simulation actually integrates, with:"),
  eq([{ t: "m = " }, { t: "rho" }, { t: " A h" }], "6"),
  eq([{ t: "Qheater = Pheater . (heater command / 100)" }], "7"),
  eq([{ t: "Qloss = UA (T - Tambient)" }], "8"),
  p("A minimum mass floor prevents the m in the denominator from approaching zero as the tank runs low, and the dry-run heater interlock described in section 3 stops the heater entirely below the minimum safe level, the way a real immersion heater would need a cutout to avoid heating an element with no water around it. Table 3 lists the thermal parameters."),
  caption("Table 3. Thermal parameters"),
  thermalParams,
  new Paragraph({ text: "", spacing: { after: 100 } }),

  h2("4.3 Coupling Between the Two Loops"),
  p("The rho Qin cp (Tin - T) term in equation 5 is the mechanism that couples the level loop to the temperature loop. When the pump runs harder to hold the level setpoint, more reservoir-temperature water enters the tank, and that shows up directly as a thermal disturbance the PID controller has to reject. This is not two simulations running side by side; a single shared variable, Qin, drives both equations."),
  p("Sizing the drain and the pump took a real iteration. My first attempt used a garden-hose-sized drain (about 6 mm diameter) and a pump rated around 3.3 L/min. Holding a steady level against that drain needed a continuous makeup flow whose thermal cost, rho Q cp times a 20 degC rise, worked out to a few kilowatts, far more than a 40 W heater could supply. The heater stayed pinned at 100% and the temperature still settled only a few tenths of a degree above ambient. Water's specific heat is large enough that even a modest continuous flow carries a large thermal cost, and a level loop that needs meaningful continuous throughput to hold its setpoint will dominate a small heater before the heater does anything useful."),
  p("The fix was to size the drain and pump around the heater's real capacity rather than the other way round: a roughly 1.2 mm drain orifice and a pump rated around 0.36 L/min, sized so the makeup flow needed to hold a level setpoint stays small enough for a 150-200 W heater to dominate. Experiment 10 in section 9.7 is the direct demonstration of this coupling once the plant was sized correctly: a level setpoint change produces a real, computed dip in temperature with no change to the temperature setpoint or controller."),
];

// =======================================================================
// 5. INSTRUMENTATION
// =======================================================================

const sensorParams = table(
  ["Sensor", "Noise (1 std dev)", "Resolution", "Delay", "Other"],
  [
    ["Temperature", "0.05 degC", "0.0625 degC", "2 steps", "DS18B20-style reference"],
    ["Level", "2.0 mm", "1.0 mm", "1 step", "1% chance per step of an outlier glitch, 12 mm"],
    ["Flow", "1.0e-7 m3/s", "none", "1 step", "Reads exactly zero below 3.0e-7 m3/s (turbine stall)"],
  ],
  [1300, 1600, 1400, 1000, 3500],
);

const calibrationTable = table(
  ["Sensor", "Slope", "Intercept", "RMSE", "Max abs error", "Mean % error"],
  [
    ["Temperature", "0.9999", "0.0148", "0.0414 degC", "0.0751 degC", "0.090%"],
    ["Level", "0.9974", "0.000628", "0.00159 m", "0.00353 m", "1.258%"],
    ["Flow", "0.9967", "2.35e-8", "6.23e-8 m3/s", "1.19e-7 m3/s", "3.580%"],
  ],
  [1300, 1200, 1400, 1400, 1900, 1600],
);

const instrumentation = [
  h1("5. Instrumentation", "sec5"),

  h2("5.1 Sensor Models"),
  p("Three virtual sensors stand in for the DS18B20, JSN-SR04T and YF-S201 in the original physical concept. Each has a different noise and failure profile on purpose, the same way a thermistor, an ultrasonic rangefinder and a turbine flow meter fail in different ways in reality. Every sensor converts a true physical quantity into a measured one through the same general steps: scale and bias, additive noise, an optional multi-step delay implemented as a small FIFO buffer, and quantization to a fixed resolution. Table 4 lists the parameters actually used."),
  caption("Table 4. Virtual sensor parameters"),
  sensorParams,
  new Paragraph({ text: "", spacing: { after: 100 } }),
  p("Two sensors get an extra failure mode that would not make sense on the other one. The level sensor has a small chance each step of an outlier glitch, a burst error an ultrasonic rangefinder produces when it catches a reflection off a disturbed water surface. The flow sensor reads exactly zero below a minimum detectable flow, because a turbine flow meter's rotor will not spin fast enough to register a pulse train at very low flow. All three sensors also support being frozen at their last reading or dropping a fraction of readings entirely, both used by the fault injection framework in section 7 rather than being active during normal operation."),

  h2("5.2 Sensor Calibration"),
  p("Calibration is a linear fit, measured = slope times reference plus intercept, computed by ordinary least squares against a set of simulated reference values swept across each sensor's working range. This produces SIMULATED CALIBRATION DATA: it comes from the sensor model in this project, not a physical bench, and every calibration output in this project is labeled that way so it is never confused with a real measurement."),
  p("Getting a clean calibration result took a second iteration too. The first version read each sensor once per reference point. For a sensor with a multi-step delay, that compares the current reference value against a measurement still lagging the previous reference point, which looks like calibration error but is really just reading the sensor too fast. The fix, matching how a real calibration bench is actually run, is to hold each reference value steady and sample the sensor repeatedly until its delay buffer has settled, then record the last reading. Temperature calibration RMSE dropped from 1.49 degC with the bug to 0.041 degC once fixed, which is close to the sensor's own 0.05 degC noise standard deviation, as it should be. Table 5 shows the calibration result actually used for all three sensors, and Figure 1 shows the temperature calibration."),
  new Paragraph({ children: [new PageBreak()] }),
  caption("Table 5. Simulated calibration results, 21 reference points per sensor"),
  calibrationTable,
  new Paragraph({ text: "", spacing: { after: 200 } }),
  ...figure("experiment_01_temperature_calibration.png", 420, "Figure 1. Simulated temperature sensor calibration, with the fitted line and the ideal y = x line for reference."),

  h2("5.3 Signal Filtering"),
  p("Both the temperature and level measurements pass through an exponential moving average filter before reaching their controllers:"),
  eq([{ t: "y[n] = " }, { t: "alpha" }, { t: " x[n] + (1 - " }, { t: "alpha" }, { t: ") y[n-1]" }], "9"),
  p("A smaller alpha filters harder at the cost of more lag behind the true signal, and that tradeoff is why alpha is a configuration parameter rather than a fixed constant. It also genuinely affects the control loop rather than being cosmetic. The level filter is the clearer example: with the outlier glitch modeled at 30 mm and a lightly-filtered alpha of 0.4, a single glitch produced a proportional-term spike large enough to swing the pump command across most of its range for one sample, visible as sharp, high-frequency spikes in the pump command trace even though the physical level itself stayed smooth (the tank's own capacitance absorbs a one-sample command spike). Reducing the outlier size to 12 mm and the filter alpha to 0.15 brought the pump command down to a level of noise that still tracks real changes but no longer spikes on every glitch. The temperature filter uses alpha = 0.3."),
];

// =======================================================================
// 6. CONTROL ARCHITECTURE
// =======================================================================

const controlArchitecture = [
  h1("6. Control Architecture", "sec6"),

  h2("6.1 PID Temperature Controller"),
  p("The temperature loop uses a discrete PID controller implemented directly rather than pulled from a library, since understanding the anti-windup and derivative handling was one of the objectives in section 2. The controller keeps a running integral and a filtered derivative as state between calls:"),
  eq([{ t: "u[n] = Kp e[n] + Ki I[n] + Kd D[n]" }], "10"),
  eq([{ t: "I[n] = clamp(I[n-1] + e[n] \u0394t,  0, 100)" }], "11"),
  eq([{ t: "D[n] = -(measurement[n] - measurement[n-1]) / \u0394t,  low-pass filtered" }], "12"),
  p("where e[n] = setpoint - measurement[n] and clamp(x, lo, hi) restricts x to the actuator's output range. Two design choices are worth stating explicitly rather than leaving implicit in the code."),
  p([{ t: "Anti-windup", b: true }, { t: ": the integral term accumulates every step and is then clamped to the actuator's output range (0 to 100%), rather than conditionally deciding whether to accumulate at all. This is simpler to reason about and keeps the integral from ever holding a value larger than the heater could act on by itself. When windup has pushed the integral to its ceiling, a small overshoot past the setpoint starts pulling the integral back down on the very next step rather than needing extra time first to work off banked windup, which is exactly what a unit test in tests/test_control.py checks for." }]),
  p([{ t: "Derivative on measurement", b: true }, { t: ": the derivative term is computed from the change in the filtered measurement, not the change in error, so a setpoint step does not produce an instantaneous spike in the heater command (a "}, {t:"derivative kick"}, {t:"). The raw derivative also passes through its own first-order low-pass filter (time constant 2 s) before being used, since differentiating a noisy measurement directly would let sensor noise dominate the heater command."}]),
  p("The controller also supports a manual mode that holds a fixed output, used for the open-loop step tests in section 6.3, and bumpless transfer back to automatic mode: the integral term is seeded from the manual output at the moment of the switch so the command does not jump."),

  h2("6.2 PI Level Controller"),
  p("The level loop uses a PI controller with no derivative term, built the same way as the PID controller (accumulate the integral, then clamp it to the output range) but without the derivative branch. Two reasons support leaving D out rather than just following convention."),
  ...bullets([
    "The ultrasonic level measurement is the noisiest signal in the project, and the occasional outlier glitch described in section 5.1 is exactly the kind of event a derivative term would amplify into a large, spurious pump command swing.",
    "The level process does not have the kind of lag that derivative action is meant to compensate for. The gravity drain's sqrt(h) outflow relationship already provides natural damping (a higher level drains faster on its own), so the process behaves closer to self-regulating than the thermal loop does, and there is not much for a D term to usefully damp.",
  ]),
  p("This matches standard industrial practice for level control, where PI is the default and PID is the exception rather than the rule, for the same reasons."),

  h2("6.3 Controller Tuning"),
  p("Gains were not hand-picked. Both controllers were tuned from an open-loop step test: hold the controller in manual mode, step the actuator command, and record the process variable's response with the other loop running normally underneath (so the identification reflects real operating conditions, including the coupling in section 4.3, not an artificially isolated loop). tuning.py fits a first-order-plus-dead-time (FOPDT) model to that response:"),
  ...bullets([
    "K, the process gain, is the steady-state change in the response divided by the size of the step",
    "tau, the time constant, is the time for the response to reach 63.2% of its total change",
    "theta, the apparent dead time, is the time before the response is first visibly moving",
  ]),
  p("For the temperature loop, stepping the heater command from 20% to 60% identified K = 0.316 degC per percent, tau = 4050 s, theta = 87 s (Figure 2). For the level loop, stepping the pump command from 20% to 40% identified K = 0.00329 m per percent, tau = 3231 s, theta = 88 s."),
  ...figure("experiment_04_open_loop_temperature_response.png", 520, "Figure 2. Open-loop temperature step response used to identify the FOPDT model."),
  p("I initially computed gains with the classic Ziegler-Nichols open-loop reaction-curve formulas, which divide directly by theta. That produced a derivative gain over 7500, because this plant has almost no real transport delay: the theta a threshold-based estimator picks up on a clean first-order response is mostly an artifact of how slowly such a response leaves its baseline, not a genuine dead time, and dividing by a very small or noisy theta blows the ZN formulas up. I switched to Skogestad's SIMC rule instead:"),
  eq([{ t: "Kc = (1/K) . " }, { t: "tau" }, { t: " / (" }, { t: "theta" }, { t: " + " }, { t: "lambda" }, { t: ")" }], "13"),
  eq([{ t: "Ti = min(" }, { t: "tau" }, { t: ", 4(" }, { t: "theta" }, { t: " + " }, { t: "lambda" }, { t: "))" }], "14"),
  p("where lambda is the desired closed-loop time constant, chosen here as tau/4 for a reasonably brisk but not aggressive response. SIMC stays well behaved as theta shrinks toward zero, which is the regime this plant sits in, and it does not need a precise theta to give sensible gains, only a roughly correct one. The derivative time for the PID controller is set directly from the real instrumentation lag (sensor delay plus filter time constant, about 5 s) rather than from the identified theta, for the same reason: using the inflated reaction-curve theta for Td would give a derivative term far larger than the real lag justifies. Table 6 summarizes both loops."),
  new Paragraph({ children: [new PageBreak()] }),
  caption("Table 6. Identified process models and resulting gains"),
  table(
    ["Loop", "K", "tau (s)", "theta (s)", "Kp", "Ki", "Kd"],
    [
      ["Temperature (PID)", "0.316 degC/%", "4050", "87", "11.22", "0.0027", "56.10"],
      ["Level (PI)", "0.00329 m/%", "3231", "88", "1095.04", "0.3389", "n/a"],
    ],
    [1700, 1400, 1100, 1100, 1200, 1200, 1100],
  ),
  new Paragraph({ text: "", spacing: { after: 100 } }),
  p("The gains actually in use in configuration.py match these identified values; they were not manually adjusted afterward. Running the identification a second time gives very similar but not bit-for-bit identical FOPDT parameters, because the level loop's pump command during the step test depends on noisy sensor data, which is expected and is discussed further in section 12."),
];

module.exports = {
  titlePage, introduction, objectives, architecture, mathModel,
  instrumentation, controlArchitecture,
};
