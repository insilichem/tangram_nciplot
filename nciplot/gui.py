#!/usr/bin/env python
# encoding: utf-8


from __future__ import print_function, division
# Python stdlib
import Tkinter as tk
import tkFileDialog
from itertools import groupby
from operator import attrgetter
import os
import json
import shutil
# Chimera stuff
import chimera
from chimera.baseDialog import ModelessDialog, ModalDialog
from chimera.widgets import MoleculeScrolledListBox
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
from libplume.ui import PlumeBaseDialog
from core import Controller, standard_color_palettes
import prefs


ui = None
def showUI():
    global ui
    if not ui:
        ui = NCIPlotDialog()
    ui.enter()


class NCIPlotDialog(PlumeBaseDialog):


    buttons = ('Run', 'Save', 'Load', 'Close')
    configure_dialog = None

    def __init__(self, *args, **kwargs):
        # GUI init
        self.title = 'Plume NCIPlot'
        self._mouse_report_binding = None

        # Variables
        self.var_input_intermolecular_enabled = tk.IntVar()
        self.var_input_intermolecular = tk.IntVar()
        self.var_input_intermolecular.set(95)
        self.var_input_summary = tk.StringVar()
        self.var_input_summary.set('Please select your input.')
        self.var_input_choice = tk.StringVar()
        self.var_input_choice.set('molecules')
        self.var_settings_isovalue_1 = tk.StringVar()
        self.var_settings_isovalue_1.set('')
        self.var_settings_isovalue_2 = tk.StringVar()
        self.var_settings_isovalue_2.set('')
        self.var_settings_report = tk.IntVar()
        self.var_reported_value = tk.StringVar()

        # Fire up
        super(NCIPlotDialog, self).__init__(*args, **kwargs)


    def fill_in_ui(self, parent):
        # Select an input menu: Radio buttons
        self.ui_input_frame = tk.LabelFrame(self.canvas, text='Input mode')
        self.ui_input_frame.pack(expand=True, fill='x', padx=5, pady=5)
        self.ui_input_frame.columnconfigure(0, weight=1)
        self.ui_input_choice_frame = tk.Frame(self.ui_input_frame)
        self.ui_input_choice_frame.grid(row=0, sticky='we')
        self.ui_input_choice_molecules = tk.Radiobutton(self.ui_input_choice_frame,
                variable=self.var_input_choice, text='Molecules', value='molecules',
                command=self._input_choice_cb)
        self.ui_input_choice_selection = tk.Radiobutton(self.ui_input_choice_frame,
                variable=self.var_input_choice, text='Selection', value='selection',
                command=self._input_choice_cb)
        self.ui_input_choice_molecules.pack(side='left')
        self.ui_input_choice_selection.pack(side='left')
        self.ui_input_choice_molecules.select()

        # Mode A: Opened molecules
        self.ui_input_molecules_frame = tk.Frame(self.ui_input_frame)
        self.ui_input_molecules_frame.grid(row=1, sticky='news')
        self.ui_input_molecules_frame.columnconfigure(0, weight=1)
        self.ui_input_molecules = MoleculeScrolledListBox(self.ui_input_molecules_frame,
                selectioncommand=self._on_selection_changed,
                listbox_selectmode="extended")
        self.ui_input_molecules.pack(expand=True, fill='x', padx=5)

        # Mode B: Current selection
        items = ['Current selection'] + sorted(chimera.selection.savedSels.keys())
        self.ui_input_named_selections = OptionMenu(self.ui_input_molecules_frame,
                command=None, items=items)
        self.input_new_named_atom_selection = None  # Text field + 'Create button'

        # More options
        self.ui_input_intermolecular_frame = tk.Frame(self.ui_input_frame)
        self.ui_input_intermolecular_frame.grid(row=2)
        self.ui_input_intermolecular_check = tk.Checkbutton(
                self.ui_input_intermolecular_frame, text='Filter out % of intramolecular',
                variable=self.var_input_intermolecular_enabled,
                command=self._intermolecular_cb, state='disabled')
        self.ui_input_intermolecular_check.pack(side='left')
        self.ui_input_intermolecular_field = tk.Entry(self.ui_input_intermolecular_frame,
                textvariable=self.var_input_intermolecular, state='disabled', width=3)
        self.ui_input_intermolecular_field.pack(side='left')

        # Review input data
        self.ui_input_summary_label = tk.Label(self.ui_input_frame,
                textvariable=self.var_input_summary)
        self.ui_input_summary_label.grid(row=3)


        # NCIPlot launcher
        self.ui_nciplot_frame = tk.Frame(self.canvas)
        self.ui_nciplot_frame.pack()
        self.ui_config_btn = tk.Button(self.ui_nciplot_frame, text='Configure',
                command=self._configure_dialog)
        self.ui_config_btn.pack(side='left')

        # Configure Volume Viewer
        self.ui_settings_frame = tk.LabelFrame(self.canvas,
                text='Customize display', padx=5, pady=5)
        self.ui_levels_lbl = tk.Label(self.ui_settings_frame,
                text='Levels: ')
        self.ui_levels_lbl.grid(row=0, column=0)
        self.ui_settings_isovalue_1 = tk.Entry(self.ui_settings_frame,
                textvariable=self.var_settings_isovalue_1,
                width=10)
        self.ui_settings_isovalue_1.grid(row=0, column=1, sticky='ew')
        self.ui_settings_isovalue_2 = tk.Entry(self.ui_settings_frame,
                textvariable=self.var_settings_isovalue_2,
                width=10)
        self.ui_settings_isovalue_2.grid(row=0, column=2, sticky='ew')
        self.ui_settings_update_btn = tk.Button(self.ui_settings_frame,
                text='Update', command=self._update_surface)
        self.ui_settings_update_btn.grid(row=0, column=3, rowspan=2, sticky='news')

        self.ui_settings_color_palette = OptionMenu(self.ui_settings_frame,
                initialitem=3, label_text='Colors: ', labelpos='w',
                items=sorted(standard_color_palettes.keys()))
        self.ui_settings_color_palette.grid(row=1, column=0, columnspan=3,
                sticky='we')

        self.ui_report_btn = tk.Checkbutton(self.ui_settings_frame,
            text=u'Report \u03BB\u2082\u22C5\u03C1\u22C5100 value at cursor',
            command=self._report_values_cb, variable=self.var_settings_report)
        self.ui_report_btn.grid(row=2, column=0, columnspan=3)
        self.ui_reported_value = tk.Entry(self.ui_settings_frame,
            textvariable=self.var_reported_value, state='readonly',
            width=8)
        self.ui_reported_value.grid(row=2, column=3, sticky='we')

        # Plot figure
        self.ui_plot_frame = tk.LabelFrame(self.canvas,
                text=u'Plot RDG vs density (\u03BB\u2082\u22C5\u03C1)',
                padx=5, pady=5)
        self.ui_plot_button = tk.Button(self.ui_plot_frame, text='Plot', command=self._plot)
        self.ui_plot_button.grid(row=0)
        self.ui_plot_figure = Figure(figsize=(5, 5), dpi=100, facecolor='#D9D9D9')
        self.ui_plot_subplot = self.ui_plot_figure.add_subplot(111)

        self.ui_plot_widget_frame = tk.Frame(self.ui_plot_frame)
        self.ui_plot_widget_frame.grid(row=1)
        self.ui_plot_widget = FigureCanvasTkAgg(self.ui_plot_figure,
                                                master=self.ui_plot_widget_frame)
        # self.plot_cursor = Cursor(self.plot_subplot, useblit=True, color='black', linewidth=1)
        # self.plot_figure.canvas.mpl_connect('button_press_event', self._on_plot_click)

        # Register and map triggers, callbacks...
        chimera.triggers.addHandler('selection changed', self._on_selection_changed, None)
        self.nciplot_run = self.buttonWidgets['Run']
        self.buttonWidgets['Save']['state'] = 'disabled'

    def load_controller(self):
        binary, dat = prefs.get_preferences()
        return Controller(gui=self, nciplot_binary=binary, nciplot_dat=dat)

    def input_options(self):
        d = {}
        if self.var_input_intermolecular_enabled.get():
            d['intermolecular'] = self.var_input_intermolecular.get() / 100.0
        return d

    # All the callbacks
    def _input_choice_cb(self):
        """
        Change input mode
        """
        if self.var_input_choice.get() == 'molecules':
            self.ui_input_molecules.pack(expand=True, fill='x', padx=5)
            self.ui_input_named_selections.pack_forget()
        elif self.var_input_choice.get() == 'selection':
            self.ui_input_molecules.pack_forget()
            self.ui_input_named_selections.pack(expand=True, fill='x', padx=5)
        self._on_selection_changed()

    def _intermolecular_cb(self):
        if self.var_input_intermolecular_enabled.get():
            self.ui_input_intermolecular_field.config(state='normal')
        else:
            self.ui_input_intermolecular_field.config(state='disabled')

    def _validate_input_data(self, *args):
        atoms = self._on_selection_changed()
        return atoms

    def _configure_dialog(self, *args):
        if self.configure_dialog is None:
            self.configure_dialog = NCIPlotConfigureDialog(self)
        self.configure_dialog.enter()

    def Run(self, *args):
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
            self.ui_settings_frame.pack_forget()

    def Save(self, *args):
        try:
            grad = self.controller.data['grad_cube']
            dens = self.controller.data['dens_cube']
            xy = self.controller.data['xy_data']
        except KeyError:
            raise chimera.UserError("NCIPlot has not run yet!")
        path = tkFileDialog.asksaveasfilename(title='Choose destination (.cube)',
                                              filetypes=[('Gaussian cube', '*.cube'),
                                                         ('All', '*')],
                                              defaultextension='.cube')
        if not path:
            return
        data = self.controller.data.copy()
        basename, ext = os.path.splitext(path)
        data['grad_cube'] = newgradpath = '{fn}.grad{ext}'.format(fn=basename, ext=ext)
        shutil.copyfile(grad, newgradpath)
        data['dens_cube'] = newdenspath = '{fn}.dens{ext}'.format(fn=basename, ext=ext)
        shutil.copyfile(dens, newdenspath)
        data['xy_data'] = newdatpath = '{fn}.dat'.format(fn=basename, ext=ext)
        shutil.copyfile(xy, newdatpath)
        with open('{}.json'.format(basename), 'w') as f:
            json.dump(data, f)
        self.status('Saved at {}!'.format(os.path.dirname(path)), color='blue',
                    blankAfter=4)

    def Load(self, *args):
        path = tkFileDialog.askopenfilename(title='Choose state file (*.json)',
                                            filetypes=[('JSON file', '*.json'),
                                                       ('All', '*')])
        if not path:
            return
        with open(path) as f:
            data = json.load(f)
        self._run_nciplot_clear_cb()
        self.controller = self.load_controller()
        self.controller._after_cb(data)
        self._run_nciplot_cb()

    def Close(self):  # Singleton mode
        global ui
        ui = None
        super(NCIPlotDialog, self).Close()

    def _run_nciplot_cb(self):
        """
        Called after NCIPlot has successfully run
        """
        self.nciplot_run.configure(state='normal', text='Run')
        self.var_settings_isovalue_1.set(self.controller.surface.surface_levels[0])
        self.var_settings_isovalue_2.set(self.controller.surface.surface_levels[1])
        self.ui_settings_frame.pack()
        self.ui_plot_frame.pack(expand=True, fill='both')
        self.buttonWidgets['Save']['state'] = 'normal'

    def _run_nciplot_clear_cb(self):
        """
        Housecleaning method. Resets everything to original state
        """
        self.nciplot_run.configure(state='normal', text='Run')
        self.ui_plot_button.configure(state='normal')
        self.ui_settings_frame.pack_forget()
        self.var_settings_isovalue_1.set('')
        self.var_settings_isovalue_2.set('')
        self.ui_plot_frame.pack_forget()
        self.ui_plot_widget.get_tk_widget().pack_forget()
        self.controller = None
        self.buttonWidgets['Save']['state'] = 'disabled'

    def _update_surface(self):
        """
        Gets GUI options, sets them and updates the surface
        """
        # Levels
        isovalue_1 = float(self.var_settings_isovalue_1.get())
        isovalue_2 = float(self.var_settings_isovalue_2.get())
        self.controller.isosurface(level_1=isovalue_1, level_2=isovalue_2)
        # Update view
        self.controller.update_surface()
        # Colors
        palette = self.ui_settings_color_palette.getvalue()
        self.controller.colorize_by_volume(palette=palette)
        # Update view
        self.controller.update_surface()

    def _plot(self):
        """
        Draw density vs rdg with a hexbin
        """
        self.controller.plot(self.ui_plot_subplot)
        self.ui_plot_widget.get_tk_widget().pack(expand=True, fill='both')
        self.ui_plot_widget.show()
        self.ui_plot_button.configure(state='disabled')

    def _report_values_cb(self):
        """
        Binds mouse mouse callbacks to mouse movement events
        """
        if self.var_settings_report.get() and self._mouse_report_binding is None:
            self._mouse_report_binding = chimera.tkgui.app.graphics.bind('<Any-Motion>',
                                                                         self._report_values_event, add=True)

    def _report_values_event(self, event):
        """
        Report value of isosurface at cursor point
        """
        if self.var_settings_report.get() and self.isVisible():
            vpn = surface_value_at_window_position(event.x, event.y)
            if vpn is None:
                self.var_reported_value.set('')
            else:
                value, position, name = vpn
                self.var_reported_value.set('{:8.5g}'.format(float(value)))
                chimera.replyobj.status('{} at cursor: {:8.5g}'.format(name, float(value)))

    def _on_plot_click(self, event):
        """
        Callback that sets isosurface values from plot X axis data.
        Left click sets isovalue 1, right click sets isovalue 2
        """
        if event.button == 1:
            self.var_settings_isovalue_1.set(round(event.xdata, 2))
        elif event.button == 3:
            self.var_settings_isovalue_2.set(round(event.xdata, 2))

    def _on_selection_changed(self, *args):
        """
        Test if current selection is valid for running a new calculation,
        reports number of atoms
        """
        atoms = []
        if self.var_input_choice.get() == 'selection':
            atoms = chimera.selection.currentAtoms()
            molecules = chimera.selection.currentMolecules()
        elif self.var_input_choice.get() == 'molecules':
            molecules = self.ui_input_molecules.getvalue()
            atoms = [a for m in molecules for a in m.atoms]

        color, state = ('black', 'normal') if atoms else ('red', 'disabled')
        self.nciplot_run.configure(state=state)
        self.ui_input_summary_label.configure(foreground=color)
        self.var_input_summary.set('{} selected atoms'.format(len(atoms)))

        if len(molecules) > 1:
            self.ui_input_intermolecular_check.config(state='normal')
            self.ui_input_intermolecular_check.select()
        else:
            self.ui_input_intermolecular_check.config(state='disabled')
            self.ui_input_intermolecular_check.deselect()
        self._intermolecular_cb()

        return atoms


