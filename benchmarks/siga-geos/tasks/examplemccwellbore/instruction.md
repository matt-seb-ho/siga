# GEOS input deck: ExampleMCCWellbore

GEOS is an open-source multiphysics simulator. This task asks you to author one or
more XML input files specified by the simulation specification below.

- The GEOS source tree (examples, documentation, XML schema) is at `/geos_lib`
  (read-only). Consult it for examples and documentation.
- Write your deck (one or more `.xml` files) under `/workspace/inputs/`.
- `xmllint` is available for checking well-formedness. There is no GEOS binary:
  do not try to build or run GEOS.

--- BEGIN SIMULATION SPECIFICATION ---
I am looking to simulate elastoplastic deformation around a vertical wellbore to replicate the drained analytical benchmark by Chen and Abousleiman (2013). Because the problem is drained, pore pressure variation is neglected, and we only need a quasi-static, Lagrangian solid mechanics setup without gravity or inertial effects.

**Mesh and Geometry**
The problem domain is a half-cylinder representing the surrounding rock formation. The vertical wellbore has an inner radius of 0.1 m and the domain extends to an outer radius of 5.0 m. The angular extent is from 0 to 180 degrees. The vertical span ranges from z = -1.0 m to z = 1.0 m, with a vertical trajectory extending between the coordinates (0, 0, -1) and (0, 0, 1). 
Use a structured, 3D hexahedral mesh (8-node elements). Assign 40 elements in the tangential direction and 2 elements in the vertical (Z) direction. For the radial direction, instruct the wellbore mesh generator to automatically space the radial elements to conform to the geometry (this will override manual counts to yield 50 elements radially). Maintain the naturally curved outer boundary rather than forcing a Cartesian outer boundary. Assign this mesh to a cell block name like "cb1".

**Material Properties**
The domain consists of a single homogeneous rock material modeled with a Modified Cam-Clay constitutive law. Please use the following properties (in SI units):
- Density: 2700 kg/m³
- Reference Pressure: -120 kPa (-1.2e5 Pa) 
- Reference Volumetric Strain: 0.0
- Shear Modulus: 4302 kPa (4.302e6 Pa)
- Pre-consolidation Pressure: -169 kPa (-1.69e5 Pa)
- Slope of Critical State Line (M): 1.2
- Virgin Compression Index (cc): 0.072676
- Recompression Index (cr): 0.014535

**Initial and Boundary Conditions**
Initialize the in-situ stress field uniformly across the domain with an isotropic horizontal stress of -100 kPa (-1.0e5 Pa) in both the X and Y directions, and a vertical (Z) stress of -160 kPa (-1.6e5 Pa). 

For the boundary conditions, constrain normal displacements on the outer boundaries using roller supports:
- Fix X-displacements to 0 on the X-planes (faces typically designated as `xneg` and `xpos`).
- Fix Y-displacements to 0 on the tangential and Y-planes (`tneg`, `tpos`, `ypos`).
- Fix Z-displacements to 0 on the vertical bounds (`zneg`, `zpos`).

At the wellbore wall (`rneg`), apply a normal pressure (traction) to represent the mud pressure. To reach equilibrium and allow the well to expand, this pressure is explicitly time-dependent: it starts at -100 kPa at t = 0 s and increases linearly to -300 kPa at t = 1.0 s. You can define this via a tabular time-history function with time coordinates {0.0, 1.0} and corresponding multipliers {1.0, 3.0} applied to a base scale of -100 kPa.

**Numerical Settings and Execution**
- Discretize the domain using first-order finite elements.
- Use a direct serial linear solver (disable direct parallel solvers).
- Limit the nonlinear Newton solver to 15 maximum iterations with a tolerance of 1.0e-5.
- Run the simulation to a maximum time of 1.0 s, forcing a constant time step of 0.005 s.
- Output Silo format files (using the root name "plot") for 3D visualization, along with restart files.
- Ensure the solver and outputs are triggered periodically based on the step size.

**File Structure**
Please cleanly isolate the physics by organizing this into two configuration files:
1. A reusable "base" file containing the table functions, materials, initial/boundary conditions, solvers, numerical methods, and output specifications.
2. A "benchmark" file that defines the wellbore mesh, includes the base file, and sets the schedule (max time, time step sizes, and execution events). 

XML files to create: ModifiedCamClayWellbore_base.xml, ModifiedCamClayWellbore_benchmark.xml
--- END SIMULATION SPECIFICATION ---

--- SCOPE ---
Deliverable: the XML input deck in /workspace/inputs/. You are scored on the deck's
structure against a reference deck; nothing downstream reads simulation output.
Once the deck is complete and well-formed, it is finished.
--- END SCOPE ---
