# -*- coding: utf-8 -*-
"""
/***************************************************************************

 QGIS Swiss Locator Plugin
 Copyright (C) 2018 Denis Rouzaud

 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""

from PyQt5.QtWidgets import QWidget
from qgis.core import Qgis
from qgis.gui import QgisInterface, QgsMessageBarItem
from solocator.core.solocator_filter import SoLocatorFilter


class SoLocatorPlugin:
    def __init__(self, iface: QgisInterface):
        self.iface = iface
        self.locator_filter = SoLocatorFilter(iface)
        self.iface.registerLocatorFilter(self.locator_filter)

    def initGui(self):
        pass

    def unload(self):
        self.iface.deregisterLocatorFilter(self.locator_filter)

    def show_message(self, title: str, msg: str, level: Qgis.MessageLevel, widget: QWidget = None):
        if widget:
            self.widget = widget
            self.item = QgsMessageBarItem(title, msg, self.widget, level, 7)
            self.iface.messageBar().pushItem(self.item)
        else:
            self.iface.messageBar().pushMessage(title, msg, level)

