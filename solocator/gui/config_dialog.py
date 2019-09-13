# -*- coding: utf-8 -*-
"""
/***************************************************************************

                                 QgisLocator

                             -------------------
        begin                : 2018-05-03
        copyright            : (C) 2018 by Denis Rouzaud
        email                : denis@opengis.ch
        git sha              : $Format:%H$
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

from solocator.settingmanager.setting_dialog import SettingDialog, UpdateMode
from solocator.core.settings import Settings

DialogUi, _ = loadUiType(os.path.join(os.path.dirname(__file__), '../ui/config.ui'))


class ConfigDialog(QDialog, DialogUi, SettingDialog):
    def __init__(self, parent=None):
        settings = Settings()
        QDialog.__init__(self, parent)
        SettingDialog.__init__(self, setting_manager=settings, mode=UpdateMode.DialogAccept)
        self.setupUi(self)

        self.crs.addItem(self.tr('Use map CRS if possible, defaults to CH1903+'), 'project')
        self.crs.addItem('CH 1903+ (EPSG:2056)', '2056')
        self.crs.addItem('CH 1903 (EPSG:21781)', '21781')

        self.search_line_edit.textChanged.connect(self.filter_rows)
        self.select_all_button.pressed.connect(self.select_all)
        self.unselect_all_button.pressed.connect(lambda: self.select_all(False))

        self.settings = settings
        self.init_widgets()

    def select_all(self, select:bool =True):
        for r in range(self.feature_search_layers_list.rowCount()):
            item = self.feature_search_layers_list.item(r, 0)
            item.setCheckState(Qt.Checked if select else Qt.Unchecked)

    @pyqtSlot(str)
    def filter_rows(self, text: str):
        if text:
            items = self.feature_search_layers_list.findItems(text, Qt.MatchContains)
            print(text)
            print(len(items))
            shown_rows = []
            for item in items:
                shown_rows.append(item.row())
            shown_rows = list(set(shown_rows))
            for r in range(self.feature_search_layers_list.rowCount()):
                self.feature_search_layers_list.setRowHidden(r, r not in shown_rows)
        else:
            for r in range(self.feature_search_layers_list.rowCount()):
                self.feature_search_layers_list.setRowHidden(r, False)