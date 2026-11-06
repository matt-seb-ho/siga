# GEOS input deck: kgdExperimentValidation

GEOS is an open-source multiphysics simulator. This task asks you to author one or
more XML input files specified by the simulation specification below.

- The GEOS source tree (examples, documentation, XML schema) is at `/geos_lib`
  (read-only). Consult it for examples and documentation.
- Write your deck (one or more `.xml` files) under `/workspace/inputs/`.
- `xmllint` is available for checking well-formedness. There is no GEOS binary:
  do not try to build or run GEOS.

--- BEGIN SIMULATION SPECIFICATION ---
We need to simulate a laboratory-scale hydraulic fracturing experiment on a finite block, corresponding to a modified KGD (Khristianovic-Geertsma-de Klerk) geometry. The computational model represents an injection benchmark test performed on a polymethylmethacrylate (PMMA) block. The purpose of this simulation is to validate our coupled fluid-mechanical hydrofracturing modeling against the experimental benchmark. To do this naturally, we will split the problem definition into two parts: a reusable base configuration defining the physics, materials, and generic solvers, and a benchmark scenario specifying the exact domain, mesh, event timings, and output controls.

### Physical Model & Geometry
Because of the problem's symmetry, we only model half of the central layer. The numerical domain is a rectangular block with overall dimensions of 0.1525 m long (x-axis), 0.096 m wide (y-axis), and 0.055 m high (z-axis). The domain spans from 0.0 to 0.1525 m in the x-direction, -0.048 to 0.048 m in the y-direction, and 0.037 to 0.092 m in the z-direction. 

We require a structured mesh of 8-node hexahedral brick elements. The mesh consists of 80 elements uniformly distributed along the x-direction and 10 elements along the z-direction. The y-direction requires element refinement near the central fracture plane, so we divide the y-axis into five zones with the following boundaries and element counts:
- from -0.048 to -0.012 m (4 elements)
- from -0.012 to -0.006 m (2 elements)
- from -0.006 to 0.006 m (6 elements)
- from 0.006 to 0.012 m (2 elements)
- from 0.012 to 0.048 m (4 elements)
This yields an 80 x 18 x 10 element grid.

The potential planar fracture is allowed to propagate along the x-z plane (the core plane). This potential rupture zone is defined by a bounding box from x=-0.1, y=-0.001, z=0.036 to x=0.2, y=0.001, z=0.093. Within this plane, an initial pre-existing fracture is localized in a smaller box spanning from x=-0.1, y=-0.001, z=0.036 to x=0.003, y=0.001, z=0.093. The initial fracture has a default aperture of 0.02 mm (0.02e-3 m).

### Material Properties
The solid medium is modeled as a homogeneous, isotropic elastic material with a density of 2700 kg/m³. It has a bulk modulus of 4.110276 GPa and a shear modulus of 1.19971 GPa. The critical stress intensity factor (rock toughness) governing fracture propagation is 1.2 MPa·m^(1/2) (1.2e6 Pa·m^(0.5)). 

The fracturing fluid is a highly viscous, compressible single-phase liquid, mimicking the experimental injection fluid. It has a reference density of 1000 kg/m³, a reference pressure of 0.0 Pa, a constant viscosity of 97.7 Pa·s, and a compressibility of 5.0e-12 Pa⁻¹.

The mechanical contact across the separated fracture faces should be frictionless, and fluid flow within the fracture should be governed by a parallel-plates permeability model supplemented by an aperture table. The table should map an aperture of -1.0 mm to a hydraulic aperture of 0.002 mm, and 0.0 mm to 0.02 mm.

### Solvers and Numerical Nuances
The model must tightly couple solid deformation, fracture propagation, and fluid flow.
1. **Mechanical Deformation**: A Lagrangian finite element formulation using first-order finite elements should compute the deformation in the rock block and the fracture. It uses a penalty stiffness of 1.0 for fracture surface contacts. Zero gravity is applied.
2. **Fluid Flow**: A finite volume method using a two-point flux approximation evaluates the single-phase flow exclusively within the fracture. The mean permeability coefficient should be set to 0.8.
3. **Fracture Propagation**: The solver should use an edge-based stress intensity factor formulation to determine rupture (i.e., not node-based).

For the nonlinear coupling, the solver needs to allow up to 2 resolves per step, with a Newton tolerance of 1.0e-5, a maximum of 20 Newton iterations, and a maximum of 3 line search cuts. Use a standard non-parallel linear solver.

### Boundary and Initial Conditions
Initialize the initial fracture volume with a rupture state of 1. Initialize the faces along the extended fracture core plane as separable (value of 1). Ensure the fluid density in the fracture is initialized to 1000 kg/m³.

Mechanically, the top and bottom surfaces in the z-direction must have roller boundary conditions (constrained against displacement in the z-direction). The x-minimum boundary (near the injection site) should be constrained against x-displacement. All other far-field lateral boundaries remain traction-free.

Fluid is injected into the initial fracture box region. Due to the symmetrical half-domain modeling, we apply exactly half of the experimental mass injection rate. Given Q0=73.2e-9 m³/s and fluid density of 1000 kg/m³, the applied mass source flux should be scaled to -0.0000366 kg/s (the negative sign follows standard compressive convention).

### Pumping Schedule and Time Integration
The total simulation time is 100.1 seconds. The time integration scheme must strictly conform to the following sequence of time step sizes:
- 0.0 s to 1.0 s: time step of 0.1000000000001 s
- 1.0 s to 2.0 s: time step of 0.2 s
- 2.0 s to 8.0 s: time step of 0.5 s
- 8.0 s to 20.0 s: time step of 2.0 s
- 20.0 s to 60.0 s: time step of 4.0 s
- 60.0 s onwards: time step of 4.0 s

### Outputs
At every exact time step, record the temporal evolution of fluid pressure, element physical aperture, hydraulic aperture, and element area for all elements in the fracture subregion. Combine these into a time-history collection stored in an HDF5 file named "KGD_validation_output". We also need a periodic VTK-format spatial output of the domain and a restart file dumped periodically.

XML files to create: kgdValidation_base.xml, kgdValidation_benchmark.xml
--- END SIMULATION SPECIFICATION ---

--- SCOPE ---
Deliverable: the XML input deck in /workspace/inputs/. You are scored on the deck's
structure against a reference deck; nothing downstream reads simulation output.
Once the deck is complete and well-formed, it is finished.
--- END SCOPE ---
