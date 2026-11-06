# GEOS input deck: AdvancedExampleCasedThermoElasticWellbore

GEOS is an open-source multiphysics simulator. This task asks you to author one or
more XML input files specified by the simulation specification below.

- The GEOS source tree (examples, documentation, XML schema) is at `/geos_lib`
  (read-only). Consult it for examples and documentation.
- Write your deck (one or more `.xml` files) under `/workspace/inputs/`.
- `xmllint` is available for checking well-formedness. There is no GEOS binary:
  do not try to build or run GEOS.

--- BEGIN SIMULATION SPECIFICATION ---
Here is the simulation setup requested for a thermoelastic analysis of a cased wellbore. We want to conduct a fully-implicit single-phase poromechanics simulation with thermal effects, capturing the thermal conduction and related thermal stress responses in the casing, cement, and surrounding rock. Because we are focusing isolating the solid mechanics and heat diffusion, fluid flow will be artificially blocked by eliminating permeability.

Please organize this as a single reusable base configuration, an integrated benchmark case with a fine grid and detailed monitoring, and a lightweight smoke test for quick checks.

### Physics and Numerical Methods
The model requires a fully implicit thermoelastic formulation. We need to solve for 3D displacement and temperature. Use a 1st-order Lagrangian finite element method for the solid mechanics and a two-point flux approximation (TPFA) finite volume method for the thermal diffusion. Configure a Newton solver allowing up to 100 iterations per step and a maximum residual norm of 1e19. Do not use direct parallel linear solvers (specify them as disabled). 

### Geometry and Meshing
We want to simulate a quarter of the wellbore domain in cylindrical geometry (0 to 90 degrees azimuthally) using standard hexahedral elements (C3D8), mapping to a full Cartesian grid. Assume a plane-strain configuration horizontally, so restrict the vertical Z coordinate between 0.0 and 0.1 m with a single vertical element layer. The wellbore trajectory is perfectly vertical (from {0,0,0} to {0,0,0.1} in XYZ). 

The domain consists of three annular regions:
1. Inner steel casing: extending from radius 0.15707 m to 0.1778 m.
2. Cement sheath: extending from radius 0.1778 m to 0.21272 m.
3. Rock formation: extending from radius 0.21272 m outwards to a far-field boundary at 1.5707 m. 

For the **Benchmark Case**, partition the mesh with 10 elements in the tangential direction, and 5 radial elements in each of the three layers (casing, cement, and rock). Enable optimized automatic radial geometric spacing for the elements in the rock layer, but leave it uniform for the casing and cement.
For the **Smoke Test Case**, use a much coarser grid: 4 elements in the tangential direction, and 2 radial elements per material layer. Again, use auto-spacing radially for the rock.

### Material Properties
We will deal with three solid materials (casing, cement, rock) interacting with a single compressible fluid phase. Because we are purely analyzing heat diffusion and thermo-mechanics without fluid convection, configure everywhere with negligible porosity (1e-6) and zero permeability (all directional components set to 1.0e-100 m²). We also want to force the Biot coefficient to identically zero, which you can do by using the same value for the grain's bulk modulus as the material's drained bulk modulus. The reference fluid properties don't heavily impact the mechanics here, but set its reference density to 1000 kg/m³, viscosity to 1e-3 Pa-s, reference pressure to 0.0 Pa, reference temperature to 20 °C, compressibility to 5e-10 1/Pa, thermal expansion coefficient to 1.0e-10 1/K, and its volumetric specific heat capacity and reference internal energy both to 1. Gravity can be ignored.

**Casing (Steel):**
* Mechanics: Drained bulk modulus 159.4202899e9 Pa (match this for the grain bulk modulus too), shear modulus 86.61417323e9 Pa. Bulk density 7500. Drained linear thermal expansion coefficient 1.2e-5.
* Thermal: Volumetric heat capacity 1.375e6, isotropic thermal conductivity 15.0 W/m-K (15 across all components).

**Cement:**
* Mechanics: Drained bulk modulus 2.298850575e9 Pa (match for grain bulk modulus), shear modulus 1.652892562e9 Pa. Bulk density 2700. Drained linear thermal expansion coefficient 2.0e-5.
* Thermal: Volumetric heat capacity 4.2e6, isotropic thermal conductivity 1.0.

**Rock:**
* Mechanics: Drained bulk modulus 5.535714286e9 Pa (match for grain bulk modulus), shear modulus 3.81147541e9 Pa. Bulk density 2700. Drained linear thermal expansion coefficient 2.0e-5.
* Thermal: Volumetric heat capacity 4.56e6, isotropic thermal conductivity 1.66.

Both the heat capacities and the internal energies are defined relative to 0 °C and 0 initial reference state.

### Boundary and Initial Conditions
Enforce plane strain by fully constraining total displacement in the Z-direction for both the upper and lower mesh bounds. Support the quarter-symmetry by constraining the Y-displacement to zero at the 0-degree tangent, and X-displacement to zero at the 90-degree tangent. The far-field outer radial boundary is assumed fixed, so constrain both X and Y components of total displacement to 0 there. 

Set the initial pressure to 0 Pa everywhere. Secure this across the boundary by enforcing 0 Pa on both the inner wellbore face and the outer far-field boundary. Set exactly zero normal traction on the inner surface.

Set an initial uniform reservoir temperature of 100 °C everywhere, and maintain this 100 °C as a constant boundary condition at the far-field boundary. Simulate cooling from the wellbore by imposing a constant -20.0 °C temperature at the inner casing radial boundary. Initialize all components of actual physical stress (X, Y, and Z) relative to this starting state at 0.0 Pa for the casing, cement, and rock materials.

### Simulation Scheduling and Diagnostics
Run both the Benchmark case and Smoke test cases out to a total simulation time of 1e5 seconds. 
Request VTK 3D field outputs every 1e4 seconds and generate restart safety saves every 5e4 seconds. 

For the **Benchmark Case**, restrict the primary solver application step size to a maximum of 1e3 seconds. Also, we want to extract scalar time histories to evaluate transient changes. Every 1e4 seconds (force the dt constraint), pack and collect the block-level temperature, block-level stress tensors (for the casing, cement, and rock blocks individually), as well as nodal total displacements for the entire system, and write all of these to corresponding history files (e.g., temperatureHistory_casing, stressHistory_rock, displacementHistory, etc.).

For the **Smoke Test Case**, no time histories need to be extracted. Let the main solver take larger steps up to a max dt of 1e4 seconds to speed up testing. 

XML files to create: CasedThermoElasticWellbore_base.xml, CasedThermoElasticWellbore_benchmark.xml, CasedThermoElasticWellbore_smoke.xml
--- END SIMULATION SPECIFICATION ---

--- SCOPE ---
Deliverable: the XML input deck in /workspace/inputs/. You are scored on the deck's
structure against a reference deck; nothing downstream reads simulation output.
Once the deck is complete and well-formed, it is finished.
--- END SCOPE ---
