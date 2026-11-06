# GEOS input deck: ExamplesingleFracCompression

GEOS is an open-source multiphysics simulator. This task asks you to author one or
more XML input files specified by the simulation specification below.

- The GEOS source tree (examples, documentation, XML schema) is at `/geos_lib`
  (read-only). Consult it for examples and documentation.
- Write your deck (one or more `.xml` files) under `/workspace/inputs/`.
- `xmllint` is available for checking well-formedness. There is no GEOS binary:
  do not try to build or run GEOS.

--- BEGIN SIMULATION SPECIFICATION ---
I am looking to simulate a single inclined fracture subjected to uniaxial shear compression in an infinite, homogeneous, isotropic elastic medium. The goal is to calculate the mechanical deformation in the surrounding rock and the frictional sliding along the fracture plane, so we can verify the numerical predictions of normal traction and slip against analytical solutions (e.g., Phan et al., 2003). I want to employ a Lagrangian contact mechanics approach to properly resolve the friction and displacement discontinuities on the fracture surface.

Please organize the problem into a set of three nested setup files for modularity:
1. A reusable "base" file that defines the bulk materials, friction laws, mathematical discretization, boundary/initial conditions, and output requests.
2. A "benchmark" geometry file (which includes the base file) that brings in the mesh and defines the spatial bounding boxes and planes for the domain.
3. An outermost "run" file (which includes the benchmark geometry file) to configure the contact mechanics solvers, stabilization methods, and the time-stepping event loop.

### Domain and Geometry
The continuum rock domain is discretized by first-order finite elements. Please import an unstructured external mesh file named `crackInPlane_benchmark.vtu` and label it `CubeHex`. 

Within the computational domain, define the fracture geometry as a rectangle. The fracture has an inclination angle of 20 degrees. Specifically, use an origin of `{0.0, 0.0, 0.0}`, a normal vector of `{-0.342020143325669, 0.939692620785908, 0.0}`, a length vector of `{0.939692620785908, 0.342020143325669, 0.0}`, a width vector of `{0.0, 0.0, 1.0}`, and dimensions of 2 by 10. The fracture represents a discontinuous surface region within the bulk cell elements. Define an identically sized and oriented rectangle to act as a core reference surface. 

For the boundaries, define spatial bounding boxes to apply constraints:
- Right point: `x` from 39.9 to 40.1, `y` from -40.1 to 40.1, `z` from -0.001 to 0.051
- Left point: `x` from -40.1 to -39.9, `y` from -40.1 to 40.1, `z` from -0.001 to 0.051
- Top point: `x` from -40.1 to 40.1, `y` from 39.9 to 40.1, `z` from -0.001 to 0.051
- Bottom point: `x` from -40.1 to 40.1, `y` from -40.1 to -39.9, `z` from -0.001 to 0.051
- Front: `x` and `y` from -40.1 to 40.1, `z` from -0.001 to 0.001
- Rear: `x` and `y` from -40.1 to 40.1, `z` from 0.049 to 0.051
- General `xmin` and `xmax` boxes matching the left and right point bounds, respectively.

### Materials
The surrounding rock behaves as an isotropic elastic material. Set the rock density to 2700 kg/m^3, the bulk modulus to 16.66666666666666 GPa, and the shear modulus to 10.0 GPa.

The contact constitutive behavior along the fracture is governed by the Coulomb failure criterion. Set the cohesion to 0.0 and the friction coefficient to 0.577350269 (which corresponds to a friction angle of 30 degrees). Specify a default initial fracture aperture of 1.0e-6 m.

### Initial and Boundary Conditions
To simulate the compressive loading, initialize the homogeneous standard rock stress in the x-direction (component 0) to exactly -1.0e8 Pa (using negative convention for compression). Set the initial state of the core surface to be separable and flag the fracture surface's rupture state to strictly broken/active (initialized as 1).

Apply zero-displacement roller constraints to the boundaries to establish plane strain deformation and hold the domain in place:
- Constrain x-displacement to 0.0 on the left and right boundaries.
- Constrain y-displacement to 0.0 on the top and bottom boundaries.
- Constrain z-displacement to 0.0 on the front and rear boundaries.

### Solvers and Numerics
We are modeling a quasi-static compression with no gravity (`{0.0, 0.0, 0.0}`). First, initialize the discontinuum using a surface generator solver placed on the fracture region, applying an initial rock toughness of 1.0e6.

Set up a finite-volume Two-Point Flux Approximation (TPFA) stabilization technique. Then, run the primary Solid Mechanics Lagrangian Contact solver, configuring it to couple the continuum block and the specific discontinuum fracture region. Apply the TPFA stabilization here with a stabilization scaling coefficient of 0.5. 

For the nonlinear solver, require line search actions, allowing up to 2 line search cuts and 2 time-step cuts. Set the maximum number of configuration attempts to 10, the maximum number of Newton iterations to 10, and a Newton tolerance of 1.0e-8. Use a direct linear solver without direct parallelism.

### Timing and Outputs
Run the underlying simulation from time 0.0 up to a maximum time of 1.0, forcing the solver to take step sizes of exactly 1.0 (an effective single-step equivalent). 

At every time step, collect time-history records of the `traction` and the relative slip (`displacementJump`) directly exclusively over the fracture face subregion. Save these data sets to separate HDF5 history files named `traction_history` and `displacementJump_history`. Additionally, write out standard restart files and ASCII-format VTK outputs (at a plot level of 2) for inspecting the full structural displacement fields. 

XML files to create: ContactMechanics_SingleFracCompression_benchmark.xml, SingleFracCompression_base.xml, SingleFracCompression_benchmark.xml
--- END SIMULATION SPECIFICATION ---

--- SCOPE ---
Deliverable: the XML input deck in /workspace/inputs/. You are scored on the deck's
structure against a reference deck; nothing downstream reads simulation output.
Once the deck is complete and well-formed, it is finished.
--- END SCOPE ---
