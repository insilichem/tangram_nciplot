#!/usr/bin/env python
# encoding: utf-8

"""
This is the preferences file for the extension. All default values
should be listed here for reference and easy reuse.
"""

# Get used to importing this in your Py27 projects!
from __future__ import print_function, division
import os
# Chimera
from chimera import preferences


options = {
    'nciplot_bin': '',
    'nciplot_dat': '',
}

def assert_preferences():
    try:
        binary, dat = get_preferences()
    except KeyError:
        binary, dat = '', ''
        category = preferences.addCategory('_plume_nciplot', preferences.HiddenCategory)
        category.set('nciplot_bin', binary)
        category.set('nciplot_dat', dat)
    return binary, dat

def set_preferences(binary, dat):
    assert_preferences()
    if os.path.isfile(binary) and os.path.isdir(dat):
        preferences.set('_plume_nciplot', 'nciplot_bin', binary)
        preferences.set('_plume_nciplot', 'nciplot_dat', dat)
    else:
        raise ValueError('One or more of the specified paths do not exist.')

def get_preferences():
    return preferences.get('_plume_nciplot', 'nciplot_bin'), \
           preferences.get('_plume_nciplot', 'nciplot_dat')

def test_preferences():
    binary, dat = assert_preferences()
    return os.path.isfile(binary) and os.path.isdir(dat)