# GEOS input deck: ExampleVerticalPoroElastoPlasticWellbore

GEOS is an open-source multiphysics simulator. This task asks you to author one or
more XML input files specified by the simulation specification below.

- The GEOS source tree (examples, documentation, XML schema) is at `/geos_lib`
  (read-only). Consult it for examples and documentation.
- Write your deck (one or more `.xml` files) under `/workspace/inputs/`.
- `xmllint` is available for checking well-formedness. There is no GEOS binary:
  do not try to build or run GEOS.

--- BEGIN SIMULATION SPECIFICATION ---
I need to simulate a coupled hydromechanical problem centered on a vertical wellbore in a porous medium. Specifically, I'd like to model fluid diffusion and poromechanical deformation using a single-phase flow model fully coupled with a solid mechanics model. I want to build two versions of this scenario: a purely poroelastic benchmark that I can check against analytical solutions, and a poroplastic benchmark to evaluate induced plasticity around the wellbore. 

Please construct both scenarios by dividing them into base reusable configurations and execution/benchmark configurations.

### Geometry and Mesh
The conceptual domain is a half-cylinder block for a vertical well. Generate an internal radial wellbore mesh using 8-node hexahedral elements. The radial extent goes from an initial radius of 0.1 m to an outer radius of 5.0 m. The azimuthal angle sweeps from 0 to 180 degrees, and the vertical (Z) extent goes from -1.0 m to 1.0 m. The wellbore trajectory is perfectly vertical, originating from coordinates `(0.0, 0.0, -1.0)` and going to `(0.0, 0.0, 1.0)`. 
We want 80 elements in the tangential direction, 2 elements in the vertical Z direction, and 40 radial elements automatically spaced. Ensure the outer boundary aligns with the cylindrical geometry (do not enforce a structured Cartesian outer boundary block).

### Phase and Material Properties
The porous domain contains water and rock, fully defined in SI units. 
For the water phase:
- Density: 1000.0 kg/m³ (with a reference density of 1000.0 kg/m³)
- Viscosity: 0.001 Pa·s (reference viscosity 0.001 Pa·s, no viscosibility)
- Compressibility: 2.09028227021e-10 1/Pa
- Reference pressure: 0.0 Pa

For the solid matrix porosity and permeability:
- Reference porosity: 0.3
- The rock grains are essentially incompressible; set their bulk modulus to 1.0e27 Pa.
- The intrinsic permeability is isotropic at 1.0e-20 m².

For the Solid Mechanics (Rock):
- Base density: 2700.0 kg/m³
- Bulk Modulus: 11.11 GPa
- Shear Modulus: 8.33 GPa

**Poroelastic version:** Use an isotropic linear elastic constitutive model for the bulk rock.
**Poroplastic version:** Use an extended Drucker-Prager plasticity model. In addition to the elastic properties, use the following failure envelope properties:
- Cohesion: 1.0 MPa
- Initial friction angle: 15.27 degrees
- Residual friction angle: 23.05 degrees
- Dilation ratio: 1.0
- Hardening rate: 0.01 

### Initial and Boundary Conditions
Initialize the domain with the following uniform far-field in-situ stresses and pressures:
- Minimum horizontal stress (X direction): -9.0 MPa
- Maximum horizontal stress (Y direction): -11.0 MPa
- Vertical stress (Z direction): -12.0 MPa
- Initial pore pressure: 0.0 MPa

*Note: Tensile stresses are positive, so these compressive stresses are negative.*

At the wellbore wall (inner radius), the excavation and circulating mud apply a boundary load. Apply this using a time-dependent multiplier function: 
- At time 0.0 s, multiplier is 0.0
- At time 0.1 s, multiplier is 1.0
- At time 1,000,000.0 s, multiplier is 1.0

Applying this time function, set:
- A compressive mechanical normal traction of -10.0 MPa at the inner wellbore face.
- A fluid pressure boundary condition of 10.0 MPa at the inner wellbore face.

For the outer boundary conditions, apply standard roller constraints (0.0 mm displacement):
- Constrain X-displacement at the negative and positive X-extremes.
- Constrain Y-displacement at the tangential extremes and the positive Y-extreme.
- Constrain Z-displacement at the negative and positive Z-extremes.

### Solvers and Numerical Methods
Setup a multiphysics workflow bounding a finite-volume single-phase flow solver and a finite-element Lagrangian solid mechanics solver into a coupled poromechanics solver. 
- **Solid mechanics discretization:** Use finite elements with linear basis functions (order 1). The mechanics solver's nonlinear loop should have a Newton tolerance of 1.0e-5 and a max of 15 iterations.
- **Flow discretization:** Use a two-point flux approximation (TPFA) for the finite volumes. The flow solver's nonlinear loop should have a Newton tolerance of 1.0e-6 and max of 8 iterations.
- **Coupling Scheme:** Drive the coupling with a direct parallel-disabled linear solver. The coupled nonlinear solver should allow a maximum of 40 iterations. Turn off gravity for the model.

### Time Schedule and Output
The entire simulation should run for 497,639.940531 seconds.
Force a fixed simulation timestep of 497.639940531 seconds for the coupled solver.
Generate standard visualization outputs (Silo format with a "plot" file root) every 4,976.39940531 seconds, enforcing an exact temporal match for these outputs. Also, include restart file outputs.

Put the physics configurations into base files and use the benchmark files to define the mesh, include those base files, and drive the solver schedules.

XML files to create: PoroDruckerPragerWellbore_base.xml, PoroDruckerPragerWellbore_benchmark.xml, PoroElasticWellbore_base.xml, PoroElasticWellbore_benchmark.xml
--- END SIMULATION SPECIFICATION ---

--- SCOPE ---
Deliverable: the XML input deck in /workspace/inputs/. You are scored on the deck's
structure against a reference deck; nothing downstream reads simulation output.
Once the deck is complete and well-formed, it is finished.
--- END SCOPE ---
