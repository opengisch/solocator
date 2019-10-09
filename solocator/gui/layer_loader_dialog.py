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
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtWidgets import QDialog, QAbstractItemView, QDialogButtonBox, QMessageBox
from qgis.PyQt.uic import loadUiType

from solocator.qgis_setting_manager import SettingDialog, UpdateMode
from solocator.core.settings import Settings
from solocator.core.layer import SoLayer

DialogUi, _ = loadUiType(os.path.join(os.path.dirname(__file__), '../ui/layer_loader_dialog.ui'))


class LayerLoaderDialog(QDialog, DialogUi, SettingDialog):
    def __init__(self, data, parent=None):
        settings = Settings()
        QDialog.__init__(self, parent)
        SettingDialog.__init__(self, setting_manager=settings, mode=UpdateMode.DialogAccept)
        self.setupUi(self)

        self.layerTreeWidget.addTopLevelItem(data.tree_widget_item())
        self.layerTreeWidget.setColumnCount(1)
        self.layerTreeWidget.setHeaderLabels(['Name'])
        self.layerTreeWidget.setSelectionMode(QAbstractItemView.SingleSelection)
        self.layerTreeWidget.setSelectionBehavior(QAbstractItemView.SelectRows)

        self.layerTreeWidget.setCurrentItem(self.layerTreeWidget.topLevelItem(0))

        self.layerTreeWidget.itemSelectionChanged.connect(self.on_selection_changed)
        self.on_selection_changed()

        self.settings = settings
        self.init_widgets()

        self.setting_widget('wms_image_format').auto_populate()

    def on_selection_changed(self):
        self.buttonBox.button(QDialogButtonBox.Ok).setEnabled(len(self.layerTreeWidget.selectedItems()) == 1)

        current_item = self.layerTreeWidget.currentItem().data(0, Qt.UserRole)
        if type(current_item) == SoLayer:
            self.descriptionBrowser.setText(current_item.description)
        else:
            self.descriptionBrowser.clear()

    def first_selected_item(self):
        return self.layerTreeWidget.currentItem().data(0, Qt.UserRole)

    def try_to_load_as_postgresql(self) -> tuple:
        return self.load_as_postgres.isChecked(), self.pg_auth_id.configId()

    def accept(self) -> None:
        if self.load_as_postgres.isChecked() and self.pg_auth_id.configId() == '':
            button = QMessageBox.question(self, 'Posgres authentification',
                                          'No authentification method has been defined. Are you sure to continue?')
            if button == QMessageBox.Yes:
                QDialog.accept(self)
            else:
                return
        else:
            QDialog.accept(self)
