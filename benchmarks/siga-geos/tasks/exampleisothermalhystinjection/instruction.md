# GEOS input deck: ExampleIsothermalHystInjection

GEOS is an open-source multiphysics simulator. This task asks you to author one or
more XML input files specified by the simulation specification below.

- The GEOS source tree (examples, documentation, XML schema) is at `/geos_lib`
  (read-only). Consult it for examples and documentation.
- Write your deck (one or more `.xml` files) under `/workspace/inputs/`.
- `xmllint` is available for checking well-formedness. There is no GEOS binary:
  do not try to build or run GEOS.

--- BEGIN SIMULATION SPECIFICATION ---
I need to configure a series of compositional multiphase flow simulations to study CO2 plume migration, solubility trapping, and residual trapping in geological formations. This is based on the benchmark problem from Class et al. (2009), modeled specifically for a deeply buried, simplified reservoir (similar to the Johansen formation). 

We need to build two reusable base simulation configurations—one evaluating purely drainage behavior and another modeling relative permeability hysteresis—along with a small 3D smoke test to verify the hysteretic setup on a fast, coarse mesh.

### Materials and Fluid Properties
The problem involves a fully miscible two-phase fluid system consisting of an aqueous brine phase and a CO2-rich gas phase, composed of H2O and CO2 components. Use molar masses of 44 g/mol for CO2 and 18 g/mol for water. 

The brine density and viscosity should follow an Ezrokhi correlation. We have provided external property tables that must be used:
- Gas PVT: `tables/pvtgas.txt`
- Brine PVT: `tables/pvtliquid_ez.txt`
- Flash model parameters: `tables/co2flash.txt`

The rock formation should be modeled as a slightly compressible porous medium. Isotropic permeability is constant at 1.0e-12 m² (roughly 1 Darcy). The reference rock porosity is 10% (0.1) defined at a reference fluid pressure of 10 MPa (1.0e7 Pa), with a solid reservoir compressibility of 4.5e-10 1/Pa. 

### Multiphase Flow Constraints
Both base configs must evaluate primary fluid flow using a finite-volume approximation (specifically, two-point flux approximation) and should track mass arrays. Upwinding for fractions must allow a maximum composition change of 0.2 per step, at a reference temperature of 363 K. Capillary pressure between the liquid and gas phases is given by a table look-up using fraction coordinates `tables/phaseVolumeFraction_water.txt` mapping to values in `tables/capPres_water.txt`. 

We are separating the relative permeability setups into two distinct configurations:
1. **Drainage-Only Base Case:** Use single table lookups for each phase's relative permeability. Water and gas use `tables/phaseVolumeFraction_water.txt` and `tables/phaseVolumeFraction_gas.txt` mapping to `tables/relPerm_water.txt` and `tables/relPerm_gas.txt`, respectively.
2. **Hysteresis Base Case:** Introduce hysteretic behavior by supplying independent drainage and imbibition relative permeability boundaries. Drainage water and gas use mappings defined in `tables/drainagePhaseVolFraction_water.txt` and `tables/drainagePhaseVolFraction_gas.txt` mapped to their corresponding `tables/drainageRelPerm_{phase}.txt` values. The imbibition bounding curves map `tables/imbibitionPhaseVolFraction_{phase}.txt` to `tables/imbibitionRelPerm_{phase}.txt`.

### Initial and Boundary Conditions
The reservoir starts totally saturated with brine, under hydrostatic state. 
- Initialize it from a datum elevation of -3000 m and a datum pressure of 30 MPa.
- The initial composition is essentially pure water (water mass fraction 0.999999, CO2 mass fraction 0.000001) uniform across the vertical column (tabulated strictly between elevations -3238.2 m and -2506.13 m).
- Impose a linear geothermal gradient mapping: at elevation -3238.2 m the temperature is 380.296 K, and at -2506.13 m it is 358.334 K.

For the boundaries (applied cleanly to the bounding exterior faces identified as face set 3):
- Fix the composition to match the initial pure brine saturation.
- Lock boundary temperature and pressure gradients by mapping coordinates from external linear spatial grids (`fc_tables/xlin.geos`, `fc_tables/ylin.geos`, `fc_tables/zlin.geos`) using linear interpolation against voxel maps `fc_tables/temperature.geos` and `fc_tables/pressure.geos`. 

### Wellbore Injection
A single, vertical top-down injection well injects pure CO2 (component stream fraction 1.0 CO2, 0.0 water) at an injection temperature of 353.15 K.
- Reference baseline parameters: well bottom reference elevation is -3000 m, with a target bottom hole pressure of 100 MPa. Do not enable crossflow into the formation.
- Standard surface conditions dictate fluid property conversions: 101,325 Pa and 288.71 K.
- Volumetric injection schedule (total volume rate controls applied to both setups): We will linearly sample step inputs using a continuous time sequence: 8.02849025 m³/s at start, dropping to 0 at 7.7198e8 s (about ~24.5 years), and staying at zero through to 1.544e9 s. 

*Note: For the non-hysteretic drainage base case only, also configure two secondary alternate well control objects for mass-rate injection. Both alternate controls enforce a 15 kg/s steady target—one explicitly using a constant rate hook, and one referencing an identical time-table (15 kg/s up to 7.7198e8 s, then 0).*

### Base Case Solver Requirements
We will couple a generic multiphase flow solver and an explicit multi-segment wellbore solver under a global implicit reservoir scheme. Time stepping should start at 100 seconds. 
Ensure the linear solver strategy calls an FGMRES algorithm preconditioned with MGR, aiming for a Krylov tolerance of 1e-6.
- The Non-Hysteretic solver loop will iterate up to 40 times per time step with a Newton convergence tolerance of 1.0e-5.
- The Hysteretic solver setup tends to oscillate locally, so constrain the nonlinear loop to a maximum of 12 Newton iterations with a slightly relaxed tolerance of 1.0e-3.

### 3D Smoke Test Verification
Finally, set up a minimal 3D structured domain that inherits everything directly from the hysteretic base. 
- **Mesh Domain:** Create an idealized 5x5x5 internal hexahedral grid. Dimensions should span X: [5240, 5640] m, Y: [3100, 3500] m, and depths Z: [-3000, -2950] m. Apply default continuous solid materials to a block named `1_hexahedra`.
- **Well Construction:** Embed the well structurally in the grid. It forms a uniform vertical well path tracking linearly from X=5440, Y=3300, Z=-2950 to the bottom at Z=-3000. It consists of 1 wellbore segment discretized into 5 equally spaced elements. Define 5 perforations located at distances of 45, 35, 25, 15, and 5 meters down from the wellhead. Set the internal wellbore radius to 0.1 m.
- **Simulation Time & Control:** Maximum simulation horizon is short, 1e6 seconds. The simulation solver should push using exact, rigid dt forcing of 1e5 s.
- **Diagnostics:** Capture standard 3D visualizations and integrated compositional mass statistics globally and dynamically per region. Visualization dumps and statistics triggers happen every 1e5 s. Checkpointing restarts are scheduled every 5e5 s. 

XML files to create: class09_pb3_drainageOnly_iterative_base.xml, class09_pb3_hystRelperm_iterative_base.xml, class09_pb3_smoke_3d.xml
--- END SIMULATION SPECIFICATION ---

--- SCOPE ---
Deliverable: the XML input deck in /workspace/inputs/. You are scored on the deck's
structure against a reference deck; nothing downstream reads simulation output.
Once the deck is complete and well-formed, it is finished.
--- END SCOPE ---
