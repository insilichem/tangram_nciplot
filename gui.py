#!/usr/bin/env python
# encoding: utf-8

# Get used to importing this in your Py27 projects!
from __future__ import print_function, division
# Python stdlib
import Tkinter as tk
# Chimera stuff
import chimera
from chimera.baseDialog import ModelessDialog, ModalDialog
from chimera.widgets import ModelScrolledListBox
from Pmw import OptionMenu
# Additional 3rd parties

# Own
from core import Controller
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

    def __init__(self, *args, **kwarg):
        # GUI init
        self.title = 'Plume NCIPlot'

        # Fire up
        ModelessDialog.__init__(self, resizable=False)
        chimera.extension.manager.registerInstance(self)

    def fillInUI(self, parent):
        """
        This is the main part of the interface. With this method you code
        the whole dialog, buttons, textareas and everything.
        """
        # Main frame is always called 'canvas'
        parent.pack(expand=True, fill='y')
        self.canvas = tk.Frame(parent)
        self.canvas.pack(expand=True, fill='y', padx=10, pady=10)

        # Select an input menu: Radio buttons
        self.input_frame = tk.LabelFrame(self.canvas, text='Input mode', padx=5, pady=5)
        self.input_frame.pack()
        self.input_choice = tk.StringVar()
        self.input_choice.set('molecules')
        self.input_choice_frame = tk.Frame(self.input_frame)
        self.input_choice_frame.pack()
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
        self.input_frame = tk.Frame(self.input_frame)
        self.input_frame.pack(expand=True, fill='x')
        self.input_molecules = ModelScrolledListBox(self.input_frame, selectioncommand=None,
                                                   filtFunc=lambda m: isinstance(m, chimera.Molecule),
                                                   listbox_selectmode="extended")
        self.input_molecules.pack(expand=True, fill='x', padx=5)

        # Mode B: Current selection
        self.input_named_selections = OptionMenu(self.input_frame, command=None,
                                                items=['-- Choose selection --', 'Current selection'] 
                                                + sorted(chimera.selection.savedSels.keys()))
        self.input_new_named_atom_selection = None  # Text field + 'Create button'

        # Review input data
        self.input_summary = tk.StringVar()
        self.input_summary.set('Please select your input.')
        self.input_summary_label = tk.Label(self.input_frame, textvariable=self.input_summary)
        self.input_summary_label.pack(side='bottom')

        # NCIPlot launcher
        self.nciplot_frame = tk.Frame(self.canvas)
        self.nciplot_frame.pack()
        tk.Button(self.nciplot_frame, text='Configure', command=self._configure_dialog).pack(side='left')
        self.nciplot_run = tk.Button(self.nciplot_frame, text='Run', command=self._run_nciplot)
        self.nciplot_run.pack(side='left')

        # 

        # Visualization configuration; Only enabled after succesful NCIPlot run
        self.cfg_isovalue_slider = None
        self.cfg_isovalue_field = None
        self.cfg_color_selector = None
        self.cfg_alpha_slider = None
        self.cfg_alpha_field = None

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
        self.destroy()

    def Close(self):
        """
        Default! Triggered action if you click on the Close button
        """
        self.destroy()

    # Below this line, implement all your custom methods for the GUI.
    def load_controller(self):
        binary, dat = prefs.get_preferences()
        print(binary, dat)
        return Controller(gui=self, nciplot_binary=binary, nciplot_dat=dat)

    # All the callbacks
    def _input_choice_cb(self):
        if self.input_choice.get() == 'molecules':
            self.input_molecules.pack(expand=True, fill='x', padx=5)
            self.input_named_selections.pack_forget()
        elif self.input_choice.get() == 'selection':
            self.input_molecules.pack_forget()
            self.input_named_selections.pack(expand=True, fill='x', padx=5)

    def _validate_input_data(self, *args):
        atoms = None
        if self.input_choice.get() == 'molecules':
            molecules = self.input_molecules.getvalue()
            atoms = [a for m in molecules for a in m.atoms]
        elif self.input_choice.get() == 'selection':
            atoms = chimera.selection.currentAtoms()

        if not atoms:
            self.input_summary.set('No atoms selected!')
            self.input_summary_label.configure(foreground='red')
            raise chimera.UserError('Please, select at least a molecule or atom.')

        self.input_summary.set('Your selection contains {} atoms'.format(len(atoms)))
        self.input_summary_label.configure(foreground='black')
        
        return atoms

    def _configure_dialog(self, *args):
        dialog = NCIPlotConfigureDialog(self)
        dialog.enter()
        chimera.preferences.save()

    def _run_nciplot(self, *args):
        atoms = self._validate_input_data()
        self.controller = self.load_controller()
        self.controller.run(atoms=atoms)
        self.nciplot_run.configure(state='disabled', text='Running...')

    def _after_run_nciplot(self):
        self.nciplot_run.configure(state='normal', text='Run')
        pass

class NCIPlotConfigureDialog(ModalDialog):
    
    buttons = ('OK', 'Close')
    help = 'https://www.insilichem.com'

    def __init__(self, parent=None):
        self.title = 'Configure NCIPlot paths'
        self.binary, self.dat_dir = prefs.assert_preferences()
        ModalDialog.__init__(self, resizable=False)

    def fillInUI(self, parent):

        tk.Label(parent, text='NCIPlot program').grid(row=0)
        tk.Label(parent, text='NCIPlot dat path').grid(row=1)

        self.bin_entry = tk.Entry(parent, text=self.binary)
        self.bin_entry.grid(row=0, column=1)
        
        self.dat_entry = tk.Entry(parent, text=self.dat_dir)
        self.dat_entry.grid(row=1, column=1)

        self.text = tk.StringVar()
        self.text.set("Tip: Click <Help> to get NCIPlot")
        self.label = tk.Label(parent, textvariable=self.text)
        self.label.grid(row=2, columnspan=2)

    def OK(self):
        self.Apply()
        self.Close()

    def Apply(self):
        try:
            prefs.set_preferences(self.bin_entry.get(), self.dat_entry.get())
        except ValueError as e:
            self.text.set(str(e))
            self.label.configure(foreground='red')
            raise ValueError(e)

    def Close(self):
        self.destroy()