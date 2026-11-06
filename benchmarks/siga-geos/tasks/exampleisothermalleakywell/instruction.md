# GEOS input deck: ExampleIsothermalLeakyWell

GEOS is an open-source multiphysics simulator. This task asks you to author one or
more XML input files specified by the simulation specification below.

- The GEOS source tree (examples, documentation, XML schema) is at `/geos_lib`
  (read-only). Consult it for examples and documentation.
- Write your deck (one or more `.xml` files) under `/workspace/inputs/`.
- `xmllint` is available for checking well-formedness. There is no GEOS binary:
  do not try to build or run GEOS.

--- BEGIN SIMULATION SPECIFICATION ---
Please create a simulation input for a benchmark study of CO2 plume evolution and leakage through an abandoned well, modeled after the isothermal test problem from Class et al., 2009. The simulation tracks the advective spreading of CO2 injected into a lower aquifer and its subsequent buoyancy-driven leakage into a higher aquifer via a connecting leaky well. 

Please split the logical definition into a reusable base case file containing the physics, constitutive laws, and solvers, and a benchmark configuration file capturing the mesh, boundary geometry, and file inclusion.

**Domain Definition and Mesh**
The model domain measures 1000m x 1000m x 160m and is located at a depth of 2840m down to 3000m. It consists of three geological layers:
- Bottom Aquifer: -3000 m to -2970 m depth.
- Aquitard: -2970 m to -2870 m depth.
- Top Aquifer: -2870 m to -2840 m depth.

Use a structured hexahedral mesh with 112 x 101 x 60 elements (in X, Y, Z). To capture the 0.15 m radius wells, model them as square columns with cross-sectional dimensions of 0.2658 m x 0.2658 m. The domain spans from -500 to 500 in X and Y.
- In X, space the mesh using regions from -500 to -0.1329 (50 cells), to 0.1329 (1 cell representing the leaky well), to 99.8671 (20 cells), to 100.1329 (1 cell representing the injection well), to 500 (40 cells).
- In Y, space the mesh from -500 to -0.1329 (50 cells), to 0.1329 (1 cell for the wells), to 500 (50 cells).
- In Z, the cell counts are 20 for the bottom aquifer, 30 for the aquitard, and 10 for the top aquifer.

The simulation will only solve for multiphase flow in the active regions: the top and bottom aquifers, the lower segment of the injection well, and the full extent of the leaky well. The rest of the aquitard acts as a completely non-simulated barrier.

**Rock and Fluid Properties**
The problem uses a simplified, isothermal (313.15 K), two-phase immiscible flow formulation for CO2 and Brine without capillary pressure. Both the fluids and the rock properties are treated as unconditionally incompressible.
- **Fluids**: Set the water phase (brine) density to 1045 kg/m³ and viscosity to 2.535e-4 Pa·s. Set the CO2 phase (modeled as a "dead oil" analog) density to 479 kg/m³ and viscosity to 3.95e-5 Pa·s. Set the molar weights to 0.018 kg/mol for water and 0.114 kg/mol for CO2. The reference pressure is 1e7 Pa.
- **Rock / Porous Media**: The entire active domain has a uniform reference porosity of 0.15 with zero compressibility.
- **Permeability**: The aquifers have an isotropic permeability of 2.0e-14 m². The wells are modeled as porous media with an artificially high isotropic permeability of 1.0e-12 m². 
- **Relative Permeability**: Use a linear Brooks-Corey model (exponent of 1) for both phases, with relative permeabilities ranging from 0.0 to a maximum of 1.0. The minimum volume fractions for mobility are 0.0.

**Initial and Boundary Conditions**
- **Initial State**: The domain is initially in hydrostatic equilibrium, saturated entirely with brine (a trace CO2 mass fraction of 1e-6 can be used for numerical stability). Specify a datum pressure of 3.086e7 Pa at an elevation of -3000 m.
- **Injection well**: Inject CO2 at a constant rate of 8.87 kg/s into the bottom aquifer at the injection well location (X center ~100, Y center ~0). Handle this as a flux source applied over the full 30 m thickness of that well segment.
- **Lateral Boundaries**: Apply constant, hydrostatic Dirichlet boundary conditions on the far-field lateral borders (East, West, North, and South sides) of the top and bottom aquifers. The boundaries should maintain the predefined hydrostatic pressure profile and a 100% brine composition (adjusting for the 1e-6 trace CO2). Define 10m thick bounding boxes on the edges to select the appropriate cells.

**Numerics and Outputs**
- Use a robust finite-volume two-point flux approximation (TPFA) method. 
- Time-stepping starts at 0.001 s, running to a total simulation time of 8.64e7 s (1000 days), capped at solver application steps of 1e5 s.
- Use a fully implicit backward Euler formulation with a Newton-Raphson nonlinear solver (max 100 iterations, tolerance 1e-3, 5 maximum timestep cuts) and an FGMRES linear solver with algebraic multigrid preconditioning (tolerance 1e-4).
- Request 3D spatial field dumps (VTK format) every 8.64e6 s (100 days).
- Set up continuous statistical monitoring and time history output tracking every 1e7 s. Specifically, collect the total phase outflux within the aquitard portion of the leaky well to monitor the mass leakage rate across the intervening layer.

XML files to create: isothermalLeakyWell_base_iterative.xml, isothermalLeakyWell_benchmark.xml
--- END SIMULATION SPECIFICATION ---

--- SCOPE ---
Deliverable: the XML input deck in /workspace/inputs/. You are scored on the deck's
structure against a reference deck; nothing downstream reads simulation output.
Once the deck is complete and well-formed, it is finished.
--- END SCOPE ---
