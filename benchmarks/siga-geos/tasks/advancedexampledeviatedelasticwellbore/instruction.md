# GEOS input deck: AdvancedExampleDeviatedElasticWellbore

GEOS is an open-source multiphysics simulator. This task asks you to author one or
more XML input files specified by the simulation specification below.

- The GEOS source tree (examples, documentation, XML schema) is at `/geos_lib`
  (read-only). Consult it for examples and documentation.
- Write your deck (one or more `.xml` files) under `/workspace/inputs/`.
- `xmllint` is available for checking well-formedness. There is no GEOS binary:
  do not try to build or run GEOS.

--- BEGIN SIMULATION SPECIFICATION ---
I need to set up a computational solid mechanics model to validate the stress distribution—specifically the radial and hoop stresses—around an inclined wellbore under open-hole completion conditions. The setup assumes an undrained scenario, so we can ignore pore fluid flow and formulate this purely as a solid mechanics problem. We are also ignoring gravity and any far-field in-situ stress conditions.

Please organize this modeling setup into a reusable base case containing the physics, boundaries, and materials, alongside two specific scenarios that import the base case: a high-resolution benchmark case for accuracy and a very coarse smoke test case for automated software testing.

**Material Properties**
Model the surrounding shale rock formation using an isotropic linear elastic constitutive model. 
- Bulk Modulus: 5.5556 GPa
- Shear Modulus: 4.16667 GPa
- Density: 2700 kg/m³ (included for completeness, though gravity is deactivated).

**Geometry and Meshing**
Use hexahedral finite elements with a first-order spatial discretization. The physical domain captures a half-symmetry representation of the wellbore, spanning azimuthally from 0 to 180 degrees.
- The inner radius of the wellbore is 0.1 m, and the rock formation extends to an outer radius of 2.0 m. 
- Instead of aligning the far-field boundary to a Cartesian bounding box, strictly maintain a cylindrical outer boundary.
- The wellbore is deviated at a 45-degree angle in the x-z plane. Define the well trajectory starting at coordinates (-0.5, 0.0, -0.5) and ending at (0.5, 0.0, 0.5), with axial limits bounded between -0.5 and 0.5.
- Enable automatic spatial grading for the radial elements so the mesh is finest at the wellbore wall and smoothly coarsens toward the far-field limit.

**Loading and Boundary Conditions**
- Apply a mud pressure of 10 MPa acting normal to the inner wellbore wall. Ensure the convention treats this as compressive (e.g., -10.0e6 Pa).
- Since we have no external in-situ stress, stabilize the numerical domain using roller constraints (zero normal displacement) on the boundary surfaces:
  - Fix displacement in the x-direction on the negative x-face.
  - Fix displacement in the y-direction on the two symmetry faces (the azimuthal boundaries).
  - Fix displacement in the z-direction on the negative z-face.

**Solver and Execution Profile**
We only need to calculate the static elastic response, so apply the load over a total simulation time of 1.0 s, forcing a calculation time step of 1.0 s. 
- Use a Newton-Raphson scheme for the nonlinear solver, allowing a maximum of 8 iterations per step and a convergence tolerance of 1.0e-6. 
- Request visualization files and restart files to be generated every 1.0 s. Write the plot files to a child directory labeled "sub" using the base name "plot", structured for 32 parallel output threads.

**Scenario Details**
1. **Benchmark Model**: Mesh the domain utilizing 30 elements in the radial direction, 80 elements azimuthally, and 100 elements along the wellbore axis. Use an iterative GMRES linear solver to handle the resulting system.
2. **Smoke Test Model**: Mesh a highly simplified coarse equivalent using only 3 elements radially, 4 elements azimuthally, and 2 elements axially. Switch to a standard direct linear solver to resolve this miniature system quickly.

XML files to create: DeviatedElasticWellbore_base.xml, DeviatedElasticWellbore_benchmark.xml, DeviatedElasticWellbore_smoke.xml
--- END SIMULATION SPECIFICATION ---

--- SCOPE ---
Deliverable: the XML input deck in /workspace/inputs/. You are scored on the deck's
structure against a reference deck; nothing downstream reads simulation output.
Once the deck is complete and well-formed, it is finished.
--- END SCOPE ---
