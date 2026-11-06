# GEOS input deck: AdvancedExampleViscoExtendedDruckerPrager

GEOS is an open-source multiphysics simulator. This task asks you to author one or
more XML input files specified by the simulation specification below.

- The GEOS source tree (examples, documentation, XML schema) is at `/geos_lib`
  (read-only). Consult it for examples and documentation.
- Write your deck (one or more `.xml` files) under `/workspace/inputs/`.
- `xmllint` is available for checking well-formedness. There is no GEOS binary:
  do not try to build or run GEOS.

--- BEGIN SIMULATION SPECIFICATION ---
I need to set up a single-element solver to simulate a triaxial compression test. The goal is to evaluate viscoplastic constitutive models under loading/unloading cycles. Specifically, I want to compare the numerical integration of a Visco Extended Drucker-Prager model against semi-analytical solutions based on the Perzyna time-dependent approach.

**Model Geometry and Region**
Since this is a test of a constitutive model and an integration algorithm, use a single generic 3D hexahedral element with unit dimensions (spanning 0 to 1 in x, y, and z, with 1 element in each direction). The cell block should be named `cellBlock01`. Since the element will be controlled by a specific material driver, you can map the mesh to a placeholder element region with a "dummy" material. 

**Reusable Material Library**
I want to establish a reusable base configuration that stores several geomechanical material models in a library, even though my current benchmark run will only execute one. Please define the following materials (all parameters in SI units):
- **Drucker-Prager**: density 2700 kg/m³, bulk modulus 10.0 GPa, shear modulus 6.0 GPa, cohesion 0.1 MPa, friction angle 6.0°, dilation angle 3.0°, and a hardening rate of 0.5 GPa.
- **Visco Drucker-Prager**: Same properties as the standard Drucker-Prager, but add a relaxation time of 0.1 s.
- **Extended Drucker-Prager**: density 2700 kg/m³, bulk modulus 10.0 GPa, shear modulus 6.0 GPa, cohesion 0.1 MPa, initial friction angle 6.0°, residual friction angle 10.0°, dilation ratio 0.5, and a yield hardening parameter of 0.0001.
- **Visco Extended Drucker-Prager**: Same properties as the Extended Drucker-Prager, plus a relaxation time of 0.1 s.
- **Modified Cam-Clay**: density 2700 kg/m³, reference pressure -0.1 MPa, reference volumetric strain 0.0, shear modulus 50 MPa (5e7 Pa), pre-consolidation pressure -0.15 MPa, critical state line slope 1.2, recompression index 0.002, and virgin compression index 0.003.
- **Visco Modified Cam-Clay**: Same parameters as the standard Modified Cam-Clay, with an added relaxation time of 0.1 s.

**Loading Profiles and Functions**
The state will be driven by external tabular histories. Define the following table functions in the base setup:
- `zeroStrain`: A constant zero function yielding 0.0 for times spanning 0.0 to 1e9 s.
- `strainFunction`: A table reading time coordinates from `tables/time.geos` and target values from `tables/axialStrain.geos`.
- `stressFunction`: A table reading time coordinates from identical `tables/time.geos` and values from `tables/radialStress.geos`.

**Triaxial Driver and Operating Conditions**
For the current benchmark case, simulate the Visco Extended Drucker-Prager material using a triaxial driver over a timeframe of 1.0 s. Setup the driver task to use a "mixed control" mode: it should apply axial control tracking the `strainFunction` and radial control tracking the `stressFunction`. 

The test begins from a pre-existing isotropic stress state of -10 MPa. Use 200 uniform time steps to properly capture the onset of plastic yield during the loading and unloading cycles. Ensure that a single continuous event manages this task appropriately up to the maximum time. Finally, export the output stress and strain series to a plain text file named `ViscoExtendedDruckerPragerResults.txt`.

**Organization**
Please structure this into two files: a reusable base configuration holding the mesh setup, the event timeline, the material library catalog, and the loading table definitions; and a main benchmark case that pulls in the base configuration and executes just the Visco Extended Drucker-Prager triaxial task setup.

XML files to create: triaxialDriver_ViscoExtendedDruckerPrager.xml, triaxialDriver_base.xml
--- END SIMULATION SPECIFICATION ---

--- SCOPE ---
Deliverable: the XML input deck in /workspace/inputs/. You are scored on the deck's
structure against a reference deck; nothing downstream reads simulation output.
Once the deck is complete and well-formed, it is finished.
--- END SCOPE ---
