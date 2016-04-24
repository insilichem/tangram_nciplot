#!/usr/bin/env python
# encoding: utf-8

# Get used to importing this in your Py27 projects!
from __future__ import print_function, division
# Python stdlib
from cStringIO import StringIO
import os
# Chimera stuff
import chimera, _chimera
from chimera.SubprocessMonitor import Popen, PIPE, monitor
from chimera.tasks import Task
from OpenSave import osTemporaryFile
from chimera import UserError
from VolumeViewer import open_volume_file
from SurfaceColor import Volume_Color, Gradient_Color, standard_color_palettes, color_by_volume
# Additional 3rd parties
import numpy as np
from matplotlib import pyplot as plt
# Own


"""
This module contains the business logic of your extension. Normally, it should
contain the Controller and the Model. Read on MVC design if you don't know about it.
"""


class Controller(object):

    """
    The controller manages the communication between the UI (graphic interface)
    and the data model. Actions such as clicks on buttons, enabling certain areas, 
    or running external programs, are the responsibility of the controller.
    """

    def __init__(self, gui=None, nciplot_binary=None, nciplot_dat=None, *args, **kwargs):
        self.gui = gui
        self.nciplot = NCIPlot(nciplot_binary, nciplot_dat, success_callback=self._after_cb,
            clear_callback=self.gui._run_nciplot_clear_cb)
        self.data = {}
        self.surface, self.density = None, None

    def run(self, atoms=None):
        """
        Convert selected molecules to temporary xyz files, launch NCIPlot
        and draw the resulting volumetric information
        """
        if atoms:
            xyz = [atoms2xyz(atoms)]
        else:
            xyz = [molecule2xyz(m) for m in self.selected_molecules]
        self.nciplot.run(*xyz, **self.nci_options)

    def _after_cb(self, data):
        """
        Called once NCIPlot has run
        """
        self.data = data
        self.surface, self.density = self.draw()
        self.isosurface()
        self.update_surface()
        self.colorize_by_volume()
        self.gui._run_nciplot_cb()

    def draw(self):
        """
        Research on Chimera's Volume extensions
        """
        try:
            grad_file, dens_file = self.data['grad_cube'], self.data['dens_cube']
        except KeyError:
            raise UserError('NCIPlot has not been run yet!')
        else:
            gradient = open_volume_file(grad_file, show_dialog=False)[0]
            density = open_volume_file(dens_file, show_dialog=False)[0]
            density.display = False
        return gradient, density

    def colorize_by_color(self, color, surface=None):
        """
        Apply a flat color, with no leves, to a given surface
        
        Parameters
        ----------
        color : _chimera.MaterialColor or str
            A Chimera color object, or a string representing one of the colors
            in the chimera.colorTable default palette.
        surface : Volume.Viewer, optional
            If not given, will use self.surface.
        """

        # Flat color
        if surface is None:
            surface = self.surface

        if isinstance(color, _chimera.MaterialColor):
            rgba = color.rgba() 
        elif color in chimera.colorTable.colors:
            rgba = chimera.colorTable.getColorByName(color)
        else:
            raise TypeError('Color not recognized.')     
        surface.surface_colors = surface.surface_colors[0], rgba
        surface.show()

    def colorize_by_volume(self, surface=None, volume=None, mask=None, palette='rainbow'):
        """
        Apply color to a surface taking the rgb values from an opened volume.

        Parameters
        ----------
        surface : VolumeViewer.volume
            Volumetric isosurface to be colorized
        volume : VolumeViewer.volume
            Volume containing the data that will be used to paint `surface`
        mask : 'volume' or 'gradient'
            Interpretation of `volume` data. It can be either the raw volume data,
            or the data extracted from the gradient norms.
        palette : str, default='rainbow'
            Colors that will be used to paint `surface`. Check 
            `SurfaceColor.standard_color_palettes.keys()` for available palettes.
        """
        if surface is None:
            surface = self.surface
        if volume is None:
            volume = self.density

        if mask == 'volume' or not mask:
            mask = Volume_Color()
            mask.set_volume(volume)
        elif mask == 'gradient':
            mask = Gradient_Color()
            mask.set_volume(volume)

        values_range = mask.value_range(surface.surfacePieces[0])
        if None in values_range:
            print('Warning: Selected molecule has no value range. Coloring will be omitted.')
        else:
            palette = standard_color_palettes.get(palette, standard_color_palettes['rainbow'])
            values = interpolate_range_into_n_values(values_range, len(palette))
            color_by_volume(surface, volume, list(values), palette)

    def isosurface(self, surface=None, level_1=0.08, level_2=0.25):
        """
        Change the cutoffs that define the isosurface extracted from the opened
        volume.

        Parameters
        ----------
        surface : VolumeViewer.volume
            The volume whose isosurface will be edited
        level_1, level_2 : float
            Cutoffs. Defaults are 0.08 and 0.25, respectively.
        """
        if surface is None:
            surface = self.surface
        surface.surface_levels = level_1, level_2

    def plot(self):
        """
        Read on Matplotlib TK dialogs
        """
        try:
            xy = np.loadtxt(self.data['xy_data'])
        except IOError:
            raise UserError('DAT file is missing. Please, run NCIPlot again.')
        except KeyError:
            raise UserError('NCIPlot has not been run yet!')
        else:
            xy_plot = plt.scatter(xy[:, 0], xy[:, 1])
            xy_plot.show()

    def update_surface(self):
        """
        Refresh self.surface view
        """
        if self.surface is not None:
            self.surface.show()

    @property
    def nci_options(self):
        """
        Get GUI options in a dictionary
        """
        options = {}
        options['names'] = [m.name for m in self.selected_molecules]
        # if self.gui.radius_search:
        #     options['radius'] = origin, radius = None
        # More to come...
        return options

    @property
    def selected_molecules(self):
        """
        Retrieve selected molecules in GUI
        """
        # Replaceable by tk selection widget
        molecules = chimera.selection.currentMolecules()
        if molecules:
            return molecules
        molecules = chimera.openModels.list(modelTypes=[chimera.Molecule])
        if len(molecules) == 1:
            return molecules
        raise UserError('If more than one molecule is open, you must '
                        'select one of them by selecting any part of it.')


