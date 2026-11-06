# GEOS input deck: ExampleThermoporoelasticConsolidation

GEOS is an open-source multiphysics simulator. This task asks you to author one or
more XML input files specified by the simulation specification below.

- The GEOS source tree (examples, documentation, XML schema) is at `/geos_lib`
  (read-only). Consult it for examples and documentation.
- Write your deck (one or more `.xml` files) under `/workspace/inputs/`.
- `xmllint` is available for checking well-formedness. There is no GEOS binary:
  do not try to build or run GEOS.

--- BEGIN SIMULATION SPECIFICATION ---
I am looking to run a one-dimensional thermoporoelastic consolidation benchmark based on the analytical solution by Bai (2005). The problem involves a fully coupled response of solid deformation, single-phase fluid flow, and heat transfer in a saturated porous medium. I need the model structured with a reusable base configuration that can be included in a full benchmark run and a companion smoke test.

**Domain and Spatial Discretization**
Although the physical problem is a 1D column, please simulate it using a 3D block geometry aligned such that the consolidation happens along the y-axis. Use first-order finite elements for the solid mechanics and a finite volume scheme with a two-point flux approximation for the fluid and heat flow. 

**Material Properties**
The domain consists of a single homogeneous, isotropic rock matrix fully saturated with water. For the solid mechanics, assume a linear elastic material with a bulk modulus of 10,000 Pa and a shear modulus of 2,143 Pa (which maps to a Young's modulus of 6,000 Pa and a Poisson's ratio of 0.4). The solid has a constant density of 2,400 kg/m³ and a drained linear thermal expansion coefficient of 3.0 × 10⁻⁷ K⁻¹. The volumetric heat capacity of the rock should be set to 1.672 × 10⁵ J/(m³·K).

For the poroelastic properties, use a reference porosity of 0.2 and a grain bulk modulus of 1.0 × 10²⁷ Pa. The porosity thermal expansion coefficient should match the linear solid expansion at 3.0 × 10⁻⁷ K⁻¹. Set the permeability to an isotropic 4.0 × 10⁻⁹ m² and the thermal conductivity to an isotropic 836 J/(m·s·K). 

For the fluid (water), assume completely constant properties with no dependence on pressure or temperature (zero compressibility, zero thermal expansion, zero viscosibility). Use a constant density of 1,000 kg/m³, a viscosity of 1.0 × 10⁻³ Pa·s, and a specific heat capacity of 167.2 J/(kg·K). The reference pressure and temperature for the fluid should be explicitly set to 0.0 Pa and 273.0 K, respectively, with an initial reference internal energy of 0.001.

**Initial Conditions and Physics Configuration**
We can ignore the effects of gravity for this problem (set the gravity vector to exactly zero). The simulation should start in equilibrium at a baseline temperature of 273.0 K (0 °C), with an initial pore pressure of 0.0 Pa and initial normal stress components all set to 0.0 Pa. 

We require a fully implicit solution strategy tying together the mechanics, fluid, and thermal physics. The coupling solver should permit up to 200 Newton iterations. The single-phase flow solver needs to support thermal transport, allowing up to 100 Newton iterations with a tolerance of 1.0 × 10⁻⁶. 

**Boundary Conditions**
To limit deformation purely to the y-direction, apply roller constraints (zero normal displacement) on all lateral boundaries (x-min, x-max, z-min, z-max) as well as the bottom boundary (y-min). The sides and bottom should also be completely sealed to fluid flow and perfectly insulated.

At the top surface (the positive y-face), impose the following:
1. A maintained drained pore pressure of 0.0 Pa.
2. A constant elevated temperature boundary of 323.0 K (50 °C).
3. A compressive normal traction stress of -1.0 Pa. Because we want a sharp but stable loading, ramp the mechanical traction from 0.0 at time exactly zero to 1.0 at time 1.0 × 10⁻¹⁰ (and hold it at 1.0 thereafter), scaled by -1.0 so it resolves to a sudden step load.

**Outputs**
To compare against the 1D analytical solution (which predicts initial settlement followed by thermal rebound), we need to track time histories of the pore pressure, temperature, and total displacement throughout the entire domain block. Additionally, output standard VTK visualization files using the prefix `thermoPoro_consolidation_fim` and ensure the simulation writes restart files. 

XML files to create: ThermoPoroElastic_consolidation_base.xml, ThermoPoroElastic_consolidation_benchmark_fim.xml, ThermoPoroElastic_consolidation_smoke_fim.xml
--- END SIMULATION SPECIFICATION ---

--- SCOPE ---
Deliverable: the XML input deck in /workspace/inputs/. You are scored on the deck's
structure against a reference deck; nothing downstream reads simulation output.
Once the deck is complete and well-formed, it is finished.
--- END SCOPE ---
