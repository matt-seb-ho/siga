# GEOS input deck: AdvancedExamplePureThermalDiffusionWellbore

GEOS is an open-source multiphysics simulator. This task asks you to author one or
more XML input files specified by the simulation specification below.

- The GEOS source tree (examples, documentation, XML schema) is at `/geos_lib`
  (read-only). Consult it for examples and documentation.
- Write your deck (one or more `.xml` files) under `/workspace/inputs/`.
- `xmllint` is available for checking well-formedness. There is no GEOS binary:
  do not try to build or run GEOS.

--- BEGIN SIMULATION SPECIFICATION ---
I would like you to build a single-phase flow and heat transfer simulation to model pure thermal diffusion around a wellbore. The goal is to match an analytical solution for radial thermal diffusion. To isolate the thermal diffusion, we need to neglect thermal convection and fluid flow entirely by driving fluid pressure to zero and giving the fluid a negligible heat capacity. 

Please structure the setup into three components: a reusable base configuration containing the physical properties and solver settings, a high-resolution benchmark model for the accurate results, and a low-resolution "smoke test" model for quick validation checks.

### Physics and Material Properties
We will model the system as a compressible solid with a thermal compressible single-phase fluid. We want to use a finite-volume method with a two-point flux approximation (TPFA) to solve the thermal flow problem. 

**Fluid Details:**
Set the fluid reference density to 1000 kg/m³ and viscosity to 0.001 Pa·s at a reference pressure and temperature of 0. Give the fluid a compressibility of 5e-10 1/Pa and a thermal expansion coefficient of 3e-4 1/K. To eliminate the effects of convection, set the specific heat capacity to an artificially low value of 1 J/(kg·K) and its reference internal energy to 0.99. Viscosibility should be 0.

**Rock Details:**
We require two sets of thermal properties to be defined in the base configuration, though the benchmark and smoke test will only rely on the linear model.
1. **Linear Model (Active):** A constant volumetric heat capacity of 1.0e6 J/(m³·K) (at a reference temperature and internal energy of 0) and a constant, isotropic thermal conductivity of 1.66 W/(m·K) (at a reference temperature of 0).
2. **Nonlinear Model (Inactive):** A temperature-dependent volumetric heat capacity with a reference value of 4.56e6 J/(m³·K) varying by 1.0e6 J/(m³·K²) per degree, evaluated around 0 °C. The thermal conductivity is 1.5 W/(m·K) at a reference temperature of 20 °C, with a linear gradient of -1.2e-3 W/(m·K²) with respect to temperature.

For the rock mechanics and hydraulics, use a null/rigid solid model, a constant isotropic permeability of 1.0e-18 m², and a standard pressure-dependent porosity model with a reference porosity of 0.1 at 0 Pa and a rock compressibility of 3.0e-11 1/Pa.

### Domain, Geometry, and Meshing
The domain is a two-dimensional horizontal cross-section of a quarter of a wellbore (from an azimuth of 0 to 90 degrees). Use a hexahedral mesh extruded along the Z-axis from 0.0 to 0.1 m with exactly 1 element in the vertical (Z) direction. The inner radius of the wellbore is 0.1 m.

**Benchmark Mesh:**
The radial domain extends up to 1.0 m. Define the radial breakpoints at 0.1, 0.106, 0.133, and 1.0 m. Use 3, 10, and 50 elements for these three intervals, respectively. Enable automatic spacing for the final radial segment (from 0.133 to 1.0 m) to grade the mesh nicely. Use 80 elements in the azimuthal direction. 

**Smoke Test Mesh:**
The radial domain extends only to 0.17 m. Use radial breakpoints at 0.1, 0.106, 0.133, and 0.17 m. The number of radial elements in each segment should be 1, 2, and 2, with no automatic element spacing enabled. Use just 10 elements in the azimuthal direction.

### Initial and Boundary Conditions
- **Pressure:** Initialize the pressure field to 0 Pa everywhere. Apply a fixed Dirichlet boundary condition of 0 Pa at both the inner wellbore surface and the outer far-field boundary to prevent any pressure gradients.
- **Temperature:** Initialize the temperature to 100 °C everywhere. Fix the temperature at the outer far-field boundary at 100 °C. Apply a fixed temperature of -20.0 °C directly on the inner surface of the wellbore to drive the thermal diffusion.

### Solvers and Schedule
Set the nonlinear solver to use a Newton tolerance of 1.0e-6 with a maximum of 100 iterations. Turn off the direct parallel linear solver.

The total simulation time for both cases is 100,000 seconds (1e5 s).
- For the **benchmark case**, set the maximum solver time step to 1,000 seconds. Output VTK files every 10,000 seconds. (You can configure a restart output but keep its event commented out or disabled).
- For the **smoke test case**, set the maximum solver time step to 10,000 seconds. Output VTK files every 10,000 seconds and write restart files every 50,000 seconds.

XML files to create: thermalCompressible_2d_base.xml, thermalCompressible_2d_benchmark.xml, thermalCompressible_2d_smoke.xml
--- END SIMULATION SPECIFICATION ---

--- SCOPE ---
Deliverable: the XML input deck in /workspace/inputs/. You are scored on the deck's
structure against a reference deck; nothing downstream reads simulation output.
Once the deck is complete and well-formed, it is finished.
--- END SCOPE ---