class NCIPlot(object):

    """
    A wrapper around NCIPlot binary interface
    """

    def __init__(self, binary, dat_directory, success_callback=None, clear_callback=None):
        self._check_paths(binary, dat_directory)
        self.binary = binary
        self.dat_directory = dat_directory
        os.environ['NCIPLOT_HOME'] = os.path.dirname(self.dat_directory)
        self.success_callback = success_callback
        self.clear_callback = clear_callback
        self.task = None
        self.subprocess = None
        self.stdout = None
        self.queue = None

    def run(self, *xyz, **options):
        """
        Launch a NCIPlot essay for specified xyz files and options.
        Read on self.create_nci_method documentation for further info.

        Notes
        -----
        This function uses threads, queues, tasks and subprocesses, so it 
        can be a bit difficult to understand for newcomers.

        `subprocess` is used to launch an external program (nciplot, in this
        case), and `task` is a Chimera feature to monitor that process in the
        tasks panels. It also allows to print status updates to the bottom bar.
        `task` and `subprocess` are synced with Chimera's `monitor`, which
        includes a very useful `afterCB` parameter: a callable that will be
        called when the process ends.

        If we needed to get it in realtime, we should add queues and threads.
        As a workaround, we need to get the stdout to an async queue (in
        realtime!) with a separate thread. 
        >>> from threading import Thread
        >>> from Queue import Queue
        >>> def enqueue_output(out, queue):
                for line in iter(out.readline, b''):
                    queue.put(line)
                out.close()
        >>> self.queue = Queue()
        >>> thread = Thread(target=enqueue_output, args=(self.subprocess.stdout, self.queue))
        >>> thread.daemon = True  # thread dies with the program
        >>> thread.start()

        Then, we can read the stdout from the queue:

        >>> self.queue.put(None) # Sentinel value. When iter gets this, it stops.
        >>> for line in iter(self.queue.get, None):
        >>>     # do stuff

        Check this SO answer for more info:
        
        http://stackoverflow.com/questions/375427/
        non-blocking-read-on-a-subprocess-pipe-in-python/4896288#4896288
        
        """
        nci_input = self.create_nci_input(xyz, **options)
        nci_file = osTemporaryFile(suffix='.nci')
        with open(nci_file, 'w') as f:
            f.write(nci_input.read())
        names = ', '.join(options.get('names', ['<unknown>']))

        self.task = Task("NCIPlot for {}".format(names), cancelCB=self._clear_task)
        self.subprocess = Popen([self.binary, nci_file], stdout=PIPE)
        monitor("NCIPlot", self.subprocess, task=self.task, afterCB=self._after_cb)
        self.task.updateStatus("Running NCIPlot")

    def _after_cb(self, aborted):
        """
        Called after the subprocess ends.
        """
        if aborted:
            self._clear_task()
            self.clear_callback()
            return
        if self.subprocess.returncode != 0:
            self.task.updateStatus("NCIPlot calculation failed!")
            self._clear_task()
            self.clear_callback()
            return

        self.task.updateStatus("Parsing NCIPlot output")
        data = self.parse_stdout(self.subprocess.stdout)
        self.task.updateStatus("Loading volumes")
        self.success_callback(data)
        self.task.updateStatus("Done!")
        self._clear_task()

    def _clear_task(self):
        """
        House cleaning 
        """
        self.task.finished()
        self.subprocess.stdout.close()
        self.task, self.subprocess, self.queue = None, None, None

    def parse_stdout(self, stdout):
        """
        Get useful data from NCIPlot stdout, or any file-like object.
        """
        data = {}
        for line in stdout:
            if line.startswith('#') or line.startswith('---'):
                continue
            elif line.lstrip().startswith('RHO'):
                data['rho'] = float(line.split()[-1].strip())
            elif line.lstrip().startswith('RDG'):
                data['rdg'] = float(line.split()[-1].strip())
            elif line.rstrip().endswith('-grad.cube'):
                data['grad_cube'] = line.split('=')[-1].strip()
            elif line.rstrip().endswith('-dens.cube'):
                data['dens_cube'] = line.split('=')[-1].strip()
            elif 'LS x RDG' in line:
                data['xy_data'] = line.split('=')[-1].strip()
        return data

    @staticmethod
    def create_nci_input(paths, output_level=3, ligand=None,
                         dat_cutoffs=(0.2, 1.0), cube_cutoffs=(0.07, 0.3), intermolecular=None,
                         radius=None, cube=None, increments=None, name=None, **kwargs):
        """
        Creates a file-like object with NCIPlot input options

        Parameters
        ----------
        paths : list of str
            Paths to XYZ molecule files.

        # Output options
        name : str, optional, default=None
            If set, replaces the output name, which by default is the molecule name
            without extension.
        output_level : int, optional, default=3
            How many files should NCI plot create. Level 1 is minimum output, level 3
            creates up to 4 files.
        dat_cutoffs : 2-tuple of float, optional, default=(0.2, 1.0)
            Density and RDG cutoffs used in creating the dat file
        cube_cutoffs : 2-tuple of float, optional, default=(0.07, 0.3)
            Density (r1) and RDG (r2) cutoffs used when creating the cube files. 
            r1 will set the cutoff for both the density and the RDG to be registered
            in the cube files, whereas r2 will be used for isosurfaces depiction.

        # Search options; If set, only a region will be explored. CHOOSE ONLY ONE!
        ligand : 2-tuple of float, int, optional, default=None
            If set, which molecule (by index) is working as a ligand, and the search
            radius to inspect within that molecule.
        intermolecular: float, optional, default=None
            If set, the search radius for interactions in between input molecules
        radius : 4-tuple of float, optional, default=None
            If set, first three values indicate the origin coordinates of the search
            sphere, and the fourth value indicates the search radius of such sphere.
        cube : 6-tuple of float, optional, default=None
            If set, search within the cube that is drawn between point A (first three
            floats) and point B (last three floats).
        increments : 3-tuple of float, optional, default=None
            ???

        Returns
        -------
        paths : list of str
            Collection of output files created by NCIPlot

        Notes
        -----
        NCI input files follow this scheme. More info @ 
        https://github.com/aoterodelaroza/nciplot

            <number of molecule files>
            <path to molecule file, xyz or wfn>
            <path to molecule file>...
            # Optional
            LIGAND n r #index of molecule in path list, search radius
            INTERMOLECULAR r # search radius
            RADIUS x y z r # coordinates center, radius
            CUBE x0 y0 z0 x1 y1 z1 # draw a cube from a to b
            INCREMENTS r1 r2 r3 
            CUTOFFS r1 r2 # density and RDG cutoffs for dat file; defaults: 0.2, 1.0
            CUTPLOT r1 r2 # density and RDG cutoffs for cube file; defaults: 0.07, 0.3
            ISORDG r # isosurface level; 0.3 for xyz mols, 0.5 for wfn mols
            OUTPUT [1-3] # level of output: 1 is minimal, 3 max
            ONAME str # tag name
        """

        output = StringIO()
        output.write('{}\n'.format(len(paths)))
        for path in paths:
            output.write('{}\n'.format(path))

        if output_level in (1, 2, 3):
            output.write('OUTPUT {}\n'.format(output_level))
        if name:
            output.write('ONAME {}\n'.format(name))
        if dat_cutoffs:
            output.write('CUTOFFS {} {}\n'.format(*dat_cutoffs[:2]))
        if cube_cutoffs:
            output.write('CUTPLOT {} {}\n'.format(*cube_cutoffs[:2]))

        if ligand:
            output.write('LIGAND {} {}\n'.format(*ligand[:2]))
        elif intermolecular:
            output.write('INTERMOLECULAR {}\n'.format(intermolecular))
        elif radius:
            output.write('RADIUS {} {} {} {}\n'.format(*radius[:4]))
        elif cube:
            output.write('CUBE {} {} {} {} {} {}\n'.format(*cube[:6]))
        elif increments:
            output.write('INCREMENTS {} {} {}\n'.format(*increments[:3]))

        output.seek(0)
        return output

    def _check_paths(self, binary, dat_directory):
        """
        Check if paths are OK, we need to bring up defaults, or if they
        have been never set
        """
        if not os.path.isfile(binary):
            raise UserError('Specified NCIplot binary path {} does not exist'.format(binary))
        if not os.path.isdir(dat_directory):
            raise UserError('Specified NCIplot dat library path {} does not exist'.format(dat_directory))


