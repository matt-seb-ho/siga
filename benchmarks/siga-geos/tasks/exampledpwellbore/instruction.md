# GEOS input deck: ExampleDPWellbore

GEOS is an open-source multiphysics simulator. This task asks you to author one or
more XML input files specified by the simulation specification below.

- The GEOS source tree (examples, documentation, XML schema) is at `/geos_lib`
  (read-only). Consult it for examples and documentation.
- Write your deck (one or more `.xml` files) under `/workspace/inputs/`.
- `xmllint` is available for checking well-formedness. There is no GEOS binary:
  do not try to build or run GEOS.

--- BEGIN SIMULATION SPECIFICATION ---
I am looking to set up a geomechanical model to evaluate wellbore stability using an elastoplastic solid mechanics formulation. The setup will consist of a common base configuration for all the physics, a high-resolution benchmark case, and a low-resolution smoke test to quickly verify the execution.

**Physical Properties and Materials**
The domain consists of a single rock formation modeled with a Drucker-Prager yield criterion and linear cohesion hardening. The properties (using SI units) are:
* Density: 2700 kg/m³
* Bulk Modulus: 500 MPa (0.5e9 Pa)
* Shear Modulus: 300 MPa (0.3e9 Pa)
* Initial Cohesion: 0.1 MPa (0.1e6 Pa)
* Friction Angle: 15.27 degrees
* Dilation Angle: 15.0 degrees
* Hardening Rate: 10.0 MPa (10.0e6 Pa)

**Initial States and Boundary Conditions**
The formation is subject to a predefined initial stress state:
* Horizontal stresses (XX and YY): -11.25 MPa
* Vertical stress (ZZ): -15.0 MPa

To represent the problem efficiently, we will model a quarter-symmetry section of the wellbore (azimuth from 0 to 90 degrees) with the vertical axis extending from z = -1.0 m to 1.0 m. The initial wellbore radius is 0.1 m. 
For constraint boundaries:
* Fix the X-displacement to zero on the positive theta face and the positive radial (outer) face.
* Fix the Y-displacement to zero on the negative theta face and the positive radial (outer) face.
* Fix the Z-displacement to zero on the top and bottom faces (z positive and negative).

The inner wellbore face (negative radial boundary) is loaded by a normal traction representing the drilling mud pressure. This pressure varies dynamically:
* At time 0.0, the mud pressure equals the horizontal stress (-11.25 MPa).
* At time 1.0, the pressure is reduced to -2.0 MPa.
* This pressure of -2.0 MPa is maintained indefinitely (e.g., until time 1e99).

**Solver and Numerical Configuration**
Use a first-order, Lagrangian finite element method for the solid mechanics solver. Disable gravity (0,0,0). Set up the nonlinear Newton solver with a maximum of 100 iterations and a tolerance of 1.0e-5. Disable parallel direct solvers. 

For outputs, I need point-based history collections for the total nodal displacement and the cell-based stress evaluated for the rock. Standard visual VTK outputs and restart records should also be generated over the run.

**Benchmark Case**
The benchmark simulation requires a high-resolution hexahedral mesh extending to an outer radius of 10.0 m. Use 40 elements in the radial direction (automatically spaced) and 40 elements in the azimuthal direction, with a single element in the vertical direction. 
The simulation will run to a maximum time of 1.02, using a scheduled time-stepping strategy:
* From time 0.0 to 0.4, use a time step of 0.1.
* From time 0.4 to 0.9, use a time step of 0.02.
* From time 0.9 to 1.02, use a time step of 0.01.
Record the stress, displacement histories, and VTK outputs every step.

**Smoke Test Case**
For the quick smoke test, use a much coarser hexahedral mesh extending only to an outer radius of 5.0 m. Use just 4 radial elements, 4 azimuthal elements, and 1 vertical element. 
Schedule the solver to run up to a maximum time of 1.0 using a constant time step of 1.0. RecordVTK outputs and restart files every step. 

XML files to create: DruckerPragerWellbore_base.xml, DruckerPragerWellbore_benchmark.xml, DruckerPragerWellbore_smoke.xml
--- END SIMULATION SPECIFICATION ---

--- SCOPE ---
Deliverable: the XML input deck in /workspace/inputs/. You are scored on the deck's
structure against a reference deck; nothing downstream reads simulation output.
Once the deck is complete and well-formed, it is finished.
--- END SCOPE ---
