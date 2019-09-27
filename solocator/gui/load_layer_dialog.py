# -*- coding: utf-8 -*-
"""
/***************************************************************************

 QGIS Solothurn Locator Plugin
 Copyright (C) 2019 Denis Rouzaud

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


import os
from PyQt5.QtCore import Qt, pyqtSlot
from PyQt5.QtWidgets import QDialog, QTableWidgetItem, QAbstractItemView, QComboBox
from qgis.PyQt.uic import loadUiType
from qgis.core import QgsLocatorFilter

from solocator.settingmanager import SettingDialog, UpdateMode, TableWidgetStringListWidget
from solocator.core.settings import Settings

DialogUi, _ = loadUiType(os.path.join(os.path.dirname(__file__), '../ui/load_layer.ui'))


class LoadLayerDialog(QDialog, DialogUi, SettingDialog):
    def __init__(self, data, parent=None):
        settings = Settings()
        QDialog.__init__(self, parent)
        SettingDialog.__init__(self, setting_manager=settings, mode=UpdateMode.DialogAccept)
        self.setupUi(self)

        self.layerTreeWidget.addTopLevelItem(data.tree_widget_item())
        self.layerTreeWidget.setColumnCount(1)
        self.layerTreeWidget.setHeaderLabels(['Name'])