def molecule2xyz(molecule, path=None):
    """
    Saves the given molecule in XYZ format.

    Parameters
    ----------
    molecule : chimera.Molecule
    path : str, optional
        Desired output location. If not provided, a temporary one will be used.
    """
    if not path:
        path = osTemporaryFile(suffix='.xyz')
    with open(path, 'w') as f:
        f.write('{}\n{}\n'.format(len(molecule.atoms), molecule.name))
        for atom in molecule.atoms:
            f.write('{} {} {} {}\n'.format(atom.element.name, *atom.coord()))
    return path

def atoms2xyz(atoms, path=None):
    """
    Saves the given molecule in XYZ format.

    Parameters
    ----------
    molecule : chimera.Molecule
    path : str, optional
        Desired output location. If not provided, a temporary one will be used.
    """
    if not path:
        path = osTemporaryFile(suffix='.xyz')
    with open(path, 'w') as f:
        f.write('{}\n{}\n'.format(len(atoms), atoms[0].molecule.name))
        for atom in atoms:
            f.write('{} {} {} {}\n'.format(atom.element.name, *atom.coord()))
    return path

def enqueue_output(out, queue):
    """
    Consume a file output (normally stdout) into a queue, in realtime. This way,
    we can update the GUI in realtime without polling or unnecessary blocking
    """
    for line in iter(out.readline, b''):
        queue.put(line)
    out.close()

def save_output(out, f):
    """
    Pipe contents of a file (normally stdout) into another, in realtime
    """
    for line in iter(out.readline, b''):
        f.write(line)
    out.close() 

def iter_queue(q):
    """
    Drain a queue if we know we are not putting any additional values. If another
    thread could add anything, better use the sentinel approach:

    >>> queue.put(None)
    >>> for line in iter(queue.get, None):
    >>>     # do something with line
    """
    while True:
        try:
            yield q.get_nowait()
        except Empty:  # on python 2 use Queue.Empty
            break

def interpolate_range_into_n_values(vrange, n):
    """
    Given an interval, subdivide that interval in `n-1` chunks, so we obtain `n` values.
    """
    a, b = vrange
    yield a
    delta = (b - a) / float(n-1)
    for i in range(1, n):
        a = a + delta
        yield a

if __name__ == '__main__':
    path = '/home/jrodriguez/dev/plume/nciplot/res/nciplot/src/nciplot'
    dat = '/home/jrodriguez/dev/plume/nciplot/res/nciplot/dat'
    c = Controller(nciplot_binary=path, nciplot_dat=dat)
    c.run()
