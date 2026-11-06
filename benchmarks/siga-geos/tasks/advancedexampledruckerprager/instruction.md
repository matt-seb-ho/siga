# GEOS input deck: AdvancedExampleDruckerPrager

GEOS is an open-source multiphysics simulator. This task asks you to author one or
more XML input files specified by the simulation specification below.

- The GEOS source tree (examples, documentation, XML schema) is at `/geos_lib`
  (read-only). Consult it for examples and documentation.
- Write your deck (one or more `.xml` files) under `/workspace/inputs/`.
- `xmllint` is available for checking well-formedness. There is no GEOS binary:
  do not try to build or run GEOS.

--- BEGIN SIMULATION SPECIFICATION ---
I need to set up a simulation of an elasto-plastic triaxial compression test to verify the accuracy and convergence of our constitutive models against semi-analytical solutions. The physical scenario involves imposing constant lateral confining stress while applying loading and unloading axial strain cycles that are large enough to drive the material into plastic yield. 

To keep our test setups organized, please structure the simulation into two parts: a reusable base configuration that houses our test geometry, a library of material models, and loading functions; and a specific benchmark file that runs the triaxial driver for the standard Drucker-Prager material.

For the physical domain in the base configuration, create a simple 1 cubic meter single-element regular hexahedral mesh (extending from 0 to 1 in the x, y, and z directions). Assign a dummy material to this region so that the mesh is properly initialized. 

We need to pre-define the following material models in the base configuration's constitutive library, all using SI units:
1. **Drucker-Prager**: Density of 2700 kg/m³, bulk modulus of 10.0 GPa, shear modulus of 6.0 GPa, cohesion of 0.1 MPa, friction angle of 6.0 degrees, dilation angle of 3.0 degrees, and a hardening rate of 0.5 GPa.
2. **Visco-Drucker-Prager**: Identical properties to the standard Drucker-Prager above, but with a viscoplastic relaxation time of 0.1 s.
3. **Extended Drucker-Prager**: Density of 2700 kg/m³, bulk modulus of 10.0 GPa, shear modulus of 6.0 GPa, cohesion of 0.1 MPa, initial friction angle of 6.0 degrees, residual friction angle of 10.0 degrees, dilation ratio of 0.5, and a hardening parameter of 0.0001.
4. **Visco-Extended Drucker-Prager**: Identical to the Extended Drucker-Prager, adding a relaxation time of 0.1 s.
5. **Modified Cam-Clay**: Density of 2700 kg/m³, reference pressure of -0.1 MPa, zero reference volumetric strain, shear modulus of 50 MPa, pre-consolidation pressure of -0.15 MPa, critical state line slope of 1.2, recompression index of 0.002, and virgin compression index of 0.003.
6. **Visco-Modified Cam-Clay**: Identical to the Modified Cam-Clay model, adding a relaxation time of 0.1 s.

For the loading functions in the base configuration, define a baseline zero-strain table function that constantly returns 0.0 over time coordinates evaluated between 0.0 and 1.0e9 seconds. We also need to read the dynamic structural loading histories from external table files. Set up an axial strain function that determines values from a `tables/axialStrain.geos` file, and a radial stress function that determines values from a `tables/radialStress.geos` file. Both of these functions should be mapped against the time coordinates provided in `tables/time.geos`. 

In the specific benchmark case, include all the definitions from the base configuration. The simulation should execute a triaxial driver configured to test the standard Drucker-Prager material. Set the test to operate in mixed control mode: the axial control will be driven by the previously defined axial strain function, and the radial control will be driven by the radial stress function. Apply a uniform initial compressional stress of -10.0 MPa to the material. 

The simulation should be carried out over a total physical time of 1 second, split exactly into 200 evenly spaced solver steps. Throughout the loading and unloading cycles, please record the resulting stress and strain responses to an output text file named `DruckerPragerResults.txt` so that we can compare the numerical results against our Python-based semi-analytical solutions.

XML files to create: triaxialDriver_DruckerPrager.xml, triaxialDriver_base.xml
--- END SIMULATION SPECIFICATION ---

--- SCOPE ---
Deliverable: the XML input deck in /workspace/inputs/. You are scored on the deck's
structure against a reference deck; nothing downstream reads simulation output.
Once the deck is complete and well-formed, it is finished.
--- END SCOPE ---
