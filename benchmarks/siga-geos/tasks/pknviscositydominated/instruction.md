# GEOS input deck: pknViscosityDominated

GEOS is an open-source multiphysics simulator. This task asks you to author one or
more XML input files specified by the simulation specification below.

- The GEOS source tree (examples, documentation, XML schema) is at `/geos_lib`
  (read-only). Consult it for examples and documentation.
- Write your deck (one or more `.xml` files) under `/workspace/inputs/`.
- `xmllint` is available for checking well-formedness. There is no GEOS binary:
  do not try to build or run GEOS.

--- BEGIN SIMULATION SPECIFICATION ---
I am looking to simulate the propagation of a Perkins-Kern-Nordgren (PKN) hydraulic fracture under viscosity-storage-dominated conditions. This is a classic benchmark, so I need to closely match analytical solutions where fracture height is constrained, fluid leak-off is neglected, and the fracture propagates laterally in an impermeable rock matrix.

Please set this up using a conceptual split for reusability: place the general material definitions, initial conditions, boundary conditions, and output requests into a generic "base" configuration, and place the specific domain mesh, solvers, geometry, and execution schedule into a "benchmark" configuration that includes the base file.

**Domain and Mesh**
Because of the inherent symmetry of a PKN fracture, we will model only a quarter of the actual physical domain to save on computational cost. 
Generate a 3D rectangular computational domain of 400 m x 400 m x 800 m using a structured mesh composed of 8-node hexahedral elements.
The mesh needs local refinement near the fracture plane. In total, it should have 105 x 105 x 60 elements in the x, y, and z directions, apportioned as follows:
- X direction: from 0 to 150 m (75 cells), 150 to 200 m (10 cells), and 200 to 400 m (20 cells).
- Y direction: from 0 to 150 m (75 cells), 150 to 200 m (10 cells), and 200 to 400 m (20 cells).
- Z direction: from -400 to -100 m (10 cells), -100 to -20 m (10 cells), -20 to 20 m (20 cells), 20 to 100 m (10 cells), and 100 to 400 m (10 cells).

**Geometry and Fracture Setup**
Define the potential fracture plane (the target interface for eventual rupture) covering x from -500.1 to 500.1 m, y from -500.1 to 10.1 m, and z from -0.1 to 0.1 m. Set this plane to initially act as a separable face with a rupture state allowing fracture propagation.
Within this plane, initialize a preexisting fracture region extending from x = -4.1 to 2.1 m, y = -4.1 to 6.1 m, and z = -0.1 to 0.1 m, with a default uniform initial aperture of 0.02 mm. 
Additionally, define a fluid injection source region right at the origin, extending from x = -2.1 to 2.1 m, y = -2.1 to 6.1 m, and z = -0.1 to 0.1 m.

**Materials and Rheology**
The domain consists of a single homogeneous and isotropic solid rock formulation, combined with a single-phase compressible fracturing fluid. 
- Rock matrix: Elastic assumed. Density is 2700 kg/m³, bulk modulus is 20.0 GPa, and shear modulus is 12.0 GPa.
- Fracture conditions: Very low initial rock toughness of 0.1 MPa·m^(1/2) to ensure viscosity-storage dominance. Use a frictionless contact logic and a parallel plates formulation for permeability. Fluid porosity within the fracture should have a reference value of 1.0 and zero compressibility. Define a hydraulic aperture relation mapping coordinates {-0.01, -0.001, 0.0} to values {0.005 mm, 0.01 mm, 0.02 mm}.
- Fracturing Fluid (Water): Density of 1000 kg/m³, viscosity of 1.0e-3 Pa·s, and compressibility of 5.0e-12 1/Pa. Initialize the water density field to 1000 kg/m³ in the fracture.

**Conditions and Constraints**
- Standard roller roller boundary constraints should be placed on all normal faces (x, y, z outer boundaries fixed to zero normal displacement).
- Inject fluid at the defined source region with a constant mass flux. Since we are modeling a quarter-symmetry domain with an intended volumetric rate of 0.0265 m³/s, the scaled mass injection scale should be set strictly to -6.625 kg/s.

**Numerical Solvers**
Use a strongly coupled system combining solid mechanics, single-phase fluid flow, and fracture surface generation.
- The mechanics should employ first-order Lagrangian finite elements, targeting both the generic domain and the fracture. Configure its non-linear solver with a 1.0e-6 tolerance.
- The fluid flow should be solved using a two-point flux approximation (finite volume) with a mean permeability coefficient of 0.8, targeting just the fracture. The non-linear flow tolerance should be 1.0e-5.
- Fracture propagation should evaluate stress intensity factors exclusively at nodes.
- Both solvers use iterative linear solvers (GMRES) configured with tight convergence limits. The master coupled solver loop should allow up to 5 resolves and 5 time-step cuts, using an adaptive GMRES/MGR solver framework with a tight Newton tolerance of 1.0e-4.

**Time Schedule**
The simulation covers exactly 200.1 seconds of injection. Guide the coupled solver with piecewise constant explicit time step sizes:
- 0 to 1 s: dt = 0.2000000000001 s
- 1 to 3 s: dt = 0.5 s
- 3 to 8 s: dt = 1.0 s
- 8 to 20 s: dt = 2.0 s
- 20 to 60 s: dt = 4.0 s
- 60 to 100 s: dt = 8.0 s
- 100 to end: dt = 10.0 s

**Data Collection and Output**
Save 3D spatial field metrics (plot level 3, root name "zeroToughness") periodically every 2.0 seconds. 
We need dedicated time series data sampled every 2.0 seconds to validate against the analytical curves:
- Track the pressure, element aperture, hydraulic aperture, and element area across the active fracture region. Route these collections directly to an output file explicitly named "pknViscosityDominated_output".
- Separately, extract just the pressure and hydraulic aperture specifically from the fluid injection "source" segment to track near-wellbore dynamics. Log these into an output file named "hydrofracture_source_curves".
- Include a restart output feature.

XML files to create: pknViscosityDominated_base.xml, pknViscosityDominated_benchmark.xml
--- END SIMULATION SPECIFICATION ---

--- SCOPE ---
Deliverable: the XML input deck in /workspace/inputs/. You are scored on the deck's
structure against a reference deck; nothing downstream reads simulation output.
Once the deck is complete and well-formed, it is finished.
--- END SCOPE ---
