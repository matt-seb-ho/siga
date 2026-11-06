# GEOS input deck: ExampleEDPWellbore

GEOS is an open-source multiphysics simulator. This task asks you to author one or
more XML input files specified by the simulation specification below.

- The GEOS source tree (examples, documentation, XML schema) is at `/geos_lib`
  (read-only). Consult it for examples and documentation.
- Write your deck (one or more `.xml` files) under `/workspace/inputs/`.
- `xmllint` is available for checking well-formedness. There is no GEOS binary:
  do not try to build or run GEOS.

--- BEGIN SIMULATION SPECIFICATION ---
I would like a simulation of a drained wellbore contraction problem under mechanical loading to evaluate the elastoplastic deformation of the surrounding rock. Please organize the problem into two configuration files: a reusable base case for the physics, materials, constraints, and outputs, and a benchmark case that defines the specific mesh and time-stepping schedule.

**Geometry and Mesh Definition**
The domain should represent a quarter cylinder (from 0 to 90 degrees azimuthally) around a vertical wellbore. We will model the depth interval from z = -1.0 m to z = 1.0 m. 
- The inner wellbore radius is 0.1 m, and the rock domain extends horizontally to an outer radius of 10.0 m. 
- Discretize the domain with an internally generated structured mesh of 8-node hexahedral elements.
- Use 40 elements azimuthally and 1 element vertically.
- In the radial direction, use 40 elements with automatic spacing/refinement biased toward the wellbore wall to capture the near-wellbore gradients. 

**Physics and Numerical Setup**
This is a drained analysis, so pore pressure effects are omitted. We want a quasi-static solid mechanics formulation using a first-order Lagrangian finite element approach without gravity or inertial effects. 
- For the nonlinear solver, set the Newton numerical tolerance to 1.0e-5 and the maximum iterations to 15. 
- Keep the linear solver basic by disabling direct parallel solving. 

**Material Properties**
The domain consists of a single homogeneous rock material modeled with a strain-hardening Extended Drucker-Prager plasticity model and an associated flow rule (dilation ratio of 1.0). Use the following parameters:
- Density: 2700 kg/m³
- Bulk Modulus: 500 MPa ($0.5 \times 10^9$ Pa)
- Shear Modulus: 300 MPa ($0.3 \times 10^9$ Pa)
- Cohesion: 0.0 MPa
- Initial Friction Angle: 15.27°
- Residual Friction Angle: 23.05°
- Hardening Rate: 0.01

**Initial and Boundary Conditions**
Initialize the domain with in-situ effective stresses. Due to geomechanics conventions, treat compressive stresses as negative values:
- Isotropic horizontal stress: -11.25 MPa (in both X and Y components).
- Vertical stress: -15.0 MPa (Z component).

Set up the following kinematic boundary constraints:
- Apply roller constraints on the two straight azimuthal symmetry planes of the quarter cylinder (fixing the normal displacements).
- Fix the far-field outer radial boundary entirely in both the horizontal X and horizontal Y directions.
- Ensure plane strain conditions by fixing the vertical Z displacement on both the top and bottom faces of the domain.

For the load, we will apply an instantaneous compressive traction (acting normally) to the innermost wellbore wall that gradually reduces as the well operates. Use a tabular function for the load history:
- At time t = 0.0 s, apply -11.25 MPa.
- Decrease the traction linearly over time to -2.0 MPa at t = 1.0 s.
- Hold the pressure steady at -2.0 MPa for any time beyond that (e.g., up to an arbitrarily large time like 1.0e99 s).

**Time Schedule**
Run the simulation up to a maximum time of 1.05 s, broken down into two main phases with exact time steps:
- From t = 0.0 s to 0.5 s, use a fixed time step of 0.1 s.
- From t = 0.5 s to 1.02 s, use a finer fixed time step of 0.02 s.

**Outputs**
Provide the following outputs continuously throughout the run:
- A standard VTK output for 3D visualization.
- Standard restart files.
- Two targeted temporal data collections spanning the whole domain:
  - A time-history collection of the element-based rock stress tensor, saved to a file named `stressHistory_rock`.
  - A time-history collection of the node-based total displacement field, saved to a file named `displacementHistory`.

XML files to create: ExtendedDruckerPragerWellbore_base.xml, ExtendedDruckerPragerWellbore_benchmark.xml
--- END SIMULATION SPECIFICATION ---

--- SCOPE ---
Deliverable: the XML input deck in /workspace/inputs/. You are scored on the deck's
structure against a reference deck; nothing downstream reads simulation output.
Once the deck is complete and well-formed, it is finished.
--- END SCOPE ---
