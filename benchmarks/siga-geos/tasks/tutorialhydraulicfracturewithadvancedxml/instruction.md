# GEOS input deck: TutorialHydraulicFractureWithAdvancedXML

GEOS is an open-source multiphysics simulator. This task asks you to author one or
more XML input files specified by the simulation specification below.

- The GEOS source tree (examples, documentation, XML schema) is at `/geos_lib`
  (read-only). Consult it for examples and documentation.
- Write your deck (one or more `.xml` files) under `/workspace/inputs/`.
- `xmllint` is available for checking well-formedness. There is no GEOS binary:
  do not try to build or run GEOS.

--- BEGIN SIMULATION SPECIFICATION ---
We need to set up a 3D quarter-symmetry hydraulic fracturing simulation with an embedded void using a fully coupled solver approach. The problem should be structured into a reusable base configuration file and a specific fast-running smoke test configuration file.

### Physical Domain and Mesh Setup
For the smoke test, construct a 3D hexahedral mesh defining the quarter-symmetry domain. The mesh is composed of a 3x3 array of blocks in the Y-Z cross-section, extruded along the X-axis. 
- **X-coordinates**: 0.0 to 0.001 (10 elements).
- **Y-coordinates**: 0.0, 0.0075, 0.00758, 0.015 (partitioned into 7, 2, and 7 elements).
- **Z-coordinates**: -0.0075, -0.00125, 0.00125, 0.0075 (partitioned into 7, 3, and 7 elements).
- **Material Blocks**: The central block in the Y-Z plane (the bounded region between Y=0.0075 to 0.00758 and Z=-0.00125 to 0.00125) represents a void. Assign this block the name `void`. All other 8 surrounding blocks should be named `cb1`. 
Both the `void` region and the `cb1` region in the domain should be assigned water and rock materials.

### Material Properties
- **Fluid (Water)**: Single-phase compressible fluid with a default and reference density of 1000 kg/m³, a default and reference viscosity of 1.0e-6 Pa·s, no viscosibility, and a compressibility of 5e-13 1/Pa. The reference pressure is 0.0.
- **Solid (Rock)**: Elastic isotropic rock with a density of 2700 kg/m³, a bulk modulus of 20.0 GPa, and a shear modulus of 12.0 GPa.
- **Fracture Properties**: The fracture elements should use a frictionless contact model, a null solid model, a pressure porosity model (reference porosity 1.0, reference pressure 0, no compressibility), and a parallel plates permeability model. The default fracture aperture is 0.02 mm. A hydraulic aperture table scales the aperture: at an effective opening of -1.0 mm, the hydraulic aperture is 0.002 mm, and at an effective opening of 0.0 mm, it is 0.02 mm.

### Boundary Conditions and Initial Fracture Geometry
Define several geometry boxes in the base file to initialize the pre-existing fracture pattern and boundary constraints:
- `core0`: X from -1.0 to 1.0, Y from 0.007499 to 0.007581, Z from -0.001251 to -0.001249
- `core1`: X from -1.0 to 1.0, Y from 0.007499 to 0.007581, Z from 0.001249 to 0.001251
- `core2`: X from -1.0 to 1.0, Y from 0.007499 to 0.007501, Z from -0.001251 to 0.001251
- `core3`: X from -1.0 to 1.0, Y from 0.007579 to 0.007581, Z from -0.001251 to 0.001251
Initialize the rupture state of the fracture faces residing in these four core boxes to broken (value 1).

Define a fixed region called `coreline`:
- `coreline`: X from -1.0 to 1.0, Y from 0.007501 to 0.007579, Z from -0.001 to 0.001.
Fix the X, Y, and Z total displacements to 0.0 for any nodes in this `coreline` box.

Apply external roller boundary conditions (0.0 normal displacement) to the outer boundaries of the entire domain:
- X-displacement bounded at the negative and positive X faces.
- Y-displacement bounded at the negative and positive Y faces.
- Z-displacement bounded at the negative and positive Z faces.

### Operational Conditions
Define a fluid injection zone via a `source` box:
- `source`: X from -1.0 to 0.0011, Y from 0.007499 to 0.0076, Z from -0.002 to 0.002.
Assign a fluid pressure boundary condition of 1.0 MPa (1.0e6 Pa) to the fracture elements within this `source` box.

### Solver Configuration
Coupled geomechanics and fluid flow driven by a hydrofracture solver:
- Use a first-order Lagrangian finite element solid mechanics solver and a two-point flux approximation (TPFA) cell-centered finite volume flow solver.
- The nonlinear solver for the hydrofracture should have a Newton tolerance of 1.0e-6, up to 50 iterations, and a maximum of 2 line search cuts. Set up up to 5 resolves and an initial time step of 0.1 s.
- Use a direct linear solver with sequential handling (direct parallel disabled), preconditioned with an MGR-type preconditioner, and an adaptive Krylov tolerance enabled. 
- Use a surface generator to model fracture propagation in the domain and void regions. Set the initial rock toughness to 3.0 MPa·m^0.5, use a node-based stress intensity factor formulation, and set the MPI comm order to 1.
- Gravity is 0 in all directions.

### Simulation Schedule and Output (Smoke Test)
- Run the simulation to a maximum time of 0.001 seconds.
- Execute the fracture surface generation once at the beginning.
- Apply the coupled hydrofracture solver constantly from 0.0 to 1.0 s, forcing a strict time step of 1.0e-4 s.
- Output visualization files (with a plot root name "walshQuarter" and a detailed plot level of 3) immediately before and after the initial fracture application, and then periodically every 0.0001 seconds without adjusting the solver timestep.
- Generate restart files exactly on the timestep every 0.0005 seconds.

XML files to create: walshQuarterNoChombo_base.xml, walshQuarterNoChombo_smoke.xml
--- END SIMULATION SPECIFICATION ---

--- SCOPE ---
Deliverable: the XML input deck in /workspace/inputs/. You are scored on the deck's
structure against a reference deck; nothing downstream reads simulation output.
Once the deck is complete and well-formed, it is finished.
--- END SCOPE ---
