# GEOS input deck: AdvancedExampleExtendedDruckerPrager

GEOS is an open-source multiphysics simulator. This task asks you to author one or
more XML input files specified by the simulation specification below.

- The GEOS source tree (examples, documentation, XML schema) is at `/geos_lib`
  (read-only). Consult it for examples and documentation.
- Write your deck (one or more `.xml` files) under `/workspace/inputs/`.
- `xmllint` is available for checking well-formedness. There is no GEOS binary:
  do not try to build or run GEOS.

--- BEGIN SIMULATION SPECIFICATION ---
I am looking to run a set of validation studies for various elasto-plastic constitutive models under triaxial compression. I want to organize the simulations into a reusable baseline setup file and a specific benchmark file for evaluating an Extended Drucker-Prager solid. 

**Base Material and Geometry Setup**
In the reusable base setup, please define a simple 1x1x1 single-element hexahedral unit mesh (1m x 1m x 1m) assigned to a placeholder "dummy" material, as we are mainly interested in the point-wise material integrations. 

Please construct a library of the following constitutive models, all using SI units (kg, m, s, Pa):
1. **Drucker-Prager**: Density = 2700 kg/m³, Bulk Modulus = 10.0 GPa, Shear Modulus = 6.0 GPa, Cohesion = 0.1 MPa, Friction Angle = 6.0 degrees, Dilation Angle = 3.0 degrees, Hardening Rate = 0.5 GPa.
2. **Visco-Drucker-Prager**: Same properties as the standard Drucker-Prager, but with a visco-plastic relaxation time of 0.1 seconds.
3. **Extended Drucker-Prager**: Density = 2700 kg/m³, Bulk Modulus = 10.0 GPa, Shear Modulus = 6.0 GPa, Cohesion = 0.1 MPa, Initial Friction Angle = 6.0 degrees, Residual Friction Angle = 10.0 degrees, Dilation Ratio = 0.5, Hardening parameter = 0.0001.
4. **Visco-Extended-Drucker-Prager**: Same as the Extended Drucker-Prager, with a relaxation time of 0.1 seconds.
5. **Modified Cam-Clay**: Density = 2700 kg/m³, Reference Pressure = -0.1 MPa, Reference Volumetric Strain = 0.0, Shear Modulus = 50.0 MPa, Pre-consolidation Pressure = -0.15 MPa, Critical State Line (CSL) Slope = 1.2, Recompression Index = 0.002, Virgin Compression Index = 0.003.
6. **Visco-Modified-Cam-Clay**: Same as the Modified Cam-Clay, with a relaxation time of 0.1 seconds.

**Functions and Loading**
For driving the triaxial test, define a constant "zero strain" function that maintains a value of 0.0 from time 0 to 1.0e9 seconds. 
Also, define two tabulated loading functions that will pull their discrete points from external files:
- An axial strain function driven by time coordinates in `tables/time.geos` and data values in `tables/axialStrain.geos`.
- A radial stress function driven by time coordinates in `tables/time.geos` and data values in `tables/radialStress.geos`.

The maximum simulated time for the event sequence in this base setup should be 1 second, pointing to the triaxial driver task defined below.

**Extended Drucker-Prager Benchmark**
For the specific validation case, include the baseline library defined above. Configure a triaxial driver numerical algorithm targeting the Extended Drucker-Prager material from our library. 

Set up the test under mixed control conditions:
- The axial control should be driven by the tabulated axial strain function.
- The radial control should be driven by the tabulated radial stress function.

Apply an initial uniform confining stress of -10.0 MPa (using a negative sign convention for compression). The simulation should march through the 1-second duration in exactly 200 solution steps. Ensure that the resulting stress-strain history is exported to a plain text file named `ExtendedDruckerPragerResults.txt` so I can compare it against my semi-analytical python models.

XML files to create: triaxialDriver_ExtendedDruckerPrager.xml, triaxialDriver_base.xml
--- END SIMULATION SPECIFICATION ---

--- SCOPE ---
Deliverable: the XML input deck in /workspace/inputs/. You are scored on the deck's
structure against a reference deck; nothing downstream reads simulation output.
Once the deck is complete and well-formed, it is finished.
--- END SCOPE ---
