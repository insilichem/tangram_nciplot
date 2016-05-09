# Plume NCIPlot GUI

NCIPlot GUI is a graphical frontend for UCSF Chimera. It runs NCIPlot behind the scenes to depict non covalent interaction blobs of the selected molecules. 

![NCIPlotGUI](screenshot.png)

NCIPlot is GPL software developed by Alberto Otero de la Roza,
Julia Conteras-Garcia, Erin R. Johnson, and Weitao Yang. Make sure to check their [GitHub](https://github.com/aoterodelaroza/nciplot).

# Dependencies
You need to download NCIPlot from [here](https://github.com/aoterodelaroza/nciplot) and configure Plume NCIPlot so it can find the location where you extracted the files.

We also provide [Anaconda](https://www.continuum.io/) [binaries](https://anaconda.org/InsiliChem/nciplot) so you can install it easily with this command:

```
conda install -c insilichem nciplot
```

# Installation
[Download](https://bitbucket.org/insilichem/nciplot/downloads) or clone this repository and extract it in any location. Then, open up Chimera and go to `Favorites> Preferences`. In the `Category` dropdown, select `Tools`. In the lower part of the dialog, under `Locations`, click on `Add` and select the parent location where you extracted NCIPlot GUI. Ie, the selected folder must contain NCIPlot.

If installed with Conda, this will give you the locations you need to know.

```
BINARY=`which nciplot`
DATDIR=`dirname $BINARY`/nciplot/dat
```
