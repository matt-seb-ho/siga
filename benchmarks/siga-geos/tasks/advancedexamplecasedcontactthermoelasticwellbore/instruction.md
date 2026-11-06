# GEOS input deck: AdvancedExampleCasedContactThermoElasticWellbore

GEOS is an open-source multiphysics simulator. This task asks you to author one or
more XML input files specified by the simulation specification below.

- The GEOS source tree (examples, documentation, XML schema) is at `/geos_lib`
  (read-only). Consult it for examples and documentation.
- Write your deck (one or more `.xml` files) under `/workspace/inputs/`.
- `xmllint` is available for checking well-formedness. There is no GEOS binary:
  do not try to build or run GEOS.

--- BEGIN SIMULATION SPECIFICATION ---
I need a coupled thermo-hydro-mechanical (THM) simulation of a cased wellbore to study thermal debonding at the casing-cement and cement-rock interfaces. We are injecting cold CO2, which cools the inner casing surface, inducing thermal stresses that may lead to interfacial debonding. Although we are using a fully coupled THM solver to capture the poro-thermo-elastic interactions and mechanics of the structural interfaces, there is no actual fluid flow occurring—heat transfer is purely conductive.

### Physical Model and Geometry
The domain represents a horizontal slice of a vertical wellbore. To save computational time, use an axisymmetric plane strain assumption by modeling a 90-degree quarter-cylinder sector (theta from 0 to 90 degrees) with a thickness in the z-direction of 0.1 m (from z = 0.0 to 0.1). 

The wellbore internal geometry consists of three nested layers:
- Inner steel casing: radius from 0.15707 m to 0.17780 m
- Cement sheath: radius from 0.17780 m to 0.21272 m
- Rock formation: radius from 0.21272 m to an outer far-field boundary at 1.5707 m.

To allow separation, incorporate mechanical interfaces at the structural boundaries. Define the casing-cement interface as a cylinder centered around a radius of 0.17780 m (bounding from 0.17779 m to 0.17781 m, extending z from -0.001 to 0.101 m). Define the cement-rock interface similarly around a radius of 0.21272 m (bounding from 0.21271 m to 0.21273 m, extending z from -0.001 to 0.101 m). 

### Material Properties
Treat the casing, cement, and rock as linear elastic, isotropic, porous materials. Because flow is negligible, set the matrix permeabilities of all three materials to essentially zero (e.g., 1.0e-100 m²). The saturating single-phase fluid has a reference density of 1000 kg/m³, viscosity of 1e-3 Pa-s, reference pressure of 0.0 Pa, reference temperature of 20.0 °C, compressibility of 5e-10 1/Pa, thermal expansion coefficient of 1e-10 1/K, and specific heat capacity of 1.0 J/(kg-K).

**Steel Casing:**
- Density: 7500 kg/m³
- Bulk modulus: 159.4202899 GPa
- Shear modulus: 86.61417323 GPa
- Drained linear thermal expansion coefficient: 1.2e-5 1/K
- Reference volumetric heat capacity: 1.375e6 J/(m³-K)
- Thermal conductivity: 15.0 W/(m-K)
- Porosity: 1.0e-6, with a Biot grain bulk modulus identical to the matrix bulk modulus (159.4202899 GPa).

**Cement:**
- Density: 2700 kg/m³
- Bulk modulus: 2.298850575 GPa
- Shear modulus: 1.652892562 GPa
- Drained linear thermal expansion coefficient: 2.0e-5 1/K
- Reference volumetric heat capacity: 4.2e6 J/(m³-K)
- Thermal conductivity: 1.0 W/(m-K)
- Porosity: 1.0e-6, with grain bulk modulus 2.298850575 GPa.

**Rock Formation:**
- Density: 2700 kg/m³
- Bulk modulus: 5.535714286 GPa
- Shear modulus: 3.81147541 GPa
- Drained linear thermal expansion coefficient: 2.0e-5 1/K
- Reference volumetric heat capacity: 4.56e6 J/(m³-K)
- Thermal conductivity: 1.66 W/(m-K)
- Porosity: 1.0e-6, with grain bulk modulus 5.535714286 GPa.

**Contact Interfaces:**
- The mechanical interfaces should use a Coulomb friction law with a friction coefficient of 0.5 and zero cohesion. 
- Initialize the interfaces as already ruptured and separable. 
- The default mechanical aperture is 5.0e-4 m. Relate hydraulic aperture to mechanical aperture via a simple table: an opening of -1e-3 m yields 1e-4 m aperture, and an opening of 0.0 m yields 1e-3 m aperture.
- Parallel plate permeability applies. Provide a uniform fracture thermal conductivity of 1.0 W/(m-K) to allow heat flow across the contacts. Set the initial crack toughness to 1.0e6 J/m².

### Initial and Boundary Conditions
- **In-situ conditions:** Set the initial temperature to 100 °C throughout the domain. Initial pore pressure and initial stress components are zero.
- **Thermal boundaries:** Fix the temperature at the outer rock boundary to the in-situ 100 °C. Apply a sharp temperature drop at the inner casing boundary, fixing it at -20 °C to simulate the cold CO2.
- **Hydraulic boundaries:** Maintain the pore pressure at 0 Pa on both the inner and outer radial boundaries.
- **Mechanical boundaries:** Apply plane strain and symmetry restrictions. Total displacement in the z-direction must be zero on the top and bottom faces. Total displacement must be constrained radially on the symmetry planes (tangential negative/positive surfaces) to maintain the wedge geometry, and radial displacement must be clamped to zero at the far-field rock boundary. The normal traction at the inner casing wall is zero. 

### Numerical Setup and Deliverables
Use a conforming Lagrangian finite-element approach for solid mechanics with explicit tracking of the contact interfaces, coupled to a finite-volume two-point flux approximation (TPFA) for poromechanics and thermal conduction. The primary solver needs to step initial dt = 1e-3 s and handle the coupled multiphysics directly.

Please structure the problem into a set of three files:
1. **A reusable base file** encompassing solvers, material physics, fields, collections, and output specifications. Track time histories for displacement, fracture displacement jumps, as well as temperature and stress broken out individually for the casing, cement, and rock blocks. Also provision a VTK generic field output and a restart output.
2. **A benchmark input file** that imports the base settings. The mesh here should use first-order hexahedral elements with 5 radial subdivisions each for the casing, cement, and rock layers, keeping the rock spacing geometrically auto-spaced. Use 40 angular subdivisions and 1 vertical subdivision. Run the simulation to a maximum time of 1.1e5 s. Record history variables and invoke the solver step every 1e3 s. Dump full history files and VTK states every 1e4 s.
3. **A smoke test input file** (also importing the base settings) for quick continuous integration verification. Degrade the mesh to 2 radial cells per domain layer and 4 angular subdivisions. Limit the simulation time to 1.0 s, stepping both the solver and VTK dumps every 1.0 s, and history variables continuously.

XML files to create: CasedThermoElasticWellbore_ImperfectInterfaces_base.xml, CasedThermoElasticWellbore_ImperfectInterfaces_benchmark.xml, CasedThermoElasticWellbore_ImperfectInterfaces_smoke.xml
--- END SIMULATION SPECIFICATION ---

--- SCOPE ---
Deliverable: the XML input deck in /workspace/inputs/. You are scored on the deck's
structure against a reference deck; nothing downstream reads simulation output.
Once the deck is complete and well-formed, it is finished.
--- END SCOPE ---
