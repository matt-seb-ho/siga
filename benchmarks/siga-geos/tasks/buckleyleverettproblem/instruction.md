# GEOS input deck: buckleyLeverettProblem

GEOS is an open-source multiphysics simulator. This task asks you to author one or
more XML input files specified by the simulation specification below.

- The GEOS source tree (examples, documentation, XML schema) is at `/geos_lib`
  (read-only). Consult it for examples and documentation.
- Write your deck (one or more `.xml` files) under `/workspace/inputs/`.
- `xmllint` is available for checking well-formedness. There is no GEOS binary:
  do not try to build or run GEOS.

--- BEGIN SIMULATION SPECIFICATION ---
I need to set up a simulation to model a 1D Buckley-Leverett CO2 core flood experiment. The goal is to verify the immiscible displacement of brine by supercritical CO2 in a porous medium against analytical solutions. 

**Physical Problem and Domain Geometry**
The problem represents one-dimensional, horizontal, isothermal, immiscible transport of two-phase flow without capillary pressure or poromechanical effects. Since the numerical scheme requires a 3D grid, please create a hexahedral mesh of length 0.1 m in the x-direction, width 1.0 m in the y-direction, and thickness 0.00202683 m in the z-direction. Discretize the domain with 1000 cells in the x-direction, 1 cell in the y-direction, and 1 cell in the z-direction.

**Material and Fluid Properties**
The rock matrix is homogeneous and isotropic. 
- Permeability is 9.0e-13 m² in all directions.
- The reference porosity is 0.2 at a reference pressure of 10 MPa. Rock compressibility is extremely low (1.0e-15 1/Pa) to effectively eliminate geomechanical responses.
- Use a Brooks-Corey relative permeability model for the gas and water phases. Both phases have a residual saturation of 0.0, Corey exponents of 3.5, and maximum relative permeability values of 1.0. Capillary pressure is negligible.

We are modeling a water and gas (supercritical CO2) system at a constant ambient temperature of 300 K. Treat the fluids as incompressible.
- Surface density is 280.0 kg/m³ for gas and 992.0 kg/m³ for water.
- Molar weights are 0.044 kg/mol for gas and 0.018 kg/mol for water.
- Rely on external fluid property tables located at `buckleyLeverett_table/pvdg.txt` for gas and `buckleyLeverett_table/pvtw.txt` for water.

**Initial and Boundary Conditions**
Prior to injection, the domain is saturated with brine at a uniform pressure of 10 MPa. Set the initial composition globally to 99.9% water and 0.1% gas to establish the initial state.

For the boundaries:
- Define an inlet region at the x=0 face spanning up to x=0.0001 m. Apply a constant mass injection rate of pure CO2 (gas) at 0.00007 kg/s.
- Define an outlet region at the x=0.1 face starting from x=0.0999 m. Apply fixed controls to maintain the pressure at 10 MPa, the temperature at 300 K, and the composition at 99.9% water and 0.1% gas.

**Solver and Numerical Methods**
Please employ an isothermal compositional multiphase finite-volume solver, utilizing a two-point flux approximation (TPFA) scheme. 
- Run the simulation to a maximum time of 70.1 seconds.
- The initial time step should be 0.001 seconds, and the maximum allowed time step size should be limited to 0.01 seconds.
- Configure the nonlinear solver with a Newton tolerance of 1.0e-6, a maximum of 50 iterations, and allow up to 2 time step cuts and 2 line search cuts. Use a direct linear solver.

**Outputs**
We need two types of outputs to compare against the analytical Buckley-Leverett curves:
1. Capture the time history of the phase volume fractions evaluated inside all elements of the mesh. Record this history data every 10 seconds into an HDF5 file named `saturationHistory`.
2. Output the full spatially distributed field fields (such as pressure and saturation) into a VTK format at exactly 70 seconds for spatial contour visualization.

To keep things modular, please organize the inputs into two files: a reusable base configuration file containing the material formulations, fluid properties, initial/boundary conditions, and solver settings, and a separate benchmark file that builds the mesh, defines the geometry bounds, includes the base file, and schedules the simulation events.

XML files to create: buckleyLeverett_base.xml, buckleyLeverett_benchmark.xml
--- END SIMULATION SPECIFICATION ---

--- SCOPE ---
Deliverable: the XML input deck in /workspace/inputs/. You are scored on the deck's
structure against a reference deck; nothing downstream reads simulation output.
Once the deck is complete and well-formed, it is finished.
--- END SCOPE ---
