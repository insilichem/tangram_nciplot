#!/usr/bin/env python
# encoding: utf-8


from __future__ import print_function, division 
import chimera.extension


class NCIPlotExtension(chimera.extension.EMO):

    def name(self):
        return 'Plume NCIPlot'

    def description(self):
        return "Depict orbitals and QM interaction blobs with NCIPlot"

    def categories(self):
        return ['InsiliChem']

    def icon(self):
        return

    def activate(self):
        self.module('gui').showUI()

chimera.extension.manager.registerExtension(NCIPlotExtension(__file__))
