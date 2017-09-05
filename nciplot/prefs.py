#!/usr/bin/env python
# encoding: utf-8

"""
This is the preferences file for the extension. All default values
should be listed here for reference and easy reuse.
"""

# Get used to importing this in your Py27 projects!
from __future__ import print_function, division
from distutils.spawn import find_executable
import os
# Chimera
from chimera import preferences


def assert_preferences():
    insert_defaults = False
    try:
        binary, dat = get_preferences()
    except KeyError:
        insert_defaults = True
    else:
        if not binary or not dat:
            insert_defaults = True
    if insert_defaults:
        binary = find_executable('nciplot') or ''
        dat = ''
        if 'NCIPLOT_HOME' in os.environ:
            dat = os.path.join(os.environ['NCIPLOT_HOME'], 'dat')
        preferences.set('plume_nciplot', 'nciplot_bin', binary)
        preferences.set('plume_nciplot', 'nciplot_dat', dat)
        preferences.save(preferences.preferences._filename)
    return binary, dat


def set_preferences(binary, dat):
    assert_preferences()
    if os.path.isfile(binary) and os.path.isdir(dat):
        preferences.set('plume_nciplot', 'nciplot_bin', binary)
        preferences.set('plume_nciplot', 'nciplot_dat', dat)
        preferences.save(preferences.preferences._filename)
    else:
        raise ValueError('One or more of the specified paths do not exist.')


def get_preferences():
    return preferences.get('plume_nciplot', 'nciplot_bin'), \
           preferences.get('plume_nciplot', 'nciplot_dat')


def test_preferences():
    binary, dat = get_preferences()
    return os.path.isfile(binary) and os.path.isdir(dat)


preferences.addCategory('plume_nciplot', preferences.HiddenCategory)
assert_preferences()