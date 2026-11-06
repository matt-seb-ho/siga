# GEOS input deck: AdvancedExampleViscoDruckerPrager

GEOS is an open-source multiphysics simulator. This task asks you to author one or
more XML input files specified by the simulation specification below.

- The GEOS source tree (examples, documentation, XML schema) is at `/geos_lib`
  (read-only). Consult it for examples and documentation.
- Write your deck (one or more `.xml` files) under `/workspace/inputs/`.
- `xmllint` is available for checking well-formedness. There is no GEOS binary:
  do not try to build or run GEOS.

--- BEGIN SIMULATION SPECIFICATION ---
I need to set up a simulation for a triaxial compression test on a visco-plastic solid. This tests the numerical convergence and accuracy of a time-dependent constitutive approach by comparing the model response for loading and unloading periods against a semi-analytical perzyna time-dependent solution. 

Please organize the simulation inputs into a reusable base configuration file and a specific benchmark execution file.

**Base Configuration**
Even though the primary driver will evaluate material response at a single point, set up a generic 1-by-1-by-1 single-element hexahedral mesh (dimensions from 0 to 1 in X, Y, and Z) to provide a valid geometric context. Assign a dummy region and a dummy material to this baseline mesh.

Next, I need a library of constitutive laws defined in this base configuration for various verification tests. All materials share a base density of 2700 kg/m^3. Provide definitions for the following:
1. **Drucker-Prager**: Elastic bulk modulus of 10.0 GPa, shear modulus of 6.0 GPa, cohesion of 0.1 MPa, friction angle of 6.0 degrees, dilation angle of 3.0 degrees, and a hardening rate of 0.5 GPa.
2. **Visco Drucker-Prager**: Same properties as the standard Drucker-Prager, but with a relaxation time of 0.1 s.
3. **Extended Drucker-Prager**: Bulk modulus of 10.0 GPa, shear modulus of 6.0 GPa, cohesion of 0.1 MPa, an initial friction angle of 6.0 degrees, a residual friction angle of 10.0 degrees, a dilation ratio of 0.5, and hardening of 0.0001.
4. **Visco Extended Drucker-Prager**: Same as the Extended Drucker-Prager, but including a 0.1 s relaxation time.
5. **Modified Cam-Clay**: Reference pressure of -0.1 MPa, reference volumetric strain of 0.0, shear modulus of 50 MPa (5e7), pre-consolidation pressure of -0.15 MPa, CSL slope of 1.2, recompression index of 0.002, and virgin compression index of 0.003.
6. **Visco Modified Cam-Clay**: Same parameters as the standard Modified Cam-Clay, but with a relaxation time of 0.1 s.

For the loading definitions, declare three tabular functions for time-dependent operations:
- A "zero strain" function that explicitly holds a value of 0.0 from time 0.0 to 1e9 s.
- An "axial strain function" that reads coordinates from `tables/time.geos` and values from `tables/axialStrain.geos`.
- A "radial stress function" that reads coordinates from `tables/time.geos` and values from `tables/radialStress.geos`.

Finally, schedule a single simulation event aimed at running the triaxial driver task up to a maximum time of 1.0 s.

**Benchmark Case Setup**
In a separate benchmark file, include the base configuration and define the specific execution task. 
Set up a point-based triaxial driver to test the **Visco Drucker-Prager** material from the library. The test should operate in mixed control mode to mimic a real triaxial test apparatus: use the axial strain function for the axial control, and the radial stress function to maintain a constant lateral confining stress. 

Configure the test to begin from an isotropic initial stress state of -10.0 MPa. The driver should integrate the material response over 200 steps and output the stress/strain results to a text file named `ViscoDruckerPragerResults.txt` for comparison with the Python-based analytical approximations.

XML files to create: triaxialDriver_ViscoDruckerPrager.xml, triaxialDriver_base.xml
--- END SIMULATION SPECIFICATION ---

--- SCOPE ---
Deliverable: the XML input deck in /workspace/inputs/. You are scored on the deck's
structure against a reference deck; nothing downstream reads simulation output.
Once the deck is complete and well-formed, it is finished.
--- END SCOPE ---
