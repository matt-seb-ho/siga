# GEOS input deck: ExampleMandel

GEOS is an open-source multiphysics simulator. This task asks you to author one or
more XML input files specified by the simulation specification below.

- The GEOS source tree (examples, documentation, XML schema) is at `/geos_lib`
  (read-only). Consult it for examples and documentation.
- Write your deck (one or more `.xml` files) under `/workspace/inputs/`.
- `xmllint` is available for checking well-formedness. There is no GEOS binary:
  do not try to build or run GEOS.

--- BEGIN SIMULATION SPECIFICATION ---
I am setting up a simulation for Mandel's 2D poroelastic consolidation problem, a classic benchmark coupling solid mechanics and single-phase fluid flow. To keep the setup modular, I need to create a reusable base configuration that defines the physics, geometry, materials, and initial/boundary conditions, and then two separate runner configurations: a fully coupled benchmark case and a sequentially coupled smoke test.

### Domain and Mesh
We will model a 2D plane strain problem using a structured 3D domain to represent one-quarter of the sample (relying on symmetry). 
- The macroscopic sample sizes we are modeling dictate a quarter-symmetry domain with dimensions $1.0\text{ m}$ in the x-direction, $0.1\text{ m}$ in the y-direction (effectively the thickness), and $1.0\text{ m}$ in the z-direction. 
- Use an internal mesh generator to create a structured grid of $20 \times 1 \times 20$ linear, 8-node hexahedral brick elements. 
- Place all of these elements in a single cell block (e.g., `cb1`) within a designated domain region.

### Material Properties
The porous medium consists of a homogeneous solid frame (shale) and a compressible single-phase fluid (water). Do not apply gravity to the system.

**Solid (Shale):**
- Porous elastic isotropic mechanics.
- Solid density: $0.0\text{ kg/m}^3$.
- Bulk modulus: $66.667\text{ MPa}$ ($6.6667 \times 10^7\text{ Pa}$).
- Shear modulus: $40.0\text{ MPa}$ ($4.0 \times 10^7\text{ Pa}$).
- Biot porosity model with a reference porosity of $0.375$ and grain bulk modulus of $1.0 \times 10^{27}\text{ Pa}$.
- Constant, isotropic permeability of $1.0 \times 10^{-12}\text{ m}^2$.

**Fluid (Water):**
- Compressible single-phase fluid representation.
- Base density: $1000\text{ kg/m}^3$ at a reference pressure of $0.0\text{ Pa}$ (reference density multiplier = $1.0$).
- Viscosity: $0.001\text{ Pa s}$ with a viscosibility of $0.0$ and reference viscosity multiplier = $0.001$.
- Compressibility: $4.4 \times 10^{-10}\text{ Pa}^{-1}$.

### Initial Conditions
Set the entire domain to an undrained initial state:
- Uniform initial pore pressure: $4934.86\text{ Pa}$.
- Uniform initial total stress (x, y, and z components): $4934.86\text{ Pa}$.
- Initial displacement fields are prescribed by analytical tables. The x-displacement is scaled by $1.0$ and populated using a 3D table defined by external voxel data (`mandel_tables/xlin.geos`, `ylin.geos`, `zlin.geos`, and `ux.geos`). The y-displacement is initialized to $0.0$. The z-displacement is scaled by $1.0$ and populated by another 3D table (`mandel_tables/xlin2.geos`, `ylin2.geos`, `zlin2.geos`, and `uz.geos`).

### Boundary Conditions
Enforce rigid, impermeable, and plane strain boundaries where appropriate:
- Plane strain/symmetry plane constraints: Lock normal displacements to zero on the negative-x face ($U_x = 0$), the negative-z face ($U_z = 0$), and both the negative-y and positive-y faces ($U_y = 0$).
- Drainage: The outer lateral edge (positive-x face) is allowed to drain freely, so set its boundary pressure to $0.0\text{ Pa}$.
- Loading: Apply a prescribed normal vertical displacement on the top surface (positive-z face). This displacement is multiplied by a scale factor of $-1.0 \times 10^{-5}$ and follows a tabulated time history:
  - Times: 0, 1.00000000e-04, 1.83298071e-04, 3.35981829e-04, 6.15848211e-04, 1.12883789e-03, 2.06913808e-03, 3.79269019e-03, 6.95192796e-03, 1.27427499e-02, 2.33572147e-02, 4.28133240e-02, 7.84759970e-02, 1.43844989e-01, 2.63665090e-01, 4.83293024e-01, 8.85866790e-01, 1.62377674e+00, 2.97635144e+00, 5.45559478e+00, 1.00000000e+01.
  - Values: 6.31691864, 6.31770204, 6.31834881, 6.31952093, 6.32162575, 6.32534495, 6.33173922, 6.34226498, 6.35857272, 6.38222902, 6.41503816, 6.45995655, 6.52156122, 6.60644048, 6.72413111, 6.8887422, 7.12175231, 7.45621336, 7.9280595, 8.51003414, 9.03811794.

### Numerics and History Output Strategy
The physics should be spatially discretized using first-order finite elements for Lagrangian solid mechanics and a finite volume Two-Point Flux Approximation for the single-phase flow.

For outputs, define continuous collection tasks that gather pore pressure across the element block and total displacement on all nodes for time history purposes. These will be exported to files named `pressure_history` and `displacement_history`.

---

### Run Case 1: Fully Implicit Benchmark Simulation
Include the base setup. This run assesses the analytical benchmark over $10.0\text{ s}$ of physical time using a fully implicit poroelastic coupling.
- Maintain a constant time step of $0.025\text{ s}$.
- The poromechanics coupling nonlinear solver should allow a maximum of 2 Newton iterations with a tolerance of $1.0\times10^{-2}$. Set max timestep cuts to 1 and maximum line search cuts to 0. Direct parallel evaluation of the linear system should be disabled.
- Trigger VTK field outputs at an interval of $0.5\text{ s}$. Write out the pressure and displacement histories at every exact timestep. 

### Run Case 2: Sequential Smoke Test Simulation
Include the base setup. This case briefly exercises the framework using a sequential coupling strategy up to a max time of $0.1\text{ s}$. 
- Enforce the same forced time step of $0.025\text{ s}$. Let the poromechanics solver run continuously until maximum time.
- The poromechanics coupling should be set to "Sequential", with subcycling enabled, line search action set to "None", 2 max Newton iterations, and a $1.0\times10^{-2}$ tolerance.
- For the underlying independent solid and fluid solver steps, set their nonlinear solvers to max 40 iterations and a tolerance of $1.0\times10^{-4}$.
- Request VTK field data and full simulation restart arrays every $0.05\text{ s}$. Similar to the benchmark, record pressure and displacement history files at every exact timestep.

XML files to create: PoroElastic_Mandel_base.xml, PoroElastic_Mandel_benchmark_fim.xml, PoroElastic_Mandel_smoke_sequential.xml
--- END SIMULATION SPECIFICATION ---

--- SCOPE ---
Deliverable: the XML input deck in /workspace/inputs/. You are scored on the deck's
structure against a reference deck; nothing downstream reads simulation output.
Once the deck is complete and well-formed, it is finished.
--- END SCOPE ---
