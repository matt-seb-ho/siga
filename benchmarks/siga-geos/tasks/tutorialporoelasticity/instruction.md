# GEOS input deck: TutorialPoroelasticity

GEOS is an open-source multiphysics simulator. This task asks you to author one or
more XML input files specified by the simulation specification below.

- The GEOS source tree (examples, documentation, XML schema) is at `/geos_lib`
  (read-only). Consult it for examples and documentation.
- Write your deck (one or more `.xml` files) under `/workspace/inputs/`.
- `xmllint` is available for checking well-formedness. There is no GEOS binary:
  do not try to build or run GEOS.

--- BEGIN SIMULATION SPECIFICATION ---
I need to set up a coupled simulation of a classic 1D poroelastic Terzaghi consolidation problem. The objective is to compute the time-dependent pressure and displacement fields of a fluid-saturated porous column subjected to an instantaneous compressive load, coupling a small-strain Lagrangian solid mechanics model with a single-phase fluid flow model. 

Please split the setup into a reusable base configuration and two specific execution cases (a quick test case and a high-resolution benchmark).

**Physical Geometry and Meshing**
The domain is a simulated 1D column extended into a 3D block using hexahedral elements. The total column length is 10.0 m in the X-direction, and it has a unit cross-section of 1.0 m by 1.0 m in the Y and Z directions.
*   **Test/Smoke Case:** Discretize the domain with a coarse grid of 25 elements in the X-direction, 1 in the Y-direction, and 1 in the Z-direction.
*   **Benchmark Case:** Discretize the domain with a finer grid of 400 elements in the X-direction, 16 in the Y-direction, and 16 in the Z-direction.

**Material and Fluid Properties**
The domain is modelled as a fluid-saturated, porous, isotropic elastic medium. Apply the following properties:
*   **Solid Skeleton:** Young's modulus of $1.0 \times 10^4$ Pa, Poisson's ratio of 0.2, and an explicitly set density of 0. 
*   **Porosity & Matrix:** Reference porosity is 0.3. Biot's coefficient is 1.0 (approximated by setting the grain bulk modulus to an effectively infinite value, $1.0 \times 10^{27}$ Pa).
*   **Permeability:** Isotropic intrinsic permeability of $1.0 \times 10^{-4}$ m² in all directions.
*   **Fluid:** Density of 1.0 kg/m³, viscosity of 1.0 Pa·s, and zero compressibility and viscosibility. The reference pressure is 0.0 Pa. 
*   Gravity is disabled (0.0 in all directions).

**Numerical Methods**
Couple the solid and fluid mechanics using a monolithic or coupled approach. Use a first-order linear finite element basis for the solid mechanics, and use a finite volume method with a two-point flux approximation (TPFA) for the fluid flow. The test case should use a direct parallel linear solver configuration. 

**Initial and Boundary Conditions**
*   **Initial Conditions:** The column starts at rest with an initial pressure of 0.0 Pa and 0.0 total displacement in all directions.
*   **Displacement Boundaries:** Apply roller boundary conditions on all faces except the loaded face. Specifically, constrain the X-displacement to 0 on the positive X face ($X=10$). Constrain the Y-displacement to 0 on both the negative and positive Y faces. Constrain the Z-displacement to 0 on both the negative and positive Z faces.
*   **Fluid Boundary:** The negative X face ($X=0$) acts as a permeable drainage boundary. Fix the pressure on this face to 0.0 Pa.
*   **Loading Condition:** Apply a compressive traction of 1.0 Pa uniformly strictly on the negative X face ($X=0$). Apply it with a direction vector of (1, 0, 0) and scale it using a time-varying table to simulate instantaneous application: 0.0 at $t=0$, 1.0 at $t=0.1 \times 10^{-9}$ s, and holding at 1.0 up to $t=10^7$ s.

**Time Stepping and Event Scheduling**
The characteristic consolidation time $t_c$ is 90 seconds, so the simulation should run up to a maximum time of 90.0 s.
Use the following strict time steps for the coupled solver events:
1.  From $t=0$ to $t=1.0 \times 10^{-5}$ s, force a timestep of $1.0 \times 10^{-5}$ s.
2.  From $t=1.0 \times 10^{-5}$ to $t=1.0$ s, force a timestep of 0.99999 s.
3.  From $t=1.0$ to $t=90.0$ s, force a timestep of 1.0 s.

**Outputs**
For both the benchmark and the test case, write visualization output (volumetric field data) every 10.0 s.
Additionally, for the coarse test case only:
*   Output restart files every 50 cycles. 
*   Collect time-history data for the pressure field over the bulk domain (every 10.0 s) and save it to a history file named "pressure_history". Target exact timesteps for this history output at 10.0 s intervals.

*Note for setup:* Construct a common base configuration with the direct solver settings, the numerical schemes, materials, and boundary definitions. Then create the test/smoke case that includes this base file, defines the coarse mesh, sets the events, and requests the explicit history/restart outputs. Similarly, set up the separate benchmark case file mapping out the fine grid mesh and volumetric outputs (the benchmark file can reference a base setup using an inclusion tag, though ensure the final targeted benchmark file structure aligns conceptually with the base requirements).

XML files to create: PoroElastic_Terzaghi_base_direct.xml, PoroElastic_Terzaghi_benchmark.xml, PoroElastic_Terzaghi_smoke.xml
--- END SIMULATION SPECIFICATION ---

--- SCOPE ---
Deliverable: the XML input deck in /workspace/inputs/. You are scored on the deck's
structure against a reference deck; nothing downstream reads simulation output.
Once the deck is complete and well-formed, it is finished.
--- END SCOPE ---
