# GEOS input deck: ExampleProppantTest

GEOS is an open-source multiphysics simulator. This task asks you to author one or
more XML input files specified by the simulation specification below.

- The GEOS source tree (examples, documentation, XML schema) is at `/geos_lib`
  (read-only). Consult it for examples and documentation.
- Write your deck (one or more `.xml` files) under `/workspace/inputs/`.
- `xmllint` is available for checking well-formedness. There is no GEOS binary:
  do not try to build or run GEOS.

--- BEGIN SIMULATION SPECIFICATION ---
**Simulation Request: Proppant Slot Test Modeling**

I need a simulation to model a proppant slot test matching the experimental setup of Chun et al. (2020). The goal is to simulate proppant transport with slickwater in a pre-existing hydraulic fracture channel. We will capture the evolution of a heterogeneous proppant distribution as particles settle in the low-viscosity fluid.

Please separate the problem definition into two reusable configurations: a "base case" that defines the geometry, material properties, and boundary/initial conditions; and a "benchmark case" that imports the base setup and dictates the mesh configuration, solver routines, and temporal stepping.

**Domain and Mesh Generation**
(To be defined in the benchmark case)
We will simulate a standard 3D domain spanning domain boundaries from -1 to 1 m in the x-direction, 0 to 1.2319 m in the y-direction, and 0 to 0.3048 m in the z-direction. Generate a structured internal mesh using eight-node hexahedral elements, discretized into 2 elements in x, 97 in y, and 24 in z. Assign this mesh space to a primary cell block group named `cb1`. 

**Geometry and Regions**
(To be defined in the base case)
The domain operates with two main material regions: a continuous volumetric region representing the entire fluid-solid cell layout and a discrete 2D surface region representing the vertical fracture plane. 
The static fracture plane is defined as a bounding box strictly inside the domain: x limits from -0.01 to 0.01 m, y limits from -0.01 to 1.2419 m, and z limits from -0.01 to 0.3148 m.

To define the injection points on the left boundary and fluid exit on the right, define several bounding boxes:
- **left0** (used to mark the entire inflow face): x from -0.001 to 0.001 m, y from -0.001 to 0.013 m, z from -0.001 to 0.3148 m.
- **left1** (bottom inlet): x from -0.001 to 0.001 m, y from -0.001 to 0.013 m, z from 0.07 to 0.09 m.
- **left2** (middle inlet): x from -0.001 to 0.001 m, y from -0.001 to 0.013 m, z from 0.15 to 0.17 m.
- **left3** (top inlet): x from -0.001 to 0.001 m, y from -0.001 to 0.013 m, z from 0.22 to 0.25 m.
- **right** (outflow/sink): x from -0.001 to 0.001 m, y from 1.21 to 1.2419 m, z from 0.22 to 0.25 m.

**Materials and Fluid Properties**
The simulation involves a fluid and a solid proppant phase. 
- **Water**: Represents slickwater. The reference density is 1000 kg/m³ at a reference pressure of 1e5 Pa. Viscosity is 0.001 Pa·s. It is strictly incompressible (compressibility = 0.0). The reference density of the proppant carried in this fluid should be matched at 2550 kg/m³, and the maximum allowable proppant volumetric concentration is 0.62.
- **Sand**: Represents the 30/50 mesh proppant. Proppant particle density is 2550 kg/m³ with a specific diameter of 4.5e-4 m. Particle settling physics should follow a Stokes settling model with a hindered settling coefficient of 4.5. Maximum proppant concentration is 0.62.
- **Fracture Fill**: The fracture space acts as a porous medium whose properties depend on the proppant distribution. It has no structural stiffness (a null solid model). Its dynamic porosity tracks a default reference of 1.0 (empty channel) capping at a max concentration of 0.62. The intrinsic fracture permeability should be modeled as a function of the proppant diameter (4.5e-4 m) and maximum proppant concentration (0.62).

**Initial and Boundary Conditions**
The entire active region handles the water and sand components, while the specifically identified surface region acts as the fracture carrying water, sand, and the fracture-fill properties.

At generation, the fracture has a uniform constant initial aperture of 7.62e-3 m, meaning propagating rupture state is set to fully open (value of 1). Within the fracture initially, pressure is 0 Pa, and the proppant concentration is 0. 

A boundary flag indicating an active proppant fluid boundary should be initialized to zero in the entire fracture space but set to exactly 1.0 in the **left0** bounding box to activate the left-wall constraints.

For operating conditions (fluid and slurry injection):
- The three inlets (**left1, left2, left3**) each act as independent fluid source terms mapped directly to the fracture surface. Set the mass source flux at each of these three inlets to scale at -0.14. Simultaneously, the injected proppant concentration at all three inlets must be fixed at 0.07.
- The single outlet on the right side (**right** box) allows pure relief: constrain fluid pressure here to 0 Pa and fix proppant concentration to 0.

**Physics, Discretization, and Numerical Parameters**
We will solve this multi-physics problem by coupling a single-phase fluid flow scheme with a proppant transport scheme in the fracture region. Use a finite-volume numerical method employing a two-point flux approximation (TPFA) for the discretizations. 

Set up a fracture generator routine targeting the fracture region, initializing the rock toughness to 1e6 (using an MPI comm order of 1). Execute this as a solo setup event prior to the main time loop.

- **Flow Solver**: Models the single-phase slurry flow using a finite volume scheme on the TPFA discretization. Apply a Newton method nonlinear solver (tolerance of 1.0e-6, max 8 iterations, no line search, min iterations 0) backed by a GMRES linear solver with AMG preconditioning (Krylov tolerance 1.0e-7).
- **Proppant Transport Solver**: Uses the TPFA discretization on the fracture. Relevant macroscopic parameters include a friction coefficient of 0.04 and a critical Shields number of 0.0. Use the given proppant diameter (4.5e-4 m) and max proppant concentration (0.62). Explicitly enable updating of the proppant packing. It relies on a Newton nonlinear solver (tolerance 1.0e-6, max 8 iterations, no line search, max timestep cuts 5) backed by a GMRES linear solver (Krylov tolerance 1.0e-7).
- **Coupling Sequence**: Define a top-level coupled driver that triggers the flow solver and then the proppant transport solver sequentially. The overall coupling scheme needs a maximum of 8 Newton iterations with no line search required.

**Time integration and Outputs**
Run the simulation over a 30-second physical window (up to a max time limit of 31 seconds to ensure completion). Implement an overarching periodic temporal cycle forcing an explicit fixed timestep of 0.1 seconds driving the coupled solver block. 
Output the standard state variables format periodically alongside a standard restart state file. 

XML files to create: ProppantSlotTest_base.xml, ProppantSlotTest_benchmark.xml
--- END SIMULATION SPECIFICATION ---

--- SCOPE ---
Deliverable: the XML input deck in /workspace/inputs/. You are scored on the deck's
structure against a reference deck; nothing downstream reads simulation output.
Once the deck is complete and well-formed, it is finished.
--- END SCOPE ---
