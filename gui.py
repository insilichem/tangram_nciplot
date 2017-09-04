#!/usr/bin/env python
# encoding: utf-8

# Get used to importing this in your Py27 projects!
from __future__ import print_function, division
# Python stdlib
import Tkinter as tk
import tkFileDialog
from itertools import groupby
from operator import attrgetter
# Chimera stuff
import chimera
from chimera.baseDialog import ModelessDialog, ModalDialog
from chimera.widgets import ModelScrolledListBox
from Pmw import OptionMenu
from SurfaceColor import surface_value_at_window_position
from OpenSave import OpenModal
# Additional 3rd parties
import matplotlib
matplotlib.use('TkAgg')
matplotlib.rc('font', **{'family': 'sans-serif', 'sans-serif': ['Helvetica']})
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
# Own
from core import Controller, standard_color_palettes
import prefs

"""
The gui.py module contains the interface code, and only that. 
It should only 'draw' the window, and should NOT contain any
business logic like parsing files or applying modifications
to the opened molecules. That belongs to core.py.
"""

# This is a Chimera thing. Do it, and deal with it.
ui = None


def showUI(callback=None):
    """
    Requested by Chimera way-of-doing-things
    """
    global ui
    if not ui:  # Edit this to reflect the name of the class!
        ui = NCIPlotDialog()
    ui.enter()
    if callback:
        ui.addCallback(callback)


