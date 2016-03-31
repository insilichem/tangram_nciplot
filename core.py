#!/usr/bin/env python
# encoding: utf-8

# Get used to importing this in your Py27 projects!
from __future__ import print_function, division 
# Python stdlib
# Chimera stuff
# Additional 3rd parties
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
    def __init__(self, *args, **kwargs):
        return


class Model(object):

    """
    The model controls the data we work with. Normally, it'd be a Chimera molecule
    and some input files from other programs. The role of the model is to create
    a layer around those to allow the easy access and use to the data contained in
    those files
    """

    def __init__(self, *args, **kwargs):
        return