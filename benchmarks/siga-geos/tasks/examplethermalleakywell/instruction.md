# GEOS input deck: ExampleThermalLeakyWell

GEOS is an open-source multiphysics simulator. This task asks you to author one or
more XML input files specified by the simulation specification below.

- The GEOS source tree (examples, documentation, XML schema) is at `/geos_lib`
  (read-only). Consult it for examples and documentation.
- Write your deck (one or more `.xml` files) under `/workspace/inputs/`.
- `xmllint` is available for checking well-formedness. There is no GEOS binary:
  do not try to build or run GEOS.

--- BEGIN SIMULATION SPECIFICATION ---
This is a request to build a physical simulation of a non-isothermal CO2 leakage problem through an abandoned well in a saline aquifer. The simulation relies on a fully compositional multiphase flow model to track mass exchange between phases using realistic, tabular fluid properties that are sensitive to temperature and pressure. The model operates under the assumption of a static geothermal gradient—meaning the energy equation is not dynamically solved, but the temperature profile strictly governs fluid properties like density, viscosity, and solubility.

### Domain Geometry and Mesh
The domain represents two aquifers separated by an aquitard. Its overall dimensions are 1000 m in the X and Y directions (spanning from -500 m to +500 m) and 160 m in depth (spanning from -800 m to -640 m in the Z direction). 

Generate a structured, hexahedral internal mesh with the following coordinates to define the internal cell blocks and cleanly resolve the wells:
- **X borders:** -500, -0.1329, 0.1329, 99.8671, 100.1329, 500 (with element counts: 50, 1, 20, 1, 40)
- **Y borders:** -500, -0.1329, 0.1329, 500 (with element counts: 50, 1, 50)
- **Z borders:** -800, -770, -670, -640 (with element counts: 20, 30, 10)

This creates a grid with 3 vertical zones:
1. **Bottom Aquifer:** Z from -800 m to -770 m.
2. **Aquitard:** Z from -770 m to -670 m.
3. **Top Aquifer:** Z from -670 m to -640 m.

Within this mesh, we need to assign standard regions to assign materials:
- **Injection Well:** Located entirely in the bottom aquifer, bounded horizontally between X = [99.8671, 100.1329] and Y = [-0.1329, 0.1329].
- **Leaky Well:** Extends vertically through all three layers (bottom aquifer, aquitard, top aquifer), bounded horizontally between X = [-0.1329, 0.1329] and Y = [-0.1329, 0.1329].
- **Aquifer Top and Bottom:** Cover their respective vertical layers, aside from the cells identified as the leaky well or injection well.
- **Barrier:** Represents the impermeable aquitard (except where the leaky well passes through) and the top portion directly above the injection well. The barrier elements should remain unassigned to any material to make them inactive to flow.

### Rock Materials and Relative Permeability
The solid matrix uses a compressible model with a constant reference porosity of 0.15 (at a reference pressure of 10 MPa) and a constant rock compressibility of 0.0.
- For the standard rock regions (both aquifers), set the isotropic permeability to 2.0e-14 m².
- For both the injection well and leaky well, set the isotropic permeability to 1.0e-12 m².

The multiphase flow properties (relative permeability and capillary pressure) between the gas phase and the water phase rely entirely on user-provided lookup tables. Use external files named `relPerm_water.txt`, `relPerm_gas.txt`, and `capPres_water.txt`. Map these to the local phase volume fractions using the coordinate files `phaseVolumeFraction_water.txt` and `phaseVolumeFraction_gas.txt`.

### Fluid Properties
The fluid system consists of two phases (gas and water) containing two components (CO2 and water). Component molar weights are 44 g/mol for CO2 and 18 g/mol for water. Because of the complex thermal dependence of the fluids, we use a tabular Phillips brine equation-of-state. Parameterize the PVT properties using external files `pvtgas.txt` and `pvtliquid.txt`, and use `co2flash.txt` for the CO2 solubility flash calculations. 

### Initial State
Initialize the pressure of the active domain by establishing a hydrostatic equilibrium. 
- The reference datum is at an elevation of Z = -800 m, with a datum pressure of 8.499 MPa. 
- The domain is initially liquid-filled. Use tables to specify a tiny background global composition of CO2 (1.0e-6) and water (0.999999) constant across all depths.
- Apply a geothermal gradient of 0.03 K/m throughout the depth. Specifically, configure a temperature table such that T = 307.15 K at Z = -800 m and T = 302.35 K at Z = -640 m.

### Boundary Conditions
Apply Dirichlet boundary conditions for pressure, temperature, and composition on the four lateral sides of the domain (East, West, North, and South). Establish bounding boxes extending 0.01 m outward/inward from the exact ±500 m borders to robustly flag these faces.
- Fix temperature on the lateral faces to match the initial geothermal gradient tabular profile.
- Fix the CO2 and water global component fractions to 1.0e-6 and 0.999999, respectively.
- For pressure, apply a 3D linear interpolation tied to spatial face centers, using the external files `xlin.geos`, `ylin.geos`, `zlin.geos`, and `pressure.geos`.

### Injection Operations
We inject CO2 at a constant mass flow rate. Setup a uniform mass flux source inside the injection well bounds (specifically limit it to a bounding box: X = 99.85 to 100.15, Y = -0.15 to 0.15, Z = -801 to -769). The injection rate for the CO2 component is exactly -8.87 kg/s.

### Numerical Solver and Time Integration
Use a compositional multiphase finite volume solver based on two-point flux approximation (TPFA) applied to the internal grid. Even though temperatures are evaluated from a static table based on depth, the generic solver configuration requires a base reference temperature (provide 307.15 K). Enable mass conservation formulations.
- Non-linear solver: standard Newton iterations (max 20, tolerance 1e-3, target max line-search cuts 5).
- Linear solver: FGMRES iterative procedure using an MGR preconditioner with a Krylov tolerance of 1e-4.
- Initial timestep should be 1.0 s, allowing the nonlinear solver to dictate subsequent increases.

To manage the problem scope, please implement this using two configuration files:
1. A reusable "base" file containing the events, methods, element regions, bounding boxes, materials, fluid properties, field constraints, tables, tasks, and outputs.
2. A "benchmark" file that includes the base file and defines the specific internal mesh geometry and the solver parameterization.

Run the simulation to a maximum time of 10 days (864,000 seconds). Request the generation of full state VTK outputs every 10 days. Also, log scalar time history, statistics, and run restarts every 5 days (432,000 s).

To track leakage behavior over time, set up a special task to collect the total component outflux passing upward through the specific grid block corresponding to the leaky well intersection with the aquitard (the center block in the aquitard layer). Include this collection task's data hook in your scalar history output.

XML files to create: thermalLeakyWell_base.xml, thermalLeakyWell_benchmark.xml
--- END SIMULATION SPECIFICATION ---

--- SCOPE ---
Deliverable: the XML input deck in /workspace/inputs/. You are scored on the deck's
structure against a reference deck; nothing downstream reads simulation output.
Once the deck is complete and well-formed, it is finished.
--- END SCOPE ---
