#!/usr/bin/env python
# encoding: utf-8

# Get used to importing this in your Py27 projects!
from __future__ import print_function, division 
# Python stdlib
import Tkinter
# Chimera stuff
import chimera
from chimera.baseDialog import ModelessDialog
# Additional 3rd parties

# Own
from core import Controller

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
    if not ui: # Edit this to reflect the name of the class!
        ui = BlankDialog()
    ui.enter()
    if callback:
        ui.addCallback(callback)


class BlankDialog(ModelessDialog):

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
        self.title = 'Plume Blank Dialog'
        self.controller = None

        # Fire up
        ModelessDialog.__init__(self)
        chimera.extension.manager.registerInstance(self)

    def fillInUI(self, parent):
        """
        This is the main part of the interface. With this method you code
        the whole dialog, buttons, textareas and everything.
        """
        # Create main window
        self.tframe = Tkinter.Frame(parent)
        self.tframe.pack(expand=True, fill='both')

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
        path = self.pop_path.text()
        molecule = self.molecule_list.selected()
        self.controller = Controller(molecule, path)
        self.fill_in_controller_data()