class NCIPlotDialog(ModelessDialog):

    """
    To display a new dialog on the interface, you will normally inherit from
    ModelessDialog class of chimera.baseDialog module. Being modeless means
    you can have this dialog open while using other parts of the interface.
    If you don't want this behaviour and instead you want your extension to 
    claim exclusive usage, use ModalDialog.
    """

    buttons = ('OK', 'Close')
    default = None
    help = 'https://www.insilichem.com'
    configure_dialog = None

    def __init__(self, *args, **kwarg):
        # GUI init
        self.title = 'Plume NCIPlot'
        self._mouse_report_binding = None
        # Fire up
        ModelessDialog.__init__(self, resizable=False)
        chimera.extension.manager.registerInstance(self)

    def fillInUI(self, parent):
        """
        This is the main part of the interface. With this method you code
        the whole dialog, buttons, textareas and everything.
        """
        # Main frame is always called 'canvas'
        parent.configure(width=50)
        parent.pack(expand=True, fill='y')
        self.canvas = tk.Frame(parent)
        self.canvas.pack(expand=True, fill='y', padx=10, pady=10)

        # Select an input menu: Radio buttons
        self.input_frame = tk.LabelFrame(self.canvas, text='Input mode', padx=5, pady=5)
        self.input_frame.pack(expand=True, fill='x')
        self.input_choice_frame = tk.Frame(self.input_frame)
        self.input_choice_frame.grid(row=0)
        self.input_choice = tk.StringVar()
        self.input_choice.set('molecules')
        self.input_choice_molecules = tk.Radiobutton(self.input_choice_frame, variable=self.input_choice,
                                                     text='Molecules', value='molecules',
                                                     command=self._input_choice_cb)
        self.input_choice_selection = tk.Radiobutton(self.input_choice_frame, variable=self.input_choice,
                                                     text='Selection', value='selection',
                                                     command=self._input_choice_cb)
        self.input_choice_molecules.pack(side='left')
        self.input_choice_selection.pack(side='left')
        self.input_choice_molecules.select()

        # Mode A: Opened molecules
        self.input_molecules_frame = tk.Frame(self.input_frame)
        self.input_molecules_frame.grid(row=1)
        self.input_molecules = ModelScrolledListBox(self.input_molecules_frame,
                                                    selectioncommand=self._on_selection_changed,
                                                    filtFunc=lambda m: isinstance(
                                                        m, chimera.Molecule),
                                                    listbox_selectmode="extended")
        self.input_molecules.pack(expand=True, fill='x', padx=5)

        # Mode B: Current selection
        items = ['Current selection'] + sorted(chimera.selection.savedSels.keys())
        self.input_named_selections = OptionMenu(self.input_molecules_frame, command=None, items=items)
        self.input_new_named_atom_selection = None  # Text field + 'Create button'

        # More options
        self.input_intermolecular_frame = tk.Frame(self.input_frame)
        self.input_intermolecular_frame.grid(row=2)
        self.input_intermolecular_enabled = tk.IntVar()
        self.input_intermolecular_check = tk.Checkbutton(
            self.input_intermolecular_frame, text='Filter out % of intramolecular',
            variable=self.input_intermolecular_enabled,
            command=self._intermolecular_cb, state='disabled')
        self.input_intermolecular_check.pack(side='left')
        self.input_intermolecular = tk.IntVar()
        self.input_intermolecular.set(95)
        self.input_intermolecular_field = tk.Entry(self.input_intermolecular_frame,
                                                   textvariable=self.input_intermolecular,
                                                   state='disabled', width=3)
        self.input_intermolecular_field.pack(side='left')

        # Review input data
        self.input_summary = tk.StringVar()
        self.input_summary.set('Please select your input.')
        self.input_summary_label = tk.Label(self.input_frame, textvariable=self.input_summary)
        self.input_summary_label.grid(row=3)


        # NCIPlot launcher
        self.nciplot_frame = tk.Frame(self.canvas)
        self.nciplot_frame.pack()
        tk.Button(self.nciplot_frame, text='Configure',
                  command=self._configure_dialog).pack(side='left')
        self.nciplot_run = tk.Button(self.nciplot_frame, text='Run', command=self._run_nciplot)
        self.nciplot_run.pack(side='left')

        # Configure Volume Viewer
        self.settings_frame = tk.LabelFrame(self.canvas, text='Customize display', padx=5, pady=5)
        tk.Label(self.settings_frame, text='Levels: ').grid(row=0, column=0)
        self.settings_isovalue_1, self.settings_isovalue_2 = tk.StringVar(), tk.StringVar()
        self.settings_isovalue_1.set('')
        self.settings_isovalue_2.set('')
        tk.Entry(self.settings_frame, textvariable=self.settings_isovalue_1,
                 width=10).grid(row=0, column=1, sticky='ew')
        tk.Entry(self.settings_frame, textvariable=self.settings_isovalue_2,
                 width=10).grid(row=0, column=2, sticky='ew')
        tk.Button(self.settings_frame, text='Update',
                  command=self._update_surface).grid(row=0, column=3, rowspan=2, sticky='news')

        self.settings_color_palette = OptionMenu(self.settings_frame, initialitem=3,
                                                 label_text='Colors: ', labelpos='w',
                                                 items=sorted(standard_color_palettes.keys()))
        self.settings_color_palette.grid(row=1, column=0, columnspan=3, sticky='we')

        self.settings_report = tk.IntVar()
        tk.Checkbutton(self.settings_frame, text=u'Report \u03BB\u2082\u22C5\u03C1\u22C5100 value at cursor',
                       command=self._report_values_cb,
                       variable=self.settings_report).grid(row=2, column=0, columnspan=3)
        self.reported_value = tk.StringVar()
        tk.Entry(self.settings_frame, textvariable=self.reported_value,
                 state='readonly', width=8).grid(row=2, column=3, sticky='we')

        # Plot figure
        self.plot_frame = tk.LabelFrame(self.canvas, text=u'Plot RDG vs density (\u03BB\u2082\u22C5\u03C1)',
                                        padx=5, pady=5)
        self.plot_button = tk.Button(self.plot_frame, text='Plot', command=self._plot)
        self.plot_button.grid(row=0)
        self.plot_figure = Figure(figsize=(5, 5), dpi=100, facecolor='#D9D9D9')
        self.plot_subplot = self.plot_figure.add_subplot(111)

        self.plot_widget_frame = tk.Frame(self.plot_frame)
        self.plot_widget_frame.grid(row=1)
        self.plot_widget = FigureCanvasTkAgg(self.plot_figure, master=self.plot_widget_frame)
        # self.plot_cursor = Cursor(self.plot_subplot, useblit=True, color='black', linewidth=1)
        # self.plot_figure.canvas.mpl_connect('button_press_event', self._on_plot_click)

        # Register and map triggers, callbacks...
        chimera.triggers.addHandler('selection changed', self._on_selection_changed, None)

    def Apply(self):
        """
        Default! Triggered action if you click on an Apply button
        """
        pass

    def OK(self):
        """
        Default! Triggered action if you click on an OK button
        """
        self.Apply()
        self.Close()

    def Close(self):
        """
        Default! Triggered action if you click on the Close button
        """
        global ui
        ui = None
        ModelessDialog.Close(self)
        # self.destroy()

    # Below this line, implement all your custom methods for the GUI.
    def load_controller(self):
        binary, dat = prefs.get_preferences()
        return Controller(gui=self, nciplot_binary=binary, nciplot_dat=dat)

    def input_options(self):
        d = {}
        if self.input_intermolecular_enabled.get():
            d['intermolecular'] = self.input_intermolecular.get() / 100.0
        return d

    # All the callbacks
    def _input_choice_cb(self):
        """
        Change input mode
        """
        if self.input_choice.get() == 'molecules':
            self.input_molecules.pack(expand=True, fill='x', padx=5)
            self.input_named_selections.pack_forget()
        elif self.input_choice.get() == 'selection':
            self.input_molecules.pack_forget()
            self.input_named_selections.pack(expand=True, fill='x', padx=5)
        self._on_selection_changed()

    def _intermolecular_cb(self):
        if self.input_intermolecular_enabled.get():
            self.input_intermolecular_field.config(state='normal')
        else:
            self.input_intermolecular_field.config(state='disabled')

    def _validate_input_data(self, *args):
        atoms = self._on_selection_changed()
        return atoms

    def _configure_dialog(self, *args):
        if self.configure_dialog is None:
            self.configure_dialog = NCIPlotConfigureDialog(self)
        self.configure_dialog.enter()


    def _run_nciplot(self, *args):
        """
        Called at clicking 'Run' button.
        """
        self._run_nciplot_clear_cb()
        atoms = self._validate_input_data()
        if atoms:
            attr_getter = attrgetter('molecule')
            groups = [list(group) for k, group in groupby(atoms, key=attr_getter)]
            options = self.input_options()
            self.controller = self.load_controller()
            self.controller.run(groups=groups, **options)
            self.nciplot_run.configure(state='disabled', text='Running...')
            self.settings_frame.pack_forget()

    def _run_nciplot_cb(self):
        """
        Called after NCIPlot has successfully run
        """
        self.nciplot_run.configure(state='normal', text='Run')
        self.settings_isovalue_1.set(self.controller.surface.surface_levels[0])
        self.settings_isovalue_2.set(self.controller.surface.surface_levels[1])
        self.settings_frame.pack()
        self.plot_frame.pack(expand=True, fill='both')

    def _run_nciplot_clear_cb(self):
        """
        Housecleaning method. Resets everything to original state
        """
        self.nciplot_run.configure(state='normal', text='Run')
        self.plot_button.configure(state='normal')
        self.settings_frame.pack_forget()
        self.settings_isovalue_1.set('')
        self.settings_isovalue_2.set('')
        self.plot_frame.pack_forget()
        self.plot_widget.get_tk_widget().pack_forget()
        self.controller = None

    def _update_surface(self):
        """
        Gets GUI options, sets them and updates the surface
        """
        # Levels
        isovalue_1 = float(self.settings_isovalue_1.get())
        isovalue_2 = float(self.settings_isovalue_2.get())
        self.controller.isosurface(level_1=isovalue_1, level_2=isovalue_2)
        # Update view
        self.controller.update_surface()
        # Colors
        palette = self.settings_color_palette.getvalue()
        self.controller.colorize_by_volume(palette=palette)
        # Update view
        self.controller.update_surface()

    def _plot(self):
        """
        Draw density vs rdg with a hexbin
        """
        self.controller.plot(self.plot_subplot)
        self.plot_widget.get_tk_widget().pack(expand=True, fill='both')
        self.plot_widget.show()
        self.plot_button.configure(state='disabled')

    def _report_values_cb(self):
        """
        Binds mouse mouse callbacks to mouse movement events
        """
        if self.settings_report.get() and self._mouse_report_binding is None:
            self._mouse_report_binding = chimera.tkgui.app.graphics.bind('<Any-Motion>',
                                                                         self._report_values_event, add=True)

    def _report_values_event(self, event):
        """
        Report value of isosurface at cursor point
        """
        if self.settings_report.get() and self.isVisible():
            vpn = surface_value_at_window_position(event.x, event.y)
            if vpn is None:
                self.reported_value.set('')
            else:
                value, position, name = vpn
                self.reported_value.set('{:8.5g}'.format(float(value)))
                chimera.replyobj.status('{} at cursor: {:8.5g}'.format(name, float(value)))

    def _on_plot_click(self, event):
        """
        Callback that sets isosurface values from plot X axis data.
        Left click sets isovalue 1, right click sets isovalue 2
        """
        if event.button == 1:
            self.settings_isovalue_1.set(round(event.xdata, 2))
        elif event.button == 3:
            self.settings_isovalue_2.set(round(event.xdata, 2))

    def _on_selection_changed(self, *args):
        """
        Test if current selection is valid for running a new calculation,
        reports number of atoms
        """
        atoms = []
        if self.input_choice.get() == 'selection':
            atoms = chimera.selection.currentAtoms()
            molecules = chimera.selection.currentMolecules()
        elif self.input_choice.get() == 'molecules':
            molecules = self.input_molecules.getvalue()
            atoms = [a for m in molecules for a in m.atoms]

        color, state = ('black', 'normal') if atoms else ('red', 'disabled')
        self.nciplot_run.configure(state=state)
        self.input_summary_label.configure(foreground=color)
        self.input_summary.set('{} selected atoms'.format(len(atoms)))


        if len(molecules) > 1:
            self.input_intermolecular_check.config(state='normal')
            self.input_intermolecular_check.select()
        else:
            self.input_intermolecular_check.config(state='disabled')
            self.input_intermolecular_check.deselect()
        self._intermolecular_cb()
        
        return atoms


