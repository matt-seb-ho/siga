# GEOS input deck: AdvancedExampleModifiedCamClay

GEOS is an open-source multiphysics simulator. This task asks you to author one or
more XML input files specified by the simulation specification below.

- The GEOS source tree (examples, documentation, XML schema) is at `/geos_lib`
  (read-only). Consult it for examples and documentation.
- Write your deck (one or more `.xml` files) under `/workspace/inputs/`.
- `xmllint` is available for checking well-formedness. There is no GEOS binary:
  do not try to build or run GEOS.

--- BEGIN SIMULATION SPECIFICATION ---
I need to simulate an elasto-plastic oedometric compression test on a geotechnical material using a single-element triaxial driver approach. To make the setup reusable, I would like to conceptually split the simulation into a base configuration that holds a library of material models, loading functions, and the single-element mesh; and a separate test case that executes the specific Modified Cam-Clay test.

**Base Configuration**
First, construct a fundamental test domain consisting of a single 1x1x1 hexahedral element spanning coordinates 0 to 1 in X, Y, and Z. The element region should apply to all cell blocks with a generic or dummy material parameter to instantiate the mesh.

For the driver controls, define three lookup functions for the loading protocol:
1. A zero-strain table function that maps a time domain from 0.0 to 1e9 seconds to a constant value of 0.0. Let's name this "zeroStrain".
2. An axial strain tabular function that reads external coordinates from `tables/time.geos` and values from a voxel file at `tables/axialStrain.geos`.
3. A radial stress tabular function that also reads time coordinates from `tables/time.geos` and values from `tables/radialStress.geos`.

The maximum simulation time will be 1.0 second, driven by a single continuous event targeting the triaxial driver task.

Next, populate a library of constitutive laws within this base setup using standard SI units for everything:
- **Modified Cam-Clay**: density of 2700 kg/m³, reference pressure of -1e5 Pa, reference volumetric strain of 0.0, shear modulus of 50 MPa (5e7), pre-consolidation pressure of -1.5e5 Pa, Critical State Line slope of 1.2, recompression index of 0.002, and virgin compression index of 0.003.
- **Visco-Modified Cam-Clay**: Identical to the standard Cam-Clay above, but with an added relaxation time of 0.1 seconds.
- **Drucker-Prager**: density of 2700 kg/m³, bulk modulus of 10 GPa (10e9), shear modulus of 6 GPa (6e9), cohesion of 0.1 MPa (0.1e6), friction angle of 6.0 degrees, dilation angle of 3.0 degrees, and a hardening rate of 0.5 GPa (0.5e9).
- **Visco-Drucker-Prager**: Same properties as the standard Drucker-Prager, but including a relaxation time of 0.1 seconds.
- **Extended Drucker-Prager**: density of 2700 kg/m³, bulk modulus of 10 GPa, shear modulus of 6 GPa, cohesion 0.1 MPa, initial friction angle of 6.0 degrees, residual friction angle of 10.0 degrees, dilation ratio of 0.5, and a constant hardening parameter of 0.0001.
- **Visco-Extended Drucker-Prager**: Same properties as the Extended Drucker-Prager above, with a relaxation time of 0.1 seconds.

**Modified Cam-Clay Test Run**
In the specific benchmark case, include all the properties from the base configuration and set up the triaxial driver to run the test using the Modified Cam-Clay material. 

Configure the test to operate in strain-control mode. The axial control must follow the external axial strain function we defined, capturing the desired loading/unloading cycles. The radial control must enforce the zero-strain function, mimicking a true oedometric compression condition with zero lateral expansion. 

Apply an initial stress of -1e5 Pa at the start of the test. The simulation driver should break the load history down into exactly 200 calculation steps. Output the resulting stress and strain variations directly to a text file named `ModifiedCamClayResults.txt` so that it can be post-processed and compared against semi-analytical solutions.

XML files to create: triaxialDriver_ModifiedCamClay.xml, triaxialDriver_base.xml
--- END SIMULATION SPECIFICATION ---

--- SCOPE ---
Deliverable: the XML input deck in /workspace/inputs/. You are scored on the deck's
structure against a reference deck; nothing downstream reads simulation output.
Once the deck is complete and well-formed, it is finished.
--- END SCOPE ---
