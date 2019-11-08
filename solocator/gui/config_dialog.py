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
from qgis.PyQt.QtCore import Qt, pyqtSlot
from qgis.PyQt.QtWidgets import QDialog, QTableWidgetItem, QAbstractItemView
from qgis.PyQt.uic import loadUiType

from solocator.core.data_products import DATA_PRODUCTS
from solocator.qgis_setting_manager import SettingDialog, UpdateMode
from solocator.qgis_setting_manager.widgets import TableWidgetStringListWidget, ComboStringWidget
from solocator.core.settings import Settings

DialogUi, _ = loadUiType(os.path.join(os.path.dirname(__file__), '../ui/config.ui'))


class ConfigDialog(QDialog, DialogUi, SettingDialog):
    def __init__(self, parent=None):
        settings = Settings()
        QDialog.__init__(self, parent)
        SettingDialog.__init__(self, setting_manager=settings, mode=UpdateMode.DialogAccept)
        self.setupUi(self)

        self.search_line_edit.textChanged.connect(self.filter_rows)
        self.select_all_button.pressed.connect(self.select_all)
        self.unselect_all_button.pressed.connect(lambda: self.select_all(False))
        self.keep_scale.toggled.connect(self.point_scale.setDisabled)
        self.keep_scale.toggled.connect(self.scale_label.setDisabled)

        self.skipped_dataproducts.setRowCount(len(DATA_PRODUCTS))
        self.skipped_dataproducts.setColumnCount(2)
        self.skipped_dataproducts.setHorizontalHeaderLabels((self.tr('Name'), self.tr('ID')))
        self.skipped_dataproducts.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.skipped_dataproducts.setSelectionMode(QAbstractItemView.SingleSelection)
        r = 0
        for _id, name in DATA_PRODUCTS.items():
            item = QTableWidgetItem(name)
            item.setData(Qt.UserRole, _id)
            item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsUserCheckable)
            self.skipped_dataproducts.setItem(r, 0, item)
            self.skipped_dataproducts.setItem(r, 1, QTableWidgetItem(_id))
            r += 1
        self.skipped_dataproducts.horizontalHeader().setStretchLastSection(True)
        self.skipped_dataproducts.resizeColumnsToContents()

        self.settings = settings
        self.init_widgets()

        sd_widget: TableWidgetStringListWidget = self.setting_widget('skipped_dataproducts')
        sd_widget.column = 0
        sd_widget.userdata = True
        sd_widget.invert = True

        self.setting_widget('wms_image_format').auto_populate()
        self.setting_widget('default_layer_loading_mode').auto_populate()


    def select_all(self, select: bool = True):
        for r in range(self.skipped_dataproducts.rowCount()):
            item = self.skipped_dataproducts.item(r, 0)
            item.setCheckState(Qt.Checked if select else Qt.Unchecked)

    @pyqtSlot(str)
    def filter_rows(self, text: str):
        if text:
            items = self.skipped_dataproducts.findItems(text, Qt.MatchContains)
            shown_rows = []
            for item in items:
                shown_rows.append(item.row())
            shown_rows = list(set(shown_rows))
            for r in range(self.skipped_dataproducts.rowCount()):
                self.skipped_dataproducts.setRowHidden(r, r not in shown_rows)
        else:
            for r in range(self.skipped_dataproducts.rowCount()):
                self.skipped_dataproducts.setRowHidden(r, False)
