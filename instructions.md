# NCIPlot for Chimera

Apparently, all one must do to open these volumes is opening molecule-grad.cube and set the high value to something between 0.3 or 0.5. The expected value is in the VMD script anyways, next to the Isosurface command.

The file molecule-dens.cube seems redundant and does not add any value to the visual information, but the VMD script loads it anyway for some reason.

The whole process would consist in something in the lines of:

1. Choose one of the molecules present in the canvas and export it to a temporal xyz file
2. Run nciplot to produce the *.cube outputs.
3. Open the *-grad.cube with Chimera and choose the correct isovalue, and smoothening and so on.

This requires that nciplot must be accurately compiled for the platform. Conda packages can be provided to overcome this issue.