# GEOS input deck: TutorialSneddon

GEOS is an open-source multiphysics simulator. This task asks you to author one or
more XML input files specified by the simulation specification below.

- The GEOS source tree (examples, documentation, XML schema) is at `/geos_lib`
  (read-only). Consult it for examples and documentation.
- Write your deck (one or more `.xml` files) under `/workspace/inputs/`.
- `xmllint` is available for checking well-formedness. There is no GEOS binary:
  do not try to build or run GEOS.

--- BEGIN SIMULATION SPECIFICATION ---
I am looking to simulate Sneddon’s problem to verify different numerical strategies for modeling the deformation of a porous medium containing a static, pressurized fracture. Specifically, I want to compute the displacement field and fracture aperture (the normal component of the displacement jump) for a fracture of length $L_f = 2.0$ m using three different coupling and discretization strategies: an Embedded Fractures approach, a Lagrangian Contact Mechanics approach, and a fully coupled Hydraulic Fracturing approach. 

The baseline physical domain for all cases is a $40 \text{ m} \times 40 \text{ m} \times 1 \text{ m}$ block of rock. The matrix material is considered a linear elastic isotropic medium with a density of 2700 kg/m$^3$, a bulk modulus of 16.66666666666666 GPa, and a shear modulus of 10.0 GPa. No fracture propagation should occur in these tests. The simulation time for all models should run from 0.0 to 1.0 seconds, with periodic applications of the solvers, outputs, and time history collections occurring at a frequency/timestep of 1.0. 

For all three models, please apply appropriate roller boundary conditions on the far-field edges. This means constraining normal displacements to zero on the opposing $X$, $Y$, and $Z$ domain boundaries.

Please build the simulations in three sets using a modular approach where base material properties and boundary conditions are kept in base files, while the meshes and execution schedules are managed in verification or benchmark files.

### Strategy 1: Embedded Fractures Model
This approach should utilize an embedded discretization technique for the surface generation and solid mechanics. Use a GMRES linear solver with an MGR preconditioner, and a nonlinear Newton solver (tolerance $1.0\times 10^{-6}$, max iterations 4).
- **Mesh Details**: Generate an internal hexahedral mesh spanning from -20 to 20 in the X and Y directions, and 0 to 1 in Z. To refine around the fracture, define the node coordinate breakpoints at $\pm 4$ in X and Y. Apply element breakdowns of 10, 101, and 10 segments along the X-axis intervals, and 10, 901, and 10 segments along the Y-axis. The Z-axis should have 1 element layer.
- **Fracture and Loads**: Define the fracture plane geometry as a rectangle originating at the center (0,0,0) with its normal along the X-axis, measuring 2 m along the Y-axis and 10 m along the Z-axis. Apply a frictionless contact law default aperture of $1\times 10^{-3}$, and an aperture table mapping closures of $-1\times 10^{-3}$ and 0.0 to $1\times 10^{-6}$ and $1\times 10^{-4}$, respectively. Place a normal traction load on the fracture surface of -2.0 MPa.
- **Outputs**: Record the time history of the normal displacement jump on the fracture elements. Include VTK outputs in binary format.
- Organize this into a base file and a verification file.

### Strategy 2: Lagrangian Contact Mechanics Model
This approach requires the fracture interface to align explicitly with element facets using a Lagrangian contact formulation stabilized with a two-point flux approximation (TPFA). Use a direct parallel linear solver and a Newton loop (tolerance $1.0\times 10^{-8}$, max 10 iterations).
- **Mesh Details**: Build a similar hexahedral mesh with X and Y domain limits of -20 to 20, but with refinement breakpoints at $\pm 2$. Apply element segment breakdowns of 40, 220, and 40 along X and Y. Split the Z-axis spanning 0 to 1 into 2 internal segments. 
- **Fracture and Loads**: Use a surface generator initialized with a rock toughness of $1.0\times 10^6$. Define two rectangular geometries at the origin (normal to X, length 2m along Y, width 10m along Z): one for the "fracture" tracking rupture states, and a longer "core" dimension tracking separable faces and where the -2.0 MPa normal traction will be applied. The fracture contact law is based on Coulomb friction (cohesion 0.0, friction coefficient $\approx 0.57735$) with a default interface aperture of $1\times 10^{-6}$.
- **Outputs**: Record the time history of the displacement jump across the fracture interface. Include ASCII VTK outputs. 
- Conceptually split this into a base file containing the geometry and mechanics physics, a benchmark file for the mesh and surface generation, and a high-level parent benchmark file linking the mechanical solver and event schedule.

### Strategy 3: Coupled Hydraulic Fracturing Model
This approach uses a finite-volume numerical method to resolve single-phase flow perfectly coupled to fully Lagrangian finite elements for rock and fracture deformation.
- **Mesh Details**: Using the same domain boundaries and refinement breakpoints at $\pm 2$ as the Lagrangian case, prescribe 40, 200, and 40 elements spanning the intervals in both the X and Y directions. Use 1 segment along the Z-axis. 
- **Fluid and Fracture Material**: Introduce water with a reference density of 1000 kg/m$^3$, a viscosity of $1.0\times 10^{-6}$ Pa·s, and fluid compressibility of $5\times 10^{-10}$ Pa$^{-1}$. Emulate the fracture flow dynamically using a pressure-dependent porosity and a parallel plates permeability model combined with frictionless mechanical contact. Set the initial hydraulic aperture via a table mapping $-1\times 10^{-3}$ and 0.0 to $0.002\times 10^{-3}$ and $0.02\times 10^{-3}$ respectively (default $0.02\times 10^{-3}$).
- **Conditions**: Instead of rectanglar planes, define the localized regions via bounding boxes: a center fracture zone (X from -0.01 to 0.01, Y from -1.01 to 1.01, Z from -0.01 to 1.01), a narrow source core (Y from -0.11 to 0.11), and a tracking core zone (Y from -10.01 to 10.01). Note that for this strategy, fix the entire domain's Z-displacement to zero. Initialize the water density to 1000 in the fracture zone and directly specify an internal fluid pressure of 2.0 MPa everywhere on the fracture surface to drive the opening. 
- **Outputs**: Instead of displacement jump, explicitly output the time history of the dynamic element aperture across the fracture face. Ensure VTK plots are generated.
- Group the setup into a base file for the fluid, physics, solvers, and boundaries, and a benchmark file that provides the mesh generation and time execution events. 

For all setups, please ensure that standard restart datasets are saved at the end of the simulation.

XML files to create: ContactMechanics_Sneddon_benchmark.xml, Sneddon_base.xml, Sneddon_benchmark.xml, Sneddon_embeddedFrac_base.xml, Sneddon_embeddedFrac_verification.xml, Sneddon_hydroFrac_base.xml, Sneddon_hydroFrac_benchmark.xml
--- END SIMULATION SPECIFICATION ---

--- SCOPE ---
Deliverable: the XML input deck in /workspace/inputs/. You are scored on the deck's
structure against a reference deck; nothing downstream reads simulation output.
Once the deck is complete and well-formed, it is finished.
--- END SCOPE ---
