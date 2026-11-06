# GEOS input deck: AdvancedExampleThermoPoroElasticWellbore

GEOS is an open-source multiphysics simulator. This task asks you to author one or
more XML input files specified by the simulation specification below.

- The GEOS source tree (examples, documentation, XML schema) is at `/geos_lib`
  (read-only). Consult it for examples and documentation.
- Write your deck (one or more `.xml` files) under `/workspace/inputs/`.
- `xmllint` is available for checking well-formedness. There is no GEOS binary:
  do not try to build or run GEOS.

--- BEGIN SIMULATION SPECIFICATION ---
I am looking to set up a fully implicit, thermo-poro-elastic simulation of an open wellbore to analyze the effects of temperature changes on the surrounding rock formation. We will be using analytical solutions by Wang and Papamichos or Cheng to validate this, so the physical assumptions and boundary conditions need to be strictly controlled.

### Physical Setup and Domain
The domain represents a quarter of a vertical open wellbore to leverage symmetry. We assume plane strain and axisymmetric conditions, focusing purely on radial thermal diffusion in a single horizontal layer. Gravitational effects and thermal convection are ignored (the fluid should have a negligibly small heat capacity so heat transfer is diffusion-only). 

The wellbore inner radius is 0.1 m and the outer/far-field boundary is at 5.0 m. The slice thickness in the vertical (z) direction is from 0.0 to 0.1 m. The mesh should use first-order hexahedral elements with radially optimized spacing (element size increasing from the near-wellbore zone to the far-field). 

I need two configurations of this model:
1. **Benchmark Model**: A high-resolution mesh with 100 elements in the radial direction, 40 elements in the tangential (theta: 0 to 90 degrees) direction, and 1 element in the vertical. Total simulation time is 3700 seconds.
2. **Smoke Test Model**: A very coarse, fast-running mesh with 4 radial elements, 4 tangential elements, and 1 vertical element. Total simulation time is 12 seconds.

### Material Properties
**Rock (Solid matrix):**
- Density: 2700 kg/m³
- Drained bulk modulus: 20.7 GPa
- Drained shear modulus: 12.4 GPa
- Drained linear thermal expansion coefficient: 4.0e-5 1/K
- Isotropic thermal conductivity: 6.6 W/(m·K)
- Volumetric heat capacity: 1.89e6 J/(m³·K) (reference temperature = 0 °C, reference internal energy = 0)
- Isotropic permeability: 1.0e-21 m²
- Reference porosity: 0.001
- Grain bulk modulus: 23.5 GPa
- Porosity thermal expansion coefficient: 4.0e-5 1/K

**Fluid:**
- Density: 1000 kg/m³
- Viscosity: 1.0e-3 Pa·s
- Compressibility: 5.0e-10 1/Pa
- Thermal expansion coefficient: 3.0e-4 1/K
- Reference pressure: 0.0 Pa
- Reference temperature: 20.0 °C
- Specific heat capacity: 1.0 J/(kg·K) (small to neglect convection)
- Reference internal energy: 1.0 J/kg

### Initial and Boundary Conditions
- **Initial Conditions:** Because the initial temperature change is zero, the initial effective stress components (x, y, z) are all set to 0. The initial pore pressure is 0 Pa, and the initial temperature is 0 °C across the domain.
- **Mechanical Boundary Conditions:** 
  - To enforce plane strain, fix the vertical (z) displacements to 0 at the bottom and top boundaries. 
  - To enforce axisymmetry on the quarter geometry, fix normal displacements on the symmetric planes (y-displacement=0 at theta=0 plane, x-displacement=0 at theta=90 plane). 
  - The far-field outer boundary should be completely fixed (x- and y-displacements equals 0).
  - The inner wellbore surface is traction-free (normal traction = 0 Pa).
- **Flow & Thermal Boundary Conditions:**
  - Inner wellbore surface: Applied temperature is 100.0 °C, and pore pressure is maintained at 0 Pa.
  - Far-field outer boundary: Temperature is 0 °C, and pore pressure is 0 Pa.

### Numerical Solver Specifications
The problem should be solved in a fully coupled, fully implicit manner using a single-phase poromechanics formulation. 
- Use a standard Lagrangian finite element method for the solid mechanics.
- Use a finite volume method with two-point flux approximation (TPFA) for fluid and heat flow.
- The nonlinear solver should allow up to 100 Newton iterations, and the linear equations should be solved using a direct solver.

### Schedules and Outputs
We need to collect time-history data for temperature, pore pressure, and solid stress from the rock elements, as well as total displacement data from the nodes. Save these to files named `temperatureHistory_rock`, `pressureHistory_rock`, `stressHistory_rock`, and `displacementHistory`. Also, generate standard 3D spatial output and restart files.

**For the Benchmark model:**
- We need variable time stepping:
  - From 0 to 60 s, step size is 6 s.
  - From 60 to 360 s, step size is 60 s.
  - From 360 to 3700 s, step size is 360 s.
- Time-history outputs should be written out every 60 s between 0 and 360 s, and then every 360 s between 360 and 3700 s.
- Standard spatial output should be generated every 360 s.
- Restart files should be written every 1800 s.

**For the Smoke test model:**
- Max solver time step is 6 s.
- Time-history outputs should be written at 12 s (the end of the run) using a forcing interval of 12 s.
- Standard spatial output every 12 s.
- Restart files every 6 s.

Please structure the files conceptually so that the common physical properties and boundary setups are housed in a base configuration file which is then included by the benchmark and smoke test files. 

XML files to create: ThermoPoroElasticWellbore_base.xml, ThermoPoroElasticWellbore_benchmark.xml, ThermoPoroElasticWellbore_smoke.xml
--- END SIMULATION SPECIFICATION ---

--- SCOPE ---
Deliverable: the XML input deck in /workspace/inputs/. You are scored on the deck's
structure against a reference deck; nothing downstream reads simulation output.
Once the deck is complete and well-formed, it is finished.
--- END SCOPE ---
