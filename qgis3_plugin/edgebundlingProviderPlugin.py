# -*- coding: utf-8 -*-

"""
***************************************************************************
    edgebundlingProviderPlugin.py
    ---------------------
    Date                 : January 2018
    Copyright            : (C) 2018 by Anita Graser
    Email                : anitagraser@gmx.at
***************************************************************************
*                                                                         *
*   This program is free software; you can redistribute it and/or modify  *
*   it under the terms of the GNU General Public License as published by  *
*   the Free Software Foundation; either version 2 of the License, or     *
*   (at your option) any later version.                                   *
*                                                                         *
***************************************************************************
"""

__author__ = 'Anita Graser'
__date__ = 'January 2018'
__copyright__ = '(C) 2018, Anita Graser'

# This will get replaced with a git SHA1 when you do a git archive

__revision__ = '$Format:%H$'

from qgis.core import QgsApplication

from processing_edgebundling.edgebundlingProvider import EdgebundlingProvider


class EdgebundlingProviderPlugin:

    def __init__(self):
        self.provider = EdgebundlingProvider()

    def initGui(self):
        QgsApplication.processingRegistry().addProvider(self.provider)

    def unload(self):
        QgsApplication.processingRegistry().removeProvider(self.provider)