class NCIPlotConfigureDialog(PlumeBaseDialog):

    buttons = ('OK', 'Close')

    def __init__(self, *args, **kwargs):
        self.title = 'Configure NCIPlot paths'
        self.binary, self.dat_dir = tk.StringVar(), tk.StringVar()
        binary, dat = prefs.get_preferences()
        if binary is None:
            binary = ''
        if dat is None:
            dat = ''
        self.binary.set(binary)
        self.dat_dir.set(dat)
        self.text = tk.StringVar()
        self.text.set("Tip: Click <Help> to get NCIPlot")

        super(NCIPlotConfigureDialog, self).__init__(resizable=False,
                                                     *args, **kwargs)

    def fill_in_ui(self, parent):
        self.ui_label_0 = tk.Label(parent, text='NCIPlot program')
        self.ui_label_1 = tk.Label(parent, text='NCIPlot dat path')

        self.ui_bin_entry = tk.Entry(parent, textvariable=self.binary)
        self.ui_bin_browse = tk.Button(parent, text='...',
            command=lambda: self._browse_cb(self.binary,
                                            mode='filename',
                                            title='Select NCIPlot binary'))

        self.ui_dat_entry = tk.Entry(parent, textvariable=self.dat_dir)
        self.ui_dat_browse = tk.Button(parent, text='...',
            command=lambda: self._browse_cb(self.dat_dir,
                                            mode='directory',
                                            title='Select NCIPlot dat directory'))

        self.ui_label = tk.Label(parent, textvariable=self.text)
        self.ui_label.grid(row=2, columnspan=3)

        grid = [[self.ui_label_0, self.ui_bin_entry, self.ui_bin_browse],
                [self.ui_label_1, self.ui_dat_entry, self.ui_dat_browse]]
        self.auto_grid(parent, grid)


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

    def _browse_cb(self, var=None, mode='filename', **options):
        # result = OpenModal(**options).run(chimera.tkgui.app)

        functions = {'filename': tkFileDialog.askopenfilename,
                     'directory': tkFileDialog.askdirectory}
        result = functions[mode](parent=self.canvas, **options)
        if result and var:
            var.set(result)
        return result