class NCIPlotConfigureDialog(ModelessDialog):

    buttons = ('OK', 'Close')
    help = 'https://www.insilichem.com'

    def __init__(self, parent=None):
        self.parent = parent
        self.title = 'Configure NCIPlot paths'
        self.binary, self.dat_dir = tk.StringVar(), tk.StringVar()
        binary, dat = prefs.get_preferences()
        if binary is None:
            binary = ''
        if dat is None:
            dat = ''
        self.binary.set(binary)
        self.dat_dir.set(dat)
        ModelessDialog.__init__(self, resizable=False)

    def fillInUI(self, parent):
        self.canvas = parent
        label_0 = tk.Label(parent, text='NCIPlot program')
        label_1 = tk.Label(parent, text='NCIPlot dat path')

        self.bin_entry = tk.Entry(parent, textvariable=self.binary)
        self.bin_browse = tk.Button(parent, text='...',
            command=lambda: self._browse_cb(self.binary, mode='filename', title='Select NCIPlot binary'))

        self.dat_entry = tk.Entry(parent, textvariable=self.dat_dir)
        self.dat_browse = tk.Button(parent, text='...',
            command=lambda: self._browse_cb(self.dat_dir, mode='directory', title='Select NCIPlot dat directory'))

        self.text = tk.StringVar()
        self.text.set("Tip: Click <Help> to get NCIPlot")
        self.label = tk.Label(parent, textvariable=self.text)
        self.label.grid(row=2, columnspan=3)

        grid = [[label_0, self.bin_entry, self.bin_browse],
                [label_1, self.dat_entry, self.dat_browse]]
        for i, row in enumerate(grid):
            for j, widget in enumerate(row):
                widget.grid(row=i, column=j, padx=2, pady=2)


    def OK(self):
        self.Apply()
        self.Close()

    def Apply(self):
        try:
            prefs.set_preferences(self.binary.get(), self.dat_dir.get())
        except ValueError as e:
            self.text.set(str(e))
            self.label.configure(foreground='red')
            raise ValueError(e)

    def Close(self):
        self.parent.configure_dialog = None
        ModelessDialog.Close(self)
        self.destroy()

    def _browse_cb(self, var=None, mode='filename', **options):
        # result = OpenModal(**options).run(chimera.tkgui.app)
        
        functions = {'filename': tkFileDialog.askopenfilename,
                     'directory': tkFileDialog.askdirectory}
        result = functions[mode](parent=self.canvas, **options)
        if result and var:
            var.set(result)
        return result